use crate::device::now;
use serde::Serialize;
use serde_json::Value;
use std::collections::VecDeque;
use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

const LOG: usize = 400;    // LINHAS DO LOG QUE A TELA MOSTRA
const GRACE: Duration = Duration::from_secs(3);    // DEPOIS DO SIGTERM, O SIGKILL
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

#[derive(Clone, Serialize, Default)]
pub struct JobState {
    pub id: u64,
    pub kind: String,
    pub status: String,
    pub stage: String,
    pub step: f64,
    pub steps: f64,
    pub message: String,
    pub log: VecDeque<String>,
    pub result: Option<Value>,
    pub error: Option<String>,
    pub started: f64,
    pub finished: Option<f64>,
}

// UM PROCESSO DO APP (SCRIPT PYTHON OU INSTALAÇÃO DO AMBIENTE): CADA LINHA JSON DO stdout É UM EVENTO (progress, log, result, error)
pub struct Job {
    pub state: Arc<Mutex<JobState>>,
    child: Arc<Mutex<Option<Child>>>,
}

impl JobState {
    fn push(&mut self, line: String) {
        self.log.push_back(line);

        if self.log.len() > LOG {
            self.log.pop_front();
        }
    }

    fn apply(&mut self, line: &str) {
        let event: Value = match serde_json::from_str(line) {
            Ok(event) => event,
            Err(_) => return self.push(line.to_string()),
        };

        let text = |key: &str| event.get(key).and_then(Value::as_str).map(str::to_string);

        match event.get("event").and_then(Value::as_str) {
            Some("progress") => {
                self.stage = text("stage").unwrap_or(self.stage.clone());
                self.step = event.get("step").and_then(Value::as_f64).unwrap_or(self.step);
                self.steps = event.get("steps").and_then(Value::as_f64).unwrap_or(self.steps);
                self.message = text("message").unwrap_or(self.message.clone());
            }
            Some("result") => self.result = event.get("data").cloned(),
            Some("error") => self.error = text("message"),
            _ => {}
        }

        if let Some(message) = text("message") {
            self.push(message);
        }
    }
}

impl Job {
    pub fn start(id: u64, kind: &str, program: &str, args: &[String], cwd: &str) -> Result<Job, String> {
        let mut command = Command::new(program);
        command.args(args).current_dir(cwd).stdout(Stdio::piped()).stderr(Stdio::piped()).stdin(Stdio::null());
        command.env("PYTHONUNBUFFERED", "1").env("MPLBACKEND", "Agg").env("PYTHONIOENCODING", "utf-8");
        hide(&mut command);

        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            command.process_group(0);    // O CANCELAMENTO MATA OS PROCESSOS QUE A BUSCA ABRIU
        }

        let mut child = command.spawn().map_err(|error| format!("não foi possível iniciar {program}: {error}"))?;
        let state = Arc::new(Mutex::new(JobState { id, kind: kind.to_string(), status: "running".to_string(), started: now(), ..Default::default() }));
        let stdout = child.stdout.take().unwrap();
        let stderr = child.stderr.take().unwrap();
        let child = Arc::new(Mutex::new(Some(child)));

        let errors = state.clone();
        thread::spawn(move || {
            for line in BufReader::new(stderr).lines().map_while(Result::ok) {
                errors.lock().unwrap().push(line);
            }
        });

        let (events, process) = (state.clone(), child.clone());
        thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                events.lock().unwrap().apply(&line);
            }

            let status = process.lock().unwrap().as_mut().map(|child| child.wait());
            let mut state = events.lock().unwrap();
            state.finished = Some(now());

            if state.status == "cancelled" {
                return;
            }

            let succeeded = matches!(status, Some(Ok(code)) if code.success()) && state.error.is_none();
            state.status = if succeeded { "done" } else { "error" }.to_string();

            if !succeeded && state.error.is_none() {
                state.error = Some(state.log.back().cloned().unwrap_or_else(|| "o script terminou com erro".to_string()));
            }
        });

        Ok(Job { state, child })
    }

    pub fn get(&self) -> JobState {
        self.state.lock().unwrap().clone()
    }

    pub fn cancel(&self) {
        let pid = match self.child.lock().unwrap().as_ref() {
            Some(child) => child.id(),
            None => return,
        };

        {
            let mut state = self.state.lock().unwrap();

            if state.status != "running" {
                return;
            }

            state.status = "cancelled".to_string();
            state.push("cancelado pelo usuário".to_string());
        }

        kill(pid, false);

        thread::spawn(move || {
            thread::sleep(GRACE);
            kill(pid, true);    // GRUPO QUE JÁ SAIU: O SINAL NÃO ACHA NINGUÉM
        });
    }
}

// O APP NO WINDOWS NÃO TEM CONSOLE: SEM ISSO CADA PROCESSO FILHO ABRE UMA JANELA PRETA, E FECHÁ-LA MATA A TAREFA
pub fn hide(command: &mut Command) -> &mut Command {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    command
}

#[cfg(unix)]
fn kill(pid: u32, force: bool) {
    unsafe {
        libc::kill(-(pid as i32), if force { libc::SIGKILL } else { libc::SIGTERM });
    }
}

#[cfg(windows)]
fn kill(pid: u32, _force: bool) {
    let _ = hide(Command::new("taskkill").args(["/PID", &pid.to_string(), "/T", "/F"])).status();
}
