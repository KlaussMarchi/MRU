mod device;
mod discover;
mod firmware;
mod job;
mod packet;
mod simulate;

use device::{now, Device, Journal, Sample, Stats, Text};
use discover::{PortInfo, Probe};
use job::{Job, JobState};
use simulate::Rig;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager, State};
use tauri_plugin_opener::OpenerExt;

const JOURNALS: [(&str, &str); 2] = [("mru", "target"), ("table", "reference")];    // O DIÁRIO DE CADA PAPEL, COM OS NOMES QUE O Session E O Calibration ESPERAM
const MODULES: [&str; 9] = ["numpy", "pandas", "scipy", "sklearn", "matplotlib", "reportlab", "tqdm", "multiprocess", "numba"];    // OS IMPORTS DO Pipeline E DO Session
const PYTHON: &str = "3.12";    // O uv BAIXA ESTE PYTHON PARA O AMBIENTE DO APP
const INSTALLER: &str = if cfg!(windows) { "https://astral.sh/uv/install.ps1" } else { "https://astral.sh/uv/install.sh" };
const STALE: f64 = 2.0;    // s SEM PACOTE: O STREAM PAROU E A TAXA É ZERO
const PREVIEW: usize = 4000;    // LINHAS NO GRÁFICO DE UMA SESSÃO SALVA
const WINDOW: (f64, f64) = (1600.0, 900.0);    // TAMANHO DE PROJETO DAS TELAS, EM PIXELS LÓGICOS
const FILL: f64 = 0.92;    // FRAÇÃO MÁXIMA DA ÁREA ÚTIL DA TELA QUE A JANELA OCUPA AO ABRIR

// UMA GRAVAÇÃO EM ANDAMENTO: OS DIÁRIOS DE CADA APARELHO E A SOLTURA DA MESA DEPOIS DO TRECHO PARADO
struct Recording {
    folder: PathBuf,
    started: f64,
    still: Option<f64>,
    journals: Vec<(String, Journal)>,
    released: Option<f64>,
}

struct App {
    devices: Mutex<HashMap<String, Arc<Device>>>,
    rig: Arc<Rig>,
    recording: Mutex<Option<Recording>>,
    jobs: Mutex<HashMap<u64, Arc<Job>>>,
    counter: AtomicU64,
}

#[derive(Deserialize, Default, Clone, Copy)]
struct Cursor {
    sample: u64,
    text: u64,
}

#[derive(Serialize)]
struct Snapshot {
    port: String,
    baud: u32,
    sample_seq: u64,
    text_seq: u64,
    stats: Stats,
    samples: Vec<Sample>,
    texts: Vec<Text>,
}

#[derive(Serialize)]
struct RecordingInfo {
    folder: String,
    started: f64,
    elapsed: f64,
    still: Option<f64>,
    released: Option<f64>,
    rows: HashMap<String, u64>,
}

#[derive(Serialize)]
struct Poll {
    devices: HashMap<String, Snapshot>,
    recording: Option<RecordingInfo>,
}

impl Recording {
    fn info(&self) -> RecordingInfo {
        let rows = self.journals.iter().map(|(name, journal)| (name.clone(), journal.rows.load(Ordering::Relaxed))).collect();
        RecordingInfo { folder: self.folder.display().to_string(), started: self.started, elapsed: now() - self.started, still: self.still, released: self.released, rows }
    }
}

fn get_device(state: &State<App>, role: &str) -> Result<Arc<Device>, String> {
    state.devices.lock().unwrap().get(role).cloned().ok_or(format!("nenhum aparelho conectado como {role}"))
}

// AS AMOSTRAS E LINHAS NOVAS DESDE O CURSOR; ATRASADO DEMAIS, A TELA RECEBE NO MÁXIMO max AMOSTRAS ESPAÇADAS
fn get_snapshot(device: &Device, cursor: Cursor, max: usize) -> Snapshot {
    let shared = device.shared.0.lock().unwrap();
    let first = shared.sample_seq + 1 - shared.samples.len() as u64;
    let start = (cursor.sample + 1).max(first);
    let count = (shared.sample_seq + 1).saturating_sub(start) as usize;
    let stride = count.div_ceil(max.max(1)).max(1);
    let offset = ((start - first) as usize).min(shared.samples.len());    // CURSOR DE UM APARELHO ANTERIOR, À FRENTE DESTE: NADA NOVO
    let samples = shared.samples.range(offset..).rev().step_by(stride).cloned().collect::<Vec<_>>().into_iter().rev().collect();

    let first = shared.text_seq + 1 - shared.texts.len() as u64;
    let start = (cursor.text + 1).max(first);
    let texts = shared.texts.range(((start - first) as usize).min(shared.texts.len())..).cloned().collect();

    let mut stats = shared.stats.clone();

    if now() - stats.last > STALE {
        stats.rate = 0.0;
    }

    Snapshot { port: device.port.clone(), baud: device.baud, sample_seq: shared.sample_seq, text_seq: shared.text_seq, stats, samples, texts }
}

// O MONITOR É AUTOSSUFICIENTE: OS SCRIPTS MORAM NO CÓDIGO-FONTE OU, INSTALADO, NOS RECURSOS DO INSTALADOR
fn get_scripts(app: &AppHandle) -> (PathBuf, bool) {
    let source = Path::new(env!("CARGO_MANIFEST_DIR")).join("..");

    if source.join("Pipeline/index.py").exists() {
        return (source.canonicalize().unwrap_or(source), false);
    }

    (app.path().resource_dir().unwrap_or_default(), true)
}

// LINUX SEM user-dirs.dirs NÃO TEM PASTA DE DOCUMENTOS: CAMINHO VAZIO VIRARIA RELATIVO À PASTA DE CADA SCRIPT
fn get_documents(app: &AppHandle) -> PathBuf {
    app.path().document_dir().or_else(|_| app.path().home_dir().map(|home| home.join("Documents"))).or_else(|_| app.path().app_local_data_dir()).unwrap_or_default()
}

// O AMBIENTE PYTHON QUE O PRÓPRIO APP INSTALA NA PASTA LOCAL DELE, E O EXECUTÁVEL DENTRO DELE
fn get_environment(app: &AppHandle) -> (PathBuf, PathBuf) {
    let folder = app.path().app_local_data_dir().unwrap_or_default().join("python");
    let python = if cfg!(windows) { folder.join("Scripts").join("python.exe") } else { folder.join("bin").join("python") };
    (folder, python)
}

#[tauri::command]
fn app_defaults(app: AppHandle) -> Value {
    let (scripts, installed) = get_scripts(&app);
    let (environment, managed) = get_environment(&app);
    let data = if installed { get_documents(&app).join("MRU Monitor") } else { scripts.join("Data") };
    let home = std::env::var("HOME").or(std::env::var("USERPROFILE")).unwrap_or_default();
    let candidates = [managed.display().to_string(), format!("{home}/miniconda3/bin/python"), format!("{home}/anaconda3/bin/python"), "python3".to_string(), "python".to_string()];
    let pythons: Vec<String> = candidates.into_iter().filter(|path| !(path.contains('/') || path.contains('\\')) || Path::new(path).exists()).collect();
    let firmware = if installed { scripts.join("Firmware/Main.ino.bin") } else { scripts.join("../Hardware/Embedded/Main/build/esp32.esp32.esp32s3/Main.ino.bin") };
    let firmware = firmware.canonicalize().unwrap_or(firmware);
    json!({"base": scripts, "sessions": data.join("Sessions"), "calibrations": data.join("Calibrations"), "environment": environment, "managed": managed, "pythons": pythons, "firmware": firmware})
}

#[tauri::command]
fn list_ports(state: State<App>) -> Vec<PortInfo> {
    discover::list_ports(&state.rig)
}

#[tauri::command]
async fn discover(app: AppHandle, state: State<'_, App>, role: String, port: Option<String>, baud: Option<u32>) -> Result<Option<Probe>, String> {
    let busy: Vec<String> = state.devices.lock().unwrap().values().map(|device| device.port.clone()).collect();
    let rig = state.rig.clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut ports: Vec<PortInfo> = discover::list_ports(&rig).into_iter().filter(|info| !busy.contains(&info.name)).collect();

        if let Some(name) = &port {
            ports.retain(|info| &info.name == name);

            if ports.is_empty() && !busy.contains(name) {
                ports.push(PortInfo { name: name.clone(), kind: "converter", label: name.clone(), vid: None, pid: None });
            }
        }

        let report = |message: String| {
            let _ = app.emit("discover", message);
        };

        ports.iter().find_map(|info| discover::search(info, &role, baud, &rig, &report))
    })
    .await
    .map_err(|error| error.to_string())
}

#[tauri::command]
fn connect(state: State<App>, role: String, port: String, baud: u32) -> Result<(), String> {
    let mut devices = state.devices.lock().unwrap();

    if let Some(other) = devices.iter().find(|(name, device)| **name != role && device.port == port) {
        return Err(format!("{port} já está aberta como {}", other.0));
    }

    if let Some(previous) = devices.remove(&role) {
        previous.stop();
    }

    let device = Arc::new(Device::new(&port, baud));
    device.start(state.rig.clone());
    devices.insert(role, device);
    Ok(())
}

#[tauri::command]
fn disconnect(state: State<App>, role: String) {
    if let Some(device) = state.devices.lock().unwrap().remove(&role) {
        device.stop();
    }
}

#[tauri::command]
fn send(state: State<App>, role: String, message: String, ending: Option<String>) -> Result<(), String> {
    get_device(&state, &role)?.send(&message, ending.as_deref().unwrap_or("\r\n"))
}

#[tauri::command]
async fn query(state: State<'_, App>, role: String, message: String, expect: Vec<String>, timeout: u64, quiet: Option<bool>) -> Result<String, String> {
    let device = get_device(&state, &role)?;
    let timeout = Duration::from_millis(timeout);
    tauri::async_runtime::spawn_blocking(move || if quiet.unwrap_or(false) { device.query_quiet(&message, &expect, timeout) } else { device.query(&message, &expect, timeout) }).await.map_err(|error| error.to_string())?
}

// CONFERE O ARQUIVO SEM TOCAR NA PORTA: É O QUE A TELA MOSTRA ANTES DE ENVIAR
#[tauri::command]
async fn firmware_inspect(path: String) -> Result<firmware::Image, String> {
    tauri::async_runtime::spawn_blocking(move || firmware::inspect(&path).map(|(image, _)| image)).await.map_err(|error| error.to_string())?
}

#[tauri::command]
fn firmware_start(state: State<App>, path: String) -> Result<u64, String> {
    if state.recording.lock().unwrap().is_some() {
        return Err("existe uma gravação em andamento: pare antes de atualizar".to_string());
    }

    let device = get_device(&state, "mru")?;
    let (image, bytes) = firmware::inspect(&path)?;
    let id = state.counter.fetch_add(1, Ordering::SeqCst) + 1;
    let job = Job::thread(id, "firmware");
    firmware::start(device, image, bytes, job.state.clone(), job.cancel.clone());
    state.jobs.lock().unwrap().insert(id, Arc::new(job));
    Ok(id)
}

#[tauri::command]
fn poll(state: State<App>, cursors: HashMap<String, Cursor>, max: usize) -> Poll {
    let devices = state.devices.lock().unwrap().iter().map(|(role, device)| (role.clone(), get_snapshot(device, cursors.get(role).copied().unwrap_or_default(), max))).collect();
    let recording = state.recording.lock().unwrap().as_ref().map(Recording::info);
    Poll { devices, recording }
}

#[tauri::command]
fn record_start(state: State<App>, folder: String, still: Option<f64>) -> Result<RecordingInfo, String> {
    let mut recording = state.recording.lock().unwrap();

    if recording.is_some() {
        return Err("já existe uma gravação em andamento".to_string());
    }

    let folder = PathBuf::from(folder);
    fs::create_dir_all(&folder).map_err(|error| format!("não foi possível criar {}: {error}", folder.display()))?;

    let devices = state.devices.lock().unwrap().clone();
    let mut journals = Vec::new();

    for (role, name) in JOURNALS {
        let Some(device) = devices.get(role) else { continue };
        let (journal, sender) = Journal::start(&folder.join(format!("{name}.journal.csv"))).map_err(|error| error.to_string())?;
        device.shared.0.lock().unwrap().journal = Some(sender);
        journals.push((name.to_string(), journal));
    }

    if journals.is_empty() {
        return Err("conecte o MRU ou a mesa antes de gravar".to_string());
    }

    let started = now();
    let table = devices.get("table").cloned();
    let platform = devices.get("mru").is_some_and(|mru| mru.port.starts_with("sim:"));

    if let (Some(_), Some(table)) = (still, &table) {
        table.send("start", "\r\n")?;    // A MESA FICA still s PARADA E RODA O CICLO: GRAVA DO MESMO INSTANTE QUE O MRU
    }

    if still.is_some() && table.is_none() && platform {
        state.rig.start();
    }

    let released = still.filter(|_| table.is_some() || platform);
    let current = Recording { folder, started, still, journals, released };
    let info = current.info();
    *recording = Some(current);
    Ok(info)
}

#[tauri::command]
fn record_stop(state: State<App>) -> Result<RecordingInfo, String> {
    let current = state.recording.lock().unwrap().take().ok_or("nenhuma gravação em andamento")?;

    for device in state.devices.lock().unwrap().values() {
        device.shared.0.lock().unwrap().journal = None;
    }

    if let (Some(_), Some(table)) = (current.released, state.devices.lock().unwrap().get("table")) {
        let _ = table.send("stop", "\r\n");    // A MESA VOLTA PARA CASA E ESPERA O PRÓXIMO start
    }

    let mut info = current.info();
    info.elapsed = now() - current.started;

    for (name, journal) in current.journals {
        let rows = journal.stop().map_err(|error| format!("erro gravando {name}.csv: {error}"))?;
        info.rows.insert(name, rows);
    }

    Ok(info)
}

#[tauri::command]
fn remove_folder(path: String) -> Result<(), String> {
    let folder = PathBuf::from(&path);
    let journal = ["target.journal.csv", "reference.journal.csv"].iter().any(|name| folder.join(name).exists());

    if !journal || folder.join("info.json").exists() {
        return Err(format!("{path} não é uma gravação descartável"));
    }

    fs::remove_dir_all(&folder).map_err(|error| error.to_string())
}

// APAGA O QUE HÁ DENTRO DA PASTA DE SESSÕES OU DE CALIBRAÇÕES, NÃO A PASTA: SÓ UMA PASTA FUNDA, NUNCA A RAIZ NEM A PASTA PESSOAL
#[tauri::command]
fn clear_folder(state: State<App>, path: String) -> Result<usize, String> {
    let folder = PathBuf::from(&path);
    let home = std::env::var("HOME").or(std::env::var("USERPROFILE")).map(PathBuf::from).unwrap_or_default();

    if state.recording.lock().unwrap().is_some() {
        return Err("pare a gravação antes de apagar: ela escreve dentro da pasta de sessões".to_string());
    }

    if !folder.exists() {
        return Ok(0);
    }

    if !folder.is_absolute() || folder.components().count() < 4 || folder == home || !folder.is_dir() {
        return Err(format!("{path} não é uma pasta de dados do app que possa ser esvaziada"));
    }

    let entries: Vec<PathBuf> = fs::read_dir(&folder).map_err(|error| error.to_string())?.filter_map(|entry| entry.ok().map(|entry| entry.path())).collect();

    for entry in &entries {
        let removed = if entry.is_dir() { fs::remove_dir_all(entry) } else { fs::remove_file(entry) };
        removed.map_err(|error| format!("{}: {error}", entry.display()))?;
    }

    Ok(entries.len())
}

fn start_job(state: &State<App>, kind: &str, program: &str, args: &[String], cwd: &str) -> Result<u64, String> {
    let id = state.counter.fetch_add(1, Ordering::SeqCst) + 1;
    let job = Job::start(id, kind, program, args, cwd)?;
    state.jobs.lock().unwrap().insert(id, Arc::new(job));
    Ok(id)
}

#[tauri::command]
fn job_start(state: State<App>, kind: String, python: String, script: String, args: Vec<String>, cwd: String) -> Result<u64, String> {
    start_job(&state, &kind, &python, &[vec!["-u".to_string(), script], args].concat(), &cwd)
}

// O SCRIPT DA INSTALAÇÃO: O uv NA PASTA LOCAL, UM PYTHON PRÓPRIO, O AMBIENTE E OS MÓDULOS, COM UM EVENTO DE PROGRESSO ANTES DE CADA PASSO
fn get_installer(local: &Path, environment: &Path, python: &Path, requirements: &Path) -> (&'static str, &'static str, String) {
    let windows = cfg!(windows);
    let uv = local.join("uv");
    let quote = |text: &str| if windows { format!("'{}'", text.replace('\'', "''")) } else { format!("'{}'", text.replace('\'', r"'\''")) };
    let path = |path: &Path| quote(&path.display().to_string());
    let step = |index: u32, message: &str| quote(&json!({"event": "progress", "stage": "Ambiente Python", "step": index, "steps": 3, "message": message}).to_string());
    let result = quote(&json!({"event": "result", "data": {"python": python}, "message": format!("ambiente pronto em {}", environment.display())}).to_string());
    let (download, create, modules) = (step(0, "baixando o uv"), step(1, &format!("criando o ambiente com o Python {PYTHON}")), step(2, "instalando os módulos do pipeline"));
    let (folder, pythons, target, executable, requirements) = (path(&uv), path(&local.join("pythons")), path(environment), path(python), path(requirements));

    if windows {
        let binary = path(&uv.join("uv.exe"));
        let script = format!("\u{FEFF}[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:UV_INSTALL_DIR = {folder}; $env:UV_NO_MODIFY_PATH = '1'; $env:UV_PYTHON_INSTALL_DIR = {pythons}
Write-Output {download}
Invoke-Expression (Invoke-RestMethod {INSTALLER} -ErrorAction Stop)
if (-not (Test-Path {binary})) {{ exit 1 }}
Write-Output {create}
& {binary} venv --clear --managed-python --python {PYTHON} {target}; if ($LASTEXITCODE) {{ exit $LASTEXITCODE }}
Write-Output {modules}
& {binary} pip install --python {executable} -r {requirements}; if ($LASTEXITCODE) {{ exit $LASTEXITCODE }}
Write-Output {result}
");
        return ("install.ps1", "powershell", script);
    }

    let binary = path(&uv.join("uv"));
    let script = format!("set -e
export UV_INSTALL_DIR={folder} UV_NO_MODIFY_PATH=1 UV_PYTHON_INSTALL_DIR={pythons}
echo {download}
installer=$(curl -LsSf {INSTALLER})
printf '%s\\n' \"$installer\" | sh
echo {create}
{binary} venv --clear --managed-python --python {PYTHON} {target}
echo {modules}
{binary} pip install --python {executable} -r {requirements}
echo {result}
");
    ("install.sh", "sh", script)
}

// O AMBIENTE DO PIPELINE NUMA MÁQUINA SEM PYTHON: O uv BAIXA UM PYTHON PRÓPRIO E OS MÓDULOS DO requirements.txt, TUDO NA PASTA LOCAL DO APP
#[tauri::command]
fn python_install(app: AppHandle, state: State<App>) -> Result<u64, String> {
    let (environment, python) = get_environment(&app);
    let local = environment.parent().map(Path::to_path_buf).unwrap_or_default();
    let requirements = get_scripts(&app).0.join("Pipeline").join("requirements.txt");
    let (name, program, script) = get_installer(&local, &environment, &python, &requirements);
    let file = local.join(name);

    fs::create_dir_all(local.join("uv")).map_err(|error| error.to_string())?;
    fs::write(&file, script).map_err(|error| error.to_string())?;
    let options: &[&str] = if cfg!(windows) { &["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"] } else { &[] };
    let args: Vec<String> = options.iter().map(|option| option.to_string()).chain([file.display().to_string()]).collect();
    start_job(&state, "environment", program, &args, &local.display().to_string())
}

// DESLIGAR A SIMULAÇÃO FECHA AS PORTAS FICTÍCIAS QUE ESTIVEREM ABERTAS
#[tauri::command]
fn simulation_set(state: State<App>, enabled: bool, scenario: String, fault: Option<String>) -> Value {
    state.rig.set(enabled, &scenario);
    state.rig.set_fault(fault.as_deref().unwrap_or(""));

    if !enabled {
        state.devices.lock().unwrap().retain(|_, device| !device.port.starts_with("sim:") || { device.stop(); false });
    }

    state.rig.get()
}

#[tauri::command]
fn simulation_reset(state: State<App>) {
    state.rig.reset();
}

#[tauri::command]
fn job_status(state: State<App>, id: u64) -> Result<JobState, String> {
    state.jobs.lock().unwrap().get(&id).map(|job| job.get()).ok_or(format!("tarefa {id} não existe"))
}

#[tauri::command]
fn job_cancel(state: State<App>, id: u64) {
    if let Some(job) = state.jobs.lock().unwrap().get(&id) {
        job.cancel();
    }
}

#[tauri::command]
async fn python_check(python: String) -> Value {
    let script = format!("import sys, json, importlib.util as u; print(json.dumps({{'version': sys.version.split()[0], 'executable': sys.executable, 'missing': [m for m in {MODULES:?} if u.find_spec(m) is None]}}))");
    let output = tauri::async_runtime::spawn_blocking(move || job::prepare(Command::new(&python).arg("-c").arg(&script)).output()).await;

    match output {
        Ok(Ok(output)) if output.status.success() => serde_json::from_slice(&output.stdout).unwrap_or(json!({"error": "resposta ilegível do Python"})),
        Ok(Ok(output)) => json!({"error": String::from_utf8_lossy(&output.stderr).trim().to_string()}),
        Ok(Err(error)) => json!({"error": error.to_string()}),
        Err(error) => json!({"error": error.to_string()}),
    }
}

fn read_json(path: &Path) -> Option<Value> {
    serde_json::from_str(&fs::read_to_string(path).ok()?).ok()
}

fn get_size(path: &Path) -> u64 {
    fs::metadata(path).map(|meta| meta.len()).unwrap_or(0)
}

// AS PASTAS DE UMA BIBLIOTECA (SESSÕES OU CALIBRAÇÕES), DA MAIS NOVA PARA A MAIS VELHA, COM O JSON DE CADA UMA
fn list_folders(folder: &str, record: &str) -> Vec<Value> {
    let Ok(entries) = fs::read_dir(folder) else { return Vec::new() };
    let mut folders: Vec<Value> = entries
        .filter_map(Result::ok)
        .filter(|entry| entry.path().is_dir() && !entry.file_name().to_string_lossy().starts_with('.'))
        .map(|entry| {
            let path = entry.path();
            let files: HashMap<String, u64> = fs::read_dir(&path).map(|files| files.filter_map(Result::ok).filter(|file| file.path().is_file()).map(|file| (file.file_name().to_string_lossy().to_string(), get_size(&file.path()))).collect()).unwrap_or_default();
            json!({"name": entry.file_name().to_string_lossy(), "path": path, "info": read_json(&path.join(record)), "files": files})
        })
        .collect();

    folders.sort_by(|a, b| b["name"].as_str().cmp(&a["name"].as_str()));
    folders
}

#[tauri::command]
fn list_sessions(folder: String) -> Vec<Value> {
    list_folders(&folder, "info.json")
}

#[tauri::command]
fn list_calibrations(folder: String) -> Vec<Value> {
    list_folders(&folder, "calibration.json")
}

#[tauri::command]
fn read_text(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|error| format!("{path}: {error}"))
}

#[tauri::command]
fn write_text(path: String, content: String) -> Result<(), String> {
    if let Some(parent) = Path::new(&path).parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }

    fs::write(&path, content).map_err(|error| format!("{path}: {error}"))
}

#[tauri::command]
fn copy_file(from: String, to: String) -> Result<(), String> {
    fs::copy(&from, &to).map(|_| ()).map_err(|error| format!("{from} → {to}: {error}"))
}

#[tauri::command]
fn open_path(app: AppHandle, path: String) -> Result<(), String> {
    app.opener().open_path(path, None::<&str>).map_err(|error| error.to_string())
}

// O CSV DE UMA SESSÃO EM ATÉ PREVIEW LINHAS ESPAÇADAS, PARA O GRÁFICO; True/False VIRAM 1/0
#[tauri::command]
async fn csv_preview(path: String, columns: Vec<String>) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let file = || fs::File::open(&path).map(|file| BufReader::with_capacity(1 << 20, file)).map_err(|error| format!("{path}: {error}"));
        let total = file()?.lines().count().saturating_sub(1);
        let stride = total.div_ceil(PREVIEW).max(1);
        let mut lines = file()?.lines().map_while(Result::ok);
        let header: Vec<String> = lines.next().unwrap_or_default().split(',').map(str::to_string).collect();
        let wanted: Vec<String> = if columns.is_empty() { header.clone() } else { columns.into_iter().filter(|column| header.contains(column)).collect() };
        let positions: Vec<usize> = wanted.iter().map(|column| header.iter().position(|name| name == column).unwrap()).collect();

        let parse = |cell: &str| match cell {
            "True" => Some(1.0),
            "False" => Some(0.0),
            _ => cell.parse::<f64>().ok(),
        };

        let rows: Vec<Vec<Option<f64>>> = lines.step_by(stride).map(|line| {
            let cells: Vec<&str> = line.split(',').collect();
            positions.iter().map(|position| cells.get(*position).and_then(|cell| parse(cell))).collect()
        }).collect();

        Ok(json!({"columns": wanted, "rows": rows, "total": total}))
    })
    .await
    .map_err(|error| error.to_string())?
}

// A JANELA ABRE NO TAMANHO DE PROJETO OU NA FRAÇÃO DA ÁREA ÚTIL QUE COUBER, CENTRADA NELA; MAXIMIZAR E TELA CHEIA FICAM COM O USUÁRIO
fn fit(window: &tauri::WebviewWindow) -> tauri::Result<()> {
    if let Some(monitor) = window.current_monitor()?.or(window.primary_monitor()?) {
        let (area, scale) = (monitor.work_area(), monitor.scale_factor());
        let width = (WINDOW.0 * scale).min(area.size.width as f64 * FILL) as u32;
        let height = (WINDOW.1 * scale).min(area.size.height as f64 * FILL) as u32;
        window.set_size(tauri::PhysicalSize::new(width, height))?;
        window.set_position(tauri::PhysicalPosition::new(area.position.x + (area.size.width - width) as i32 / 2, area.position.y + (area.size.height - height) as i32 / 2))?;
    }

    window.show()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(App { devices: Mutex::default(), rig: Arc::new(Rig::new()), recording: Mutex::default(), jobs: Mutex::default(), counter: AtomicU64::new(0) })
        .setup(|app| Ok(fit(&app.get_webview_window("main").expect("janela main do tauri.conf.json"))?))
        .invoke_handler(tauri::generate_handler![app_defaults, list_ports, discover, connect, disconnect, send, query, firmware_inspect, firmware_start, poll, record_start, record_stop, remove_folder, clear_folder, job_start, job_status, job_cancel, python_check, python_install, simulation_set, simulation_reset, list_sessions, list_calibrations, read_text, write_text, copy_file, open_path, csv_preview])
        .run(tauri::generate_context!())
        .expect("erro ao iniciar o MRU Monitor");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cursor_de_um_aparelho_anterior_nao_derruba_o_poll() {
        let device = Device::new("sim:mru", 115200);
        let snapshot = get_snapshot(&device, Cursor { sample: 30, text: 12 }, 4000);
        assert!(snapshot.samples.is_empty() && snapshot.texts.is_empty());
    }

    #[test]
    fn mru_simulado_de_fabrica_chega_a_100_hz_no_terminal_e_no_grafico() {
        let rig = Arc::new(Rig::new());
        rig.set(true, "table");
        let device = Device::new("sim:mru", 115200);
        device.start(rig.clone());
        std::thread::sleep(Duration::from_millis(5500));
        let snapshot = get_snapshot(&device, Cursor::default(), 100000);
        device.stop();

        let times: Vec<f64> = snapshot.samples.iter().map(|sample| sample.t).collect();
        let steps: Vec<f64> = times.windows(2).map(|pair| pair[1] - pair[0]).collect();
        let streamed = snapshot.texts.iter().filter(|text| text.kind == "stream").count();
        assert!((snapshot.stats.rate - 100.0).abs() < 0.5, "taxa exibida {}", snapshot.stats.rate);
        assert!(snapshot.samples.len() > 200, "{} amostras depois do boot", snapshot.samples.len());
        assert!(steps.iter().all(|step| *step > 0.0 && *step < 0.05), "o tempo das amostras anda sem parar nem voltar: {:?}", steps.iter().fold((f64::MAX, 0.0f64), |(low, high), step| (low.min(*step), high.max(*step))));
        assert_eq!(streamed, snapshot.samples.len(), "cada pacote também vai ao terminal");
        assert!(snapshot.samples.iter().any(|sample| sample.values[2].abs() > 1.0), "a plataforma simulada já balança sem gravação");
    }
}
