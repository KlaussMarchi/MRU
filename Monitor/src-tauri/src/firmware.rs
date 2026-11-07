use crate::device::{now, Device};
use crate::job::JobState;
use base64::{engine::general_purpose::STANDARD, Engine};
use serde::Serialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const MAGIC: u8 = 0xE9;                            // PRIMEIRO BYTE DE UMA IMAGEM DO ESP32
const CHIP: u16 = 9;                               // ESP32-S3 NO esp_image_header_t
const DESCRIPTION: [u8; 4] = [0x32, 0x54, 0xCD, 0xAB];    // esp_app_desc_t: SÓ UMA APLICAÇÃO TEM, O merged E O bootloader NÃO
const HEADER: usize = 24;
const MARK: &[u8] = b"MRU_FIRMWARE=";
const PROTOCOL: &[u8] = b"$MICACK!";               // TODO FIRMWARE DO MRU, DE QUALQUER VERSÃO, TEM ESTE TEXTO
const PIECE: usize = 64;                           // BYTES POR ESCRITA: O USB NATIVO DESCARTA O QUE PASSA DO BUFFER DO ESP
const PAUSE: Duration = Duration::from_millis(2);
const CHUNK: usize = 2048;
const ANSWER: Duration = Duration::from_secs(5);   // ALÉM DO TEMPO DO BLOCO NA LINHA: O ESP ESTÁ GRAVANDO A FLASH
const ATTEMPTS: u32 = 6;                           // VEZES QUE UM BLOCO É TENTADO; O ESP DESISTE COM 15 s SEM RECEBER NADA
const ACKS: u32 = 5;
const LEGACY_END: Duration = Duration::from_secs(11);    // O FIRMWARE ANTIGO SÓ TERMINA DEPOIS DE 10 s SEM DADOS

#[derive(Clone, Serialize)]
pub struct Image {
    pub path: String,
    pub name: String,
    pub size: usize,
    pub crc: String,
    pub version: Option<String>,
    pub modified: f64,
    pub outdated: bool,
}

pub fn crc32(bytes: &[u8], start: u32) -> u32 {
    let mut crc = !start;

    for byte in bytes {
        crc ^= *byte as u32;

        for _ in 0..8 {
            crc = (crc >> 1) ^ (0xEDB88320 & 0u32.wrapping_sub(crc & 1));
        }
    }

    !crc
}

// O ARQUIVO É MESMO A APLICAÇÃO DO MRU, INTEIRA E PARA ESTE CHIP? OS SEGMENTOS, A SOMA E O SHA-256 VÊM DO esp_image_format
pub fn check(bytes: &[u8]) -> Result<(), String> {
    if bytes.len() < HEADER + 64 {
        return Err("o arquivo é pequeno demais para ser um firmware".to_string());
    }

    if bytes[0] != MAGIC {
        return Err(if bytes[0] == 0xAA { "este é o partitions.bin: use o Main.ino.bin".to_string() } else { "não é uma imagem de firmware do ESP32".to_string() });
    }

    let chip = u16::from_le_bytes([bytes[12], bytes[13]]);

    if chip != CHIP {
        return Err(format!("este firmware é de outro chip (id {chip}, o MRU usa ESP32-S3): {}", if chip == 0 { "parece o da mesa, ESP32 clássico" } else { "confira o arquivo" }));
    }

    if bytes[HEADER + 8..HEADER + 12] != DESCRIPTION {
        return Err("este é o merged ou o bootloader: use o Main.ino.bin".to_string());
    }

    let (mut position, mut checksum) = (HEADER, 0xEFu8);

    for _ in 0..bytes[1] {
        let header = bytes.get(position..position + 8).ok_or("o arquivo está cortado")?;
        let length = u32::from_le_bytes([header[4], header[5], header[6], header[7]]) as usize;
        let data = bytes.get(position + 8..position + 8 + length).ok_or("o arquivo está cortado")?;
        checksum = data.iter().fold(checksum, |sum, byte| sum ^ byte);
        position += 8 + length;
    }

    position |= 15;    // A SOMA FICA NO ÚLTIMO BYTE DO BLOCO DE 16

    if bytes.get(position) != Some(&checksum) {
        return Err("o arquivo está corrompido: a soma dos segmentos não confere".to_string());
    }

    if bytes[23] == 1 {
        let hash = bytes.get(position + 1..position + 33).ok_or("o arquivo está cortado")?;

        if Sha256::digest(&bytes[..position + 1]).as_slice() != hash {
            return Err("o arquivo está corrompido: o SHA-256 não confere".to_string());
        }
    }

    if !bytes.windows(PROTOCOL.len()).any(|window| window == PROTOCOL) {
        return Err("este firmware do ESP32-S3 não é o do MRU: ele não responde o ACK".to_string());
    }

    Ok(())
}

// A VERSÃO NA MARCA DO Main.ino OU, EM FIRMWARE ANTERIOR A ELA, A PRIMEIRA STRING vX.Y.Z DO ARQUIVO
pub fn get_version(bytes: &[u8]) -> Option<String> {
    if let Some(start) = bytes.windows(MARK.len()).position(|window| window == MARK) {
        let text = &bytes[start + MARK.len()..];
        let end = text.iter().position(|byte| *byte == 0).unwrap_or(0);
        return Some(String::from_utf8_lossy(&text[..end]).to_string());
    }

    bytes.split(|byte| *byte == 0).find(|text| {
        let parts: Vec<&[u8]> = text.strip_prefix(b"v").unwrap_or(&[]).split(|byte| *byte == b'.').collect();
        parts.len() == 3 && parts.iter().all(|part| !part.is_empty() && part.len() < 4 && part.iter().all(u8::is_ascii_digit))
    }).map(|text| String::from_utf8_lossy(text).to_string())
}

fn get_modified(path: &Path) -> Option<SystemTime> {
    path.metadata().and_then(|meta| meta.modified()).ok()
}

// O CÓDIGO MAIS NOVO QUE O .bin, QUANDO ELE ESTÁ NA PASTA build DO SKETCH: O ARQUIVO PADRÃO NÃO TEM O QUE FOI MEXIDO DEPOIS DE COMPILAR
fn is_outdated(path: &Path, built: SystemTime) -> bool {
    let Some(sketch) = path.parent().and_then(Path::parent).and_then(Path::parent) else { return false };

    if !sketch.join("Main.ino").exists() {
        return false;
    }

    fn newest(folder: &Path, built: SystemTime) -> bool {
        std::fs::read_dir(folder).map_or(false, |entries| entries.flatten().any(|entry| {
            let path = entry.path();

            if path.is_dir() {
                return path.file_name().is_none_or(|name| name != "build") && newest(&path, built);
            }

            matches!(path.extension().and_then(|text| text.to_str()), Some("h" | "ino" | "cpp")) && get_modified(&path).is_some_and(|time| time > built)
        }))
    }

    newest(sketch, built)
}

pub fn inspect(path: &str) -> Result<(Image, Vec<u8>), String> {
    let file = Path::new(path);
    let bytes = std::fs::read(file).map_err(|error| format!("não foi possível ler {path}: {error}"))?;
    check(&bytes)?;
    let modified = get_modified(file).unwrap_or(UNIX_EPOCH);

    let image = Image {
        path: path.to_string(),
        name: file.file_name().map_or(path.to_string(), |name| name.to_string_lossy().to_string()),
        size: bytes.len(),
        crc: format!("{:08x}", crc32(&bytes, 0)),
        version: get_version(&bytes),
        modified: modified.duration_since(UNIX_EPOCH).map_or(0.0, |elapsed| elapsed.as_secs_f64()),
        outdated: is_outdated(file, modified),
    };

    Ok((image, bytes))
}

// A TAREFA DE ATUALIZAÇÃO: O MESMO JobState DOS SCRIPTS, COM stage, step/steps EM BYTES E O LOG
struct Progress<'a> {
    state: &'a Arc<Mutex<JobState>>,
    cancel: &'a AtomicBool,
}

impl Progress<'_> {
    fn stage(&self, stage: &str, message: &str) {
        let mut state = self.state.lock().unwrap();
        state.stage = stage.to_string();
        state.message = message.to_string();
        state.push(format!("{stage}: {message}"));
    }

    fn log(&self, message: String) {
        self.state.lock().unwrap().push(message);
    }

    fn set(&self, step: usize, steps: usize, message: String) {
        let mut state = self.state.lock().unwrap();
        state.step = step as f64;
        state.steps = steps as f64;
        state.message = message;
    }

    fn cancelled(&self) -> bool {
        self.cancel.load(Ordering::SeqCst)
    }
}

// O TEMPO DO QUADRO NA LINHA ENTRA NA ESPERA: A 9600 bps UM BLOCO LEVA QUASE 3 s
fn get_answer(device: &Device, length: usize) -> Duration {
    ANSWER + Duration::from_secs_f64(length as f64 * 10.0 / device.baud.max(1200) as f64)
}

fn transmit(device: &Device, frame: &str) -> Result<(), String> {
    for piece in frame.as_bytes().chunks(PIECE) {
        device.write(piece)?;
        thread::sleep(PAUSE);
    }

    Ok(())
}

fn field(answer: &str, position: usize) -> &str {
    answer.trim_start_matches('$').trim_end_matches('!').split(':').nth(position).unwrap_or("")
}

// O PROTOCOLO DO FIRMWARE A PARTIR DA v1.0.9: BLOCO NUMERADO COM CRC, CONFIRMADO UM A UM, E O CRC DA IMAGEM NO FIM ANTES DE TROCAR A PARTIÇÃO
fn send_frames(device: &Device, bytes: &[u8], progress: &Progress) -> Result<u32, String> {
    let mut retries = 0;
    let started = now();

    for (index, chunk) in bytes.chunks(CHUNK).enumerate() {
        if progress.cancelled() {
            let _ = device.ask("$update_abort!", &["$UPDATE ABORTED".to_string(), "$UPDATE ERROR".to_string()], ANSWER);
            return Err("cancelada".to_string());
        }

        let frame = format!("${index},{:08x},{}!", crc32(chunk, 0), STANDARD.encode(chunk));
        let wanted = [format!("$UPDATE OK:{index}:"), "$UPDATE RETRY".to_string(), "$UPDATE ERROR".to_string()];
        let mut sent = false;

        for attempt in 0..ATTEMPTS {
            let start = device.mark();

            if let Err(error) = transmit(device, &frame) {
                progress.log(format!("bloco {index}: {error}"));
                retries += 1;
                thread::sleep(Duration::from_millis(500));    // A PORTA CAIU: A LEITURA REABRE SOZINHA
                continue;
            }

            match device.expect(start, &wanted, get_answer(device, frame.len())) {
                Some(answer) if answer.contains("$UPDATE OK") => {
                    sent = true;
                    break;
                }
                Some(answer) if answer.contains("$UPDATE ERROR") => return Err(format!("o MRU recusou: {}", field(&answer, 1))),
                Some(answer) => progress.log(format!("bloco {index}, tentativa {}: o MRU pediu de novo ({})", attempt + 1, field(&answer, 2))),
                None => progress.log(format!("bloco {index}, tentativa {}: sem confirmação", attempt + 1)),
            }

            retries += 1;
        }

        if !sent {
            return Err(format!("o MRU parou de responder no bloco {index} de {}: confira cabo e alimentação", bytes.len().div_ceil(CHUNK)));
        }

        let done = (index * CHUNK + chunk.len()).min(bytes.len());
        let speed = done as f64 / (now() - started).max(0.1) / 1024.0;
        progress.set(done, bytes.len(), format!("{} de {} KB · {speed:.1} KB/s{}", done / 1024, bytes.len() / 1024, if retries > 0 { format!(" · {retries} repetições") } else { String::new() }));
    }

    Ok(retries)
}

// O PROTOCOLO DOS FIRMWARES ATÉ A v1.0.8: SEM NÚMERO NEM CRC, UM BLOCO PERDIDO NÃO TEM COMO SER REPETIDO
fn send_legacy(device: &Device, bytes: &[u8], progress: &Progress) -> Result<(), String> {
    let wanted = ["__WRITTEN__".to_string(), "error to".to_string()];

    for (index, chunk) in bytes.chunks(CHUNK).enumerate() {
        if progress.cancelled() {
            progress.log("cancelada: o MRU desiste sozinho depois de 10 s".to_string());
            return Err("cancelada".to_string());
        }

        let frame = format!("${}!", STANDARD.encode(chunk));
        let start = device.mark();
        transmit(device, &frame)?;

        match device.expect(start, &wanted, get_answer(device, frame.len()) * 6) {
            Some(answer) if answer.contains("__WRITTEN__") => {}
            Some(answer) => return Err(format!("o MRU recusou: {answer}")),
            None => return Err(format!("o MRU parou de responder no bloco {index}")),
        }

        let done = (index * CHUNK + chunk.len()).min(bytes.len());
        progress.set(done, bytes.len(), format!("{} de {} KB", done / 1024, bytes.len() / 1024));
    }

    Ok(())
}

fn update(device: &Device, image: &Image, bytes: &[u8], progress: &Progress) -> Result<serde_json::Value, String> {
    let started = now();
    progress.stage("Sincronizar", &format!("procurando o MRU em {} a {} bps", device.port, device.baud));
    let ack = ["$MICACK!".to_string()];

    if !(0..ACKS).any(|_| device.ask("$ackoneledge!", &ack, Duration::from_millis(1500)).is_ok()) {
        return Err("o MRU não respondeu ao ACK: confira cabo, baud e alimentação".to_string());
    }

    progress.stage("Preparar", "pedindo para o MRU preparar a flash");
    let request = format!("$update:{}:{}!", bytes.len(), image.crc);
    let answers = ["$UPDATE".to_string()];
    let modern = match device.ask(&request, &answers, Duration::from_secs(4)) {
        Ok(answer) if answer.contains("READY") => true,
        Ok(answer) => return Err(format!("o MRU recusou a atualização: {}", field(&answer, 1))),
        Err(_) => false,
    };

    if !modern {
        progress.log("o firmware em uso não conhece a atualização com CRC: usando o protocolo antigo".to_string());
        device.ask("__updt__", &["STARTING_UPDATE".to_string()], Duration::from_secs(5)).map_err(|_| "o MRU não entrou no modo de atualização".to_string())?;
        thread::sleep(Duration::from_millis(500));
    }

    progress.stage("Enviar", "enviando o firmware");
    progress.set(0, bytes.len(), format!("0 de {} KB", bytes.len() / 1024));
    let retries = if modern { send_frames(device, bytes, progress)? } else { send_legacy(device, bytes, progress).map(|_| 0)? };
    progress.stage("Verificar", if modern { "o MRU confere o tamanho e o CRC da imagem" } else { "o firmware antigo termina depois de 10 s sem dados" });

    if modern {
        let finish = ["$UPDATE DONE".to_string(), "$UPDATE ERROR".to_string()];
        let answer = device.ask("$update_end!", &finish, Duration::from_secs(15)).or_else(|_| device.ask("$update_end!", &finish, Duration::from_secs(15)));

        match answer {
            Ok(answer) if answer.contains("DONE") => {}
            Ok(answer) => return Err(format!("o MRU recusou a imagem: {}; o firmware anterior continua", field(&answer, 1))),
            Err(_) => progress.log("sem resposta ao fim do envio: a volta do MRU é que vai dizer".to_string()),
        }
    } else {
        thread::sleep(LEGACY_END);
    }

    Ok(json!({"protocol": if modern { 2 } else { 1 }, "bytes": bytes.len(), "seconds": now() - started, "retries": retries, "version": image.version}))
}

// A THREAD DA ATUALIZAÇÃO SEGURA A PORTA: COMANDO DE OUTRA TELA NO MEIO DOS BLOCOS RECEBE ERRO EM VEZ DE CORROMPER O ENVIO
pub fn start(device: Arc<Device>, image: Image, bytes: Vec<u8>, state: Arc<Mutex<JobState>>, cancel: Arc<AtomicBool>) {
    thread::spawn(move || {
        device.hold(true);
        let result = update(&device, &image, &bytes, &Progress { state: &state, cancel: &cancel });
        device.hold(false);

        let mut state = state.lock().unwrap();
        state.finished = Some(now());

        match result {
            Ok(result) => {
                state.result = Some(result);
                state.status = "done".to_string();
            }
            Err(_) if cancel.load(Ordering::SeqCst) => state.status = "cancelled".to_string(),
            Err(error) => {
                state.push(error.clone());
                state.error = Some(error);
                state.status = "error".to_string();
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::job::Job;
    use crate::simulate::Rig;

    // UMA IMAGEM QUE O ESP ACEITARIA: CABEÇALHO, UM SEGMENTO COM A DESCRIÇÃO DA APLICAÇÃO, SOMA NO FIM DO BLOCO DE 16 E SHA-256
    fn get_image(version: &str, size: usize, ack: bool) -> Vec<u8> {
        let mut data = DESCRIPTION.to_vec();
        data.extend_from_slice(&[0u8; 60]);
        data.extend_from_slice(format!("MRU_FIRMWARE={version}\0").as_bytes());

        if ack {
            data.extend_from_slice(b"$MICACK!\0");
        }

        data.extend((0..size).map(|index| (index * 7 % 251) as u8));
        let mut bytes = vec![0u8; HEADER];
        bytes[0] = MAGIC;
        bytes[1] = 1;
        bytes[12] = CHIP as u8;
        bytes[23] = 1;
        bytes.extend_from_slice(&[0, 0, 0, 0]);
        bytes.extend_from_slice(&(data.len() as u32).to_le_bytes());
        bytes.extend_from_slice(&data);
        let checksum = data.iter().fold(0xEFu8, |sum, byte| sum ^ byte);

        while bytes.len() % 16 != 15 {
            bytes.push(0);
        }

        bytes.push(checksum);
        let hash = Sha256::digest(&bytes);
        bytes.extend_from_slice(&hash);
        bytes
    }

    #[test]
    fn imagem_valida_passa_e_mostra_a_versao() {
        let bytes = get_image("v9.9.9", 5000, true);
        assert_eq!(check(&bytes), Ok(()));
        assert_eq!(get_version(&bytes).as_deref(), Some("v9.9.9"));
        assert_eq!(get_version(b"\0abc\0v1.0.3\0xyz\0").as_deref(), Some("v1.0.3"), "firmware anterior à marca");
    }

    #[test]
    fn arquivo_errado_e_recusado_antes_de_tocar_no_mru() {
        let good = get_image("v9.9.9", 5000, true);
        let mut other = good.clone();
        other[12] = 0;
        let mut merged = good.clone();
        merged[HEADER + 8] = 0;
        let mut flipped = good.clone();
        flipped[400] ^= 0x10;
        let mut hash = good.clone();
        let last = hash.len() - 1;
        hash[last] ^= 1;
        let mut partitions = good.clone();
        partitions[0] = 0xAA;

        for (bytes, reason) in [(&other, "outro chip"), (&merged, "merged"), (&flipped, "corrompido"), (&hash, "SHA-256"), (&partitions, "partitions")] {
            let error = check(bytes).unwrap_err();
            assert!(error.contains(reason), "esperava {reason}, veio {error}");
        }

        assert!(check(&good[..good.len() / 2]).unwrap_err().contains("cortado"));
        assert!(check(&get_image("v9.9.9", 5000, false)).unwrap_err().contains("não é o do MRU"));
        assert!(check(&[1, 2, 3]).is_err());
    }

    fn get_device(fault: &str, legacy: bool) -> (Arc<Rig>, Arc<Device>) {
        let rig = Arc::new(Rig::new());
        rig.set(true, "still");
        rig.set_fault(fault);

        if legacy {
            rig.set_legacy();
        }

        let device = Arc::new(Device::new("sim:mru", 115200));
        device.start(rig.clone());
        (rig, device)
    }

    fn send_image(device: &Arc<Device>, bytes: Vec<u8>, cancel: bool) -> JobState {
        let image = Image { path: String::new(), name: String::new(), size: bytes.len(), crc: format!("{:08x}", crc32(&bytes, 0)), version: get_version(&bytes), modified: 0.0, outdated: false };
        let job = Job::thread(1, "firmware");
        start(device.clone(), image, bytes, job.state.clone(), job.cancel.clone());

        loop {
            thread::sleep(Duration::from_millis(50));
            let state = job.get();

            if cancel && state.step > 0.0 {
                job.cancel.store(true, Ordering::SeqCst);
            }

            if state.status != "running" {
                return state;
            }
        }
    }

    fn get_firmware(device: &Device) -> String {
        for _ in 0..20 {
            if let Ok(answer) = device.query("$firmware!", &["v".to_string()], Duration::from_millis(500)) {
                return answer;
            }
        }

        String::new()
    }

    #[test]
    fn atualiza_o_mru_simulado_e_o_firmware_muda() {
        let (_rig, device) = get_device("", false);
        let bytes = get_image("v9.9.9", 30000, true);
        let held = device.clone();
        let state = thread::spawn(move || send_image(&held, bytes, false));

        thread::sleep(Duration::from_millis(4000));
        assert!(device.send("$status!", "\r\n").unwrap_err().contains("atualizado"), "outra tela não fala na porta durante o envio");

        let state = state.join().unwrap();
        assert_eq!(state.status, "done", "{:?}", state.error);
        assert_eq!(state.result.unwrap()["protocol"], 2);
        assert_eq!(get_firmware(&device), "v9.9.9");
        device.stop();
    }

    #[test]
    fn linha_ruidosa_repete_blocos_e_termina_certo() {
        let (_rig, device) = get_device("noisy_link", false);
        let state = send_image(&device, get_image("v9.9.8", 120000, true), false);
        assert_eq!(state.status, "done", "{:?} {:?}", state.error, state.log);
        assert!(state.result.unwrap()["retries"].as_u64().unwrap() > 0, "a falha força repetições");
        assert_eq!(get_firmware(&device), "v9.9.8");
        device.stop();
    }

    #[test]
    fn erro_de_gravacao_mantem_o_firmware_em_uso() {
        let (_rig, device) = get_device("flash_fail", false);
        let state = send_image(&device, get_image("v9.9.7", 30000, true), false);
        assert_eq!(state.status, "error");
        assert!(state.error.unwrap().contains("Flash Write Failed"));
        assert_eq!(get_firmware(&device), "v1.0.9", "o que estava rodando continua");
        device.stop();
    }

    #[test]
    fn cancelar_devolve_o_mru_ao_normal() {
        let (_rig, device) = get_device("", false);
        let state = send_image(&device, get_image("v9.9.6", 200000, true), true);
        assert_eq!(state.status, "cancelled");
        assert_eq!(get_firmware(&device), "v1.0.9");
        device.stop();
    }

    #[test]
    fn firmware_antigo_atualiza_pelo_protocolo_dele() {
        let (_rig, device) = get_device("", true);
        let state = send_image(&device, get_image("v1.0.9", 20000, true), false);
        assert_eq!(state.status, "done", "{:?} {:?}", state.error, state.log);
        assert_eq!(state.result.unwrap()["protocol"], 1);
        assert_eq!(get_firmware(&device), "v1.0.9");
        device.stop();
    }

    #[test]
    fn firmware_novo_que_cai_volta_para_o_anterior() {
        let (_rig, device) = get_device("rollback", false);
        let state = send_image(&device, get_image("v9.9.5", 20000, true), false);
        assert_eq!(state.status, "done");
        thread::sleep(Duration::from_millis(4000));
        assert_eq!(get_firmware(&device), "v9.9.5", "no começo ele roda");
        thread::sleep(Duration::from_millis(4000));
        assert_eq!(get_firmware(&device), "v1.0.9", "caiu em prova: voltou sozinho");
        let info = device.query_quiet("$diagnostics!", &["\"uptime\"".to_string()], Duration::from_secs(2)).unwrap();
        assert!(info.contains("\"rolled_back\":true"), "{info}");
        assert!(info.contains("\"reset\":\"panic\""), "{info}");
        device.stop();
    }

    #[test]
    fn o_binario_de_release_do_repositorio_passa() {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../Hardware/Embedded/Main/build/esp32.esp32.esp32s3/Main.ino.bin");
        let (image, _) = inspect(path).unwrap();
        assert!(image.version.unwrap().starts_with('v'));
        assert!(image.size > 100000);
    }

    #[test]
    fn mru_mudo_falha_na_sincronizacao_com_motivo() {
        let rig = Arc::new(Rig::new());
        rig.set(true, "still");
        let device = Arc::new(Device::new("sim:mru", 9600));    // O SIMULADO ESTÁ EM 115200: COMANDO NÃO CHEGA
        device.start(rig);
        let state = send_image(&device, get_image("v9.9.4", 2000, true), false);
        assert_eq!(state.status, "error");
        assert!(state.error.unwrap().contains("não respondeu ao ACK"));
        device.stop();
    }
}
