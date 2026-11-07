use crate::packet::{self, Format, Layout, Line, CHANNELS, N, TIME};
use crate::simulate::{self, Link, Rig};
use serde::Serialize;
use std::collections::{HashMap, VecDeque};
use std::fs::File;
use std::io::{self, BufWriter, ErrorKind, Read, Write};
use std::path::Path;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Condvar, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const SAMPLES: usize = 1 << 17;                    // AMOSTRAS NA MEMÓRIA: ~11 MIN A 200 Hz PARA A TELA VOLTAR NO TEMPO
const TEXTS: usize = 3000;                         // LINHAS DO TERMINAL
const SPILL: usize = 4096;                         // BYTES SEM FIM DE LINHA: É BAUD ERRADO, O RESTO VAI FORA
const CHUNK: usize = 1 << 16;
const TIMEOUT: Duration = Duration::from_millis(20);    // O read NUNCA PRENDE A THREAD NEM GIRA EM VAZIO
const RETRY: Duration = Duration::from_millis(500);
const SILENT: u32 = 200;                           // LEITURAS VAZIAS SEGUIDAS QUE SIGNIFICAM PORTA MORTA
const FLUSH: Duration = Duration::from_secs(1);    // NO MÁXIMO UM SEGUNDO SE PERDE SE O PC CAIR
const STEPS: usize = 50;
const WRITE: Duration = Duration::from_secs(3);    // SEM ACEITAR NADA POR ESTE TEMPO, A PORTA MORREU
const SPACING: Duration = Duration::from_millis(120);    // O FIRMWARE LÊ A PORTA A CADA 100 ms: ATÉ A v1.0.8, DOIS COMANDOS NA MESMA LEITURA VIRAM UM SÓ, E O SEGUNDO SE PERDE

pub fn now() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|elapsed| elapsed.as_secs_f64()).unwrap_or(0.0)
}

#[derive(Clone, Serialize)]
pub struct Sample {
    pub seq: u64,
    pub host: f64,
    pub t: f64,
    pub layout: Layout,
    pub format: Format,
    pub values: [f64; N],
}

#[derive(Clone, Serialize)]
pub struct Text {
    pub seq: u64,
    pub host: f64,
    pub kind: &'static str,
    pub text: String,
}

#[derive(Clone, Serialize, Default)]
pub struct Stats {
    pub port: String,
    pub baud: u32,
    pub connected: bool,
    pub error: Option<String>,
    pub count: u64,
    pub lost: u64,
    pub bad: u64,
    pub bytes: u64,
    pub rate: f64,
    pub layout: Option<Layout>,
    pub format: Option<Format>,
    pub layouts: HashMap<&'static str, u64>,
    pub last: f64,
    pub opened: f64,
}

// O QUE A THREAD DE LEITURA DIVIDE COM OS COMANDOS: AMOSTRAS, TERMINAL, ESTATÍSTICAS E O DIÁRIO SE ESTIVER GRAVANDO
pub struct Shared {
    pub samples: VecDeque<Sample>,
    pub texts: VecDeque<Text>,
    pub sample_seq: u64,
    pub text_seq: u64,
    pub stats: Stats,
    pub journal: Option<Sender<Row>>,
    pub quiet: u32,    // RESPOSTAS DE DIAGNÓSTICO PEDIDAS PELO APP, QUE NÃO VÃO AO TERMINAL
}

pub struct Row {
    pub host: f64,
    pub layout: Layout,
    pub values: [f64; N],
}

impl Shared {
    fn push_text(&mut self, kind: &'static str, text: String) {
        self.text_seq += 1;
        self.texts.push_back(Text { seq: self.text_seq, host: now(), kind, text });

        if self.texts.len() > TEXTS {
            self.texts.pop_front();
        }
    }
}

// O RELÓGIO DO APARELHO LEVADO AO DO PC PELO MENOR ATRASO DE CHEGADA, AS PERDAS PELO SALTO NO time E A TAXA DO ÚLTIMO SEGUNDO
#[derive(Default)]
pub struct Tracker {
    offset: Option<f64>,
    previous: Option<f64>,
    steps: VecDeque<f64>,
    arrivals: VecDeque<f64>,
}

impl Tracker {
    fn update(&mut self, host: f64, time: f64, stats: &mut Stats) -> f64 {
        self.arrivals.push_back(host);

        while self.arrivals.front().map_or(false, |first| host - first > 1.0) {
            self.arrivals.pop_front();
        }

        stats.rate = self.arrivals.len() as f64;

        if time.is_nan() {
            return host;
        }

        if self.previous.map_or(false, |previous| time < previous) {    // TEMPO VOLTANDO É O APARELHO REINICIANDO O STREAM
            self.offset = None;
            self.steps.clear();
        }

        if let Some(previous) = self.previous.filter(|previous| time > *previous) {
            let step = time - previous;
            let nominal = self.get_nominal().unwrap_or(step);

            if step > 1.5 * nominal {
                stats.lost += ((step / nominal).round() as u64).saturating_sub(1);
            } else {
                self.steps.push_back(step);
            }

            if self.steps.len() > STEPS {
                self.steps.pop_front();
            }
        }

        self.previous = Some(time);
        stats.rate = self.get_nominal().map_or(stats.rate, |step| 1.0 / step);    // O PASSO MEDIANO DO time: A CONTAGEM DO ÚLTIMO SEGUNDO OSCILA COM OS LOTES DA PORTA
        let offset = self.offset.map_or(host - time, |offset| offset.min(host - time));
        self.offset = Some(offset);
        time + offset
    }

    fn get_nominal(&self) -> Option<f64> {
        if self.steps.is_empty() {
            return None;
        }

        let mut steps: Vec<f64> = self.steps.iter().copied().collect();
        steps.sort_by(|a, b| a.total_cmp(b));
        Some(steps[steps.len() / 2])
    }
}

// UMA PORTA SERIAL: LÊ NUMA THREAD PRÓPRIA, SEPARA AMOSTRAS DE RESPOSTAS E VOLTA SOZINHA SE A PORTA CAIR
pub struct Device {
    pub port: String,
    pub baud: u32,
    pub shared: Arc<(Mutex<Shared>, Condvar)>,
    writer: Arc<Mutex<Option<Box<dyn Write + Send>>>>,
    running: Arc<AtomicBool>,
    thread: Mutex<Option<JoinHandle<()>>>,
    asking: Mutex<()>,
    held: AtomicBool,    // A ATUALIZAÇÃO DO FIRMWARE É DONA DA PORTA
    spoken: Mutex<Option<Instant>>,
}

impl Device {
    pub fn new(port: &str, baud: u32) -> Device {
        let stats = Stats { port: port.to_string(), baud, opened: now(), ..Default::default() };
        let shared = Shared { samples: VecDeque::with_capacity(SAMPLES), texts: VecDeque::new(), sample_seq: 0, text_seq: 0, stats, journal: None, quiet: 0 };

        Device {
            port: port.to_string(),
            baud,
            shared: Arc::new((Mutex::new(shared), Condvar::new())),
            writer: Arc::new(Mutex::new(None)),
            running: Arc::new(AtomicBool::new(false)),
            thread: Mutex::new(None),
            asking: Mutex::new(()),
            held: AtomicBool::new(false),
            spoken: Mutex::new(None),
        }
    }

    pub fn start(&self, rig: Arc<Rig>) {
        self.running.store(true, Ordering::SeqCst);
        let (port, baud) = (self.port.clone(), self.baud);
        let (shared, writer, running) = (self.shared.clone(), self.writer.clone(), self.running.clone());
        let handle = thread::spawn(move || listen(&port, baud, &rig, shared, writer, running));
        *self.thread.lock().unwrap() = Some(handle);
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);

        if let Some(handle) = self.thread.lock().unwrap().take() {
            let _ = handle.join();
        }

        *self.writer.lock().unwrap() = None;
        self.shared.0.lock().unwrap().journal = None;
    }

    pub fn hold(&self, held: bool) {
        self.held.store(held, Ordering::SeqCst);
    }

    fn check_held(&self) -> Result<(), String> {
        if self.held.load(Ordering::SeqCst) {
            return Err("o firmware está sendo atualizado: a porta volta quando terminar".to_string());
        }

        Ok(())
    }

    pub fn send(&self, message: &str, ending: &str) -> Result<(), String> {
        self.check_held()?;
        self.transmit(message, ending)
    }

    // UM COMANDO POR VEZ NA PORTA, COM O INTERVALO QUE O FIRMWARE PRECISA, VENHA DE QUE TELA VIER
    fn speak(&self, line: &str) -> Result<(), String> {
        let mut spoken = self.spoken.lock().unwrap();

        if let Some(wait) = spoken.and_then(|last| SPACING.checked_sub(last.elapsed())) {
            thread::sleep(wait);
        }

        *spoken = Some(Instant::now());
        self.write(line.as_bytes())
    }

    fn transmit(&self, message: &str, ending: &str) -> Result<(), String> {
        self.speak(&format!("{message}{ending}"))?;
        self.shared.0.lock().unwrap().push_text("tx", message.to_string());
        Ok(())
    }

    // OS BYTES NA PORTA; COM O TIMEOUT DE ESCRITA A SERIAL ACEITA UM PEDAÇO DE CADA VEZ, E SÓ DESISTE SE PARAR DE ANDAR
    pub fn write(&self, bytes: &[u8]) -> Result<(), String> {
        let deadline = Instant::now() + WRITE;
        let mut sent = 0;

        while sent < bytes.len() {
            let mut writer = self.writer.lock().unwrap();
            let port = writer.as_mut().ok_or(format!("{} não está aberta", self.port))?;

            match port.write(&bytes[sent..]) {
                Ok(count) => sent += count,
                Err(error) if error.kind() == ErrorKind::TimedOut || error.kind() == ErrorKind::Interrupted => {}
                Err(error) => return Err(error.to_string()),
            }

            drop(writer);

            if Instant::now() > deadline {
                return Err(format!("{} parou de aceitar dados", self.port));
            }
        }

        self.writer.lock().unwrap().as_mut().map_or(Ok(()), |port| port.flush().map_err(|error| error.to_string()))
    }

    // MANDA O COMANDO E ESPERA A PRIMEIRA RESPOSTA QUE CONTÉM UM DOS TRECHOS; UMA PERGUNTA POR VEZ NA PORTA
    pub fn query(&self, message: &str, expect: &[String], timeout: Duration) -> Result<String, String> {
        self.check_held()?;
        self.ask(message, expect, timeout)
    }

    // O DIAGNÓSTICO PERIÓDICO DO APP: NEM A PERGUNTA NEM A RESPOSTA VÃO AO TERMINAL
    pub fn query_quiet(&self, message: &str, expect: &[String], timeout: Duration) -> Result<String, String> {
        self.check_held()?;
        let _turn = self.asking.lock().unwrap();
        let start = {
            let mut shared = self.shared.0.lock().unwrap();
            shared.quiet += 1;
            shared.text_seq
        };

        let result = self.speak(&format!("{message}\r\n")).and_then(|_| self.expect(start, expect, timeout).ok_or(format!("sem resposta a {message}")));
        let mut shared = self.shared.0.lock().unwrap();
        shared.quiet = shared.quiet.saturating_sub(1);
        result
    }

    pub fn ask(&self, message: &str, expect: &[String], timeout: Duration) -> Result<String, String> {
        let _turn = self.asking.lock().unwrap();
        let start = self.mark();
        self.transmit(message, "\r\n")?;
        self.expect(start, expect, timeout).ok_or(format!("sem resposta a {message} em {} ms", timeout.as_millis()))
    }

    pub fn mark(&self) -> u64 {
        self.shared.0.lock().unwrap().text_seq
    }

    // A PRIMEIRA RESPOSTA DEPOIS DA MARCA QUE CONTÉM UM DOS TRECHOS; OS EVENTOS DO FIRMWARE (#W ...) NÃO SÃO RESPOSTA
    pub fn expect(&self, start: u64, expect: &[String], timeout: Duration) -> Option<String> {
        let deadline = Instant::now() + timeout;
        let (lock, signal) = &*self.shared;
        let mut shared = lock.lock().unwrap();

        loop {
            let found = shared.texts.iter().filter(|text| text.seq > start && (text.kind == "rx" || text.kind == "health")).find(|text| expect.is_empty() || expect.iter().any(|piece| text.text.contains(piece.as_str())));

            if let Some(text) = found {
                return Some(text.text.clone());
            }

            let left = deadline.saturating_duration_since(Instant::now());

            if left.is_zero() {
                return None;
            }

            shared = signal.wait_timeout(shared, left).unwrap().0;
        }
    }
}

// UMA PORTA ABERTA EM LEITURA E ESCRITA: A SERIAL DE VERDADE OU, COM O PREFIXO sim:, A FICTÍCIA DO SIMULADOR, QUE ENTRA PELO MESMO CAMINHO
pub fn open(port: &str, baud: u32, rig: &Arc<Rig>) -> io::Result<Link> {
    if let Some(kind) = port.strip_prefix("sim:") {
        return simulate::open(rig, kind == "table", baud);
    }

    let serial = serialport::new(port, baud).timeout(TIMEOUT).open().map_err(io::Error::other)?;
    let writer = serial.try_clone().map_err(io::Error::other)?;
    Ok((Box::new(serial), Box::new(writer)))
}

fn listen(port: &str, baud: u32, rig: &Arc<Rig>, shared: Arc<(Mutex<Shared>, Condvar)>, writer: Arc<Mutex<Option<Box<dyn Write + Send>>>>, running: Arc<AtomicBool>) {
    let mut serial: Option<Box<dyn Read + Send>> = None;
    let mut buffer = vec![0u8; CHUNK];
    let mut pending: Vec<u8> = Vec::with_capacity(SPILL * 2);
    let mut tracker = Tracker::default();
    let mut silent = 0;

    while running.load(Ordering::SeqCst) {
        if serial.is_none() {
            match open(port, baud, rig) {
                Ok((reader, clone)) => {
                    *writer.lock().unwrap() = Some(clone);
                    serial = Some(reader);
                    pending.clear();
                    let mut state = shared.0.lock().unwrap();
                    state.stats.connected = true;
                    state.stats.error = None;
                    state.push_text("info", format!("{port} aberta a {baud} bps"));
                }
                Err(error) => {
                    set_error(&shared, &error.to_string());
                    thread::sleep(RETRY);
                }
            }

            continue;
        }

        let result = serial.as_mut().unwrap().read(&mut buffer);

        match result {
            Ok(0) => {
                silent += 1;

                if silent < SILENT {
                    continue;
                }

                silent = 0;
                serial = None;
                *writer.lock().unwrap() = None;
                set_error(&shared, "a porta parou de responder: reabrindo");
            }
            Ok(count) => {
                silent = 0;
                process(&buffer[..count], &mut pending, &shared, &mut tracker);
            }
            Err(error) if error.kind() == ErrorKind::TimedOut || error.kind() == ErrorKind::Interrupted => continue,
            Err(error) => {
                serial = None;
                *writer.lock().unwrap() = None;
                set_error(&shared, &format!("{port} caiu ({error}): reconectando"));
                thread::sleep(RETRY);
            }
        }
    }
}

fn set_error(shared: &Arc<(Mutex<Shared>, Condvar)>, message: &str) {
    let mut state = shared.0.lock().unwrap();

    if state.stats.error.as_deref() == Some(message) {
        return;
    }

    state.stats.connected = false;
    state.stats.error = Some(message.to_string());
    state.push_text("error", message.to_string());
}

// EVENTO DO FIRMWARE, RESPOSTA AO DIAGNÓSTICO DO APP OU RESPOSTA COMUM
fn get_kind(text: &str, quiet: u32) -> &'static str {
    if text.starts_with('#') {
        return "log";
    }

    if quiet > 0 && (text.starts_with("$VERBOSE") || (text.starts_with('{') && (text.contains("\"uptime\"") || text.starts_with("{\"log\"")))) {
        return "health";
    }

    "rx"
}

// O QUE CHEGOU, EM LINHAS COMPLETAS; A LINHA PELA METADE ESPERA O RESTO
pub fn process(chunk: &[u8], pending: &mut Vec<u8>, shared: &Arc<(Mutex<Shared>, Condvar)>, tracker: &mut Tracker) {
    let host = now();
    pending.extend_from_slice(chunk);

    let mut lines = Vec::new();
    let mut start = 0;

    while let Some(position) = pending[start..].iter().position(|byte| *byte == b'\n') {
        lines.push(start..start + position);
        start += position + 1;
    }

    let (lock, signal) = &**shared;
    let mut state = lock.lock().unwrap();
    let mut answered = false;
    state.stats.bytes += chunk.len() as u64;

    for range in lines {
        let raw = &pending[range];

        match packet::parse(raw) {
            Some(Line::Packet(packet)) => {
                let t = tracker.update(host, packet.values[TIME], &mut state.stats);
                state.sample_seq += 1;
                state.stats.count += 1;
                state.stats.last = host;
                state.stats.layout = Some(packet.layout);
                state.stats.format = Some(packet.format);
                *state.stats.layouts.entry(packet.layout.name()).or_insert(0) += 1;

                if let Some(journal) = &state.journal {
                    let _ = journal.send(Row { host, layout: packet.layout, values: packet.values });
                }

                let text: String = String::from_utf8_lossy(raw).trim().chars().take(240).collect();
                state.push_text("stream", text);

                let sample = Sample { seq: state.sample_seq, host, t, layout: packet.layout, format: packet.format, values: packet.values };
                state.samples.push_back(sample);

                if state.samples.len() > SAMPLES {
                    state.samples.pop_front();
                }
            }
            Some(Line::Text(text)) => {
                let kind = get_kind(&text, state.quiet);
                state.push_text(kind, text);
                answered = true;
            }
            Some(Line::Bad) => state.stats.bad += 1,
            None => {}
        }
    }

    pending.drain(..start);

    if pending.len() > SPILL {
        state.stats.bad += 1;
        pending.clear();
    }

    if answered {
        signal.notify_all();
    }
}

// O DIÁRIO DE UM APARELHO EM CSV: host, layout E OS CANAIS, NUMA THREAD PARA O DISCO NUNCA SEGURAR A LEITURA
pub struct Journal {
    pub rows: Arc<AtomicU64>,
    handle: JoinHandle<io::Result<u64>>,
}

impl Journal {
    pub fn start(path: &Path) -> io::Result<(Journal, Sender<Row>)> {
        let mut file = BufWriter::with_capacity(1 << 20, File::create(path)?);
        writeln!(file, "host,layout,{}", CHANNELS.join(","))?;

        let (sender, receiver) = mpsc::channel();
        let rows = Arc::new(AtomicU64::new(0));
        let counter = rows.clone();
        let handle = thread::spawn(move || write(file, receiver, counter));
        Ok((Journal { rows, handle }, sender))
    }

    pub fn stop(self) -> io::Result<u64> {
        self.handle.join().unwrap_or_else(|_| Err(io::Error::other("a gravação parou com erro")))
    }
}

fn write(mut file: BufWriter<File>, receiver: Receiver<Row>, rows: Arc<AtomicU64>) -> io::Result<u64> {
    let mut flushed = Instant::now();
    let mut line = String::with_capacity(256);

    loop {
        match receiver.recv_timeout(FLUSH) {
            Ok(row) => {
                line.clear();
                line.push_str(&format!("{:.6},{}", row.host, row.layout.name()));

                for value in row.values {
                    line.push(',');

                    if !value.is_nan() {
                        line.push_str(&value.to_string());
                    }
                }

                line.push('\n');
                file.write_all(line.as_bytes())?;
                rows.fetch_add(1, Ordering::Relaxed);
            }
            Err(mpsc::RecvTimeoutError::Timeout) => {}
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
        }

        if flushed.elapsed() >= FLUSH {
            file.flush()?;
            flushed = Instant::now();
        }
    }

    file.flush()?;
    Ok(rows.load(Ordering::Relaxed))
}
