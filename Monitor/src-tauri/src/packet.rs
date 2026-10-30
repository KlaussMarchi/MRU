use serde::Serialize;
use serde_json::{Map, Value};

pub const N: usize = 17;
pub const CHANNELS: [&str; N] = ["time", "tmp", "pitch", "roll", "yaw", "ax", "ay", "az", "wx", "wy", "wz", "heave", "heave_rate", "q0", "q1", "q2", "q3"];

pub const TIME: usize = 0;
pub const PITCH: usize = 2;
pub const ROLL: usize = 3;
pub const AX: usize = 5;
pub const AY: usize = 6;
pub const AZ: usize = 7;
pub const Q0: usize = 13;

const FULL: [&str; 13] = ["time", "tmp", "pitch", "roll", "yaw", "ax", "ay", "az", "wx", "wy", "wz", "heave", "heave_rate"];
const QUATERNION: [&str; 10] = ["time", "tmp", "pitch", "roll", "yaw", "q0", "q1", "q2", "q3", "heave"];
const TABLE: [&str; 3] = ["time", "pitch", "roll"];
const NMEA: [&str; 4] = ["pitch", "roll", "yaw", "heave"];
const RAW_LIMIT: f64 = 1000.0;    // ACELERAÇÃO NA CASA DE 1e6 (OU 4000 NO OR) É O INTEIRO DO RAW_MODE, NÃO m/s²
const GARBAGE: f64 = 0.2;         // FRAÇÃO DE CARACTERES ILEGÍVEIS QUE FAZ A LINHA SER BAUD ERRADO

// O QUE A LINHA É: QUEM MANDOU E EM QUE EIXOS E UNIDADES
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Layout {
    Table,
    Scale,
    Calibrated,
    Raw,
    Quaternion,
    Nmea,
    Legacy,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Format {
    List,
    Json,
    Nmea,
}

#[derive(Clone, Debug)]
pub struct Packet {
    pub layout: Layout,
    pub format: Format,
    pub values: [f64; N],
}

#[derive(Debug)]
pub enum Line {
    Packet(Packet),
    Text(String),
    Bad,
}

impl Layout {
    pub fn name(&self) -> &'static str {
        match self {
            Layout::Table => "table",
            Layout::Scale => "scale",
            Layout::Calibrated => "calibrated",
            Layout::Raw => "raw",
            Layout::Quaternion => "quaternion",
            Layout::Nmea => "nmea",
            Layout::Legacy => "legacy",
        }
    }
}

pub fn index(name: &str) -> Option<usize> {
    CHANNELS.iter().position(|channel| *channel == name)
}

// UMA LINHA DO SERIAL NO QUE ELA É; None PARA LINHA VAZIA
pub fn parse(raw: &[u8]) -> Option<Line> {
    let text = String::from_utf8_lossy(raw);
    let line = text.trim();

    if line.is_empty() {
        return None;
    }

    if line.starts_with('[') && line.ends_with(']') {
        return Some(parse_list(&line[1..line.len() - 1]));
    }

    if line.starts_with('{') && line.ends_with('}') {
        return Some(parse_json(line));
    }

    if line.starts_with("$GPPASHR") {
        return Some(parse_nmea(line));
    }

    if line.starts_with('[') || line.starts_with('{') || is_cut(line) || is_garbage(line) {
        return Some(Line::Bad);
    }

    Some(Line::Text(line.to_string()))
}

// O FIM DE UM PACOTE QUE COMEÇOU ANTES DE A PORTA ABRIR: ...] , ...} OU ...*CS SEM O COMEÇO
fn is_cut(line: &str) -> bool {
    let checksum = line.len() > 3 && line.as_bytes()[line.len() - 3] == b'*' && line[line.len() - 2..].chars().all(|c| c.is_ascii_hexdigit());
    !line.starts_with('$') && (line.ends_with(']') || line.ends_with('}') || checksum)
}

fn is_garbage(line: &str) -> bool {
    let total = line.chars().count() as f64;
    let unreadable = line.chars().filter(|c| !(c.is_ascii_graphic() || *c == ' ' || c.is_alphabetic())).count() as f64;
    unreadable / total > GARBAGE
}

fn empty() -> [f64; N] {
    [f64::NAN; N]
}

// OS LAYOUTS DO streamer PELO TAMANHO DA LISTA E O [t, pitch, roll] DO Table.ino
fn parse_list(content: &str) -> Line {
    let numbers: Result<Vec<f64>, _> = content.split(',').map(|value| value.trim().parse::<f64>()).collect();

    let numbers = match numbers {
        Ok(numbers) => numbers,
        Err(_) => return Line::Bad,
    };

    let keys: &[&str] = match numbers.len() {
        3 => &TABLE,
        10 => &QUATERNION,
        11 => &FULL[1..12],
        12 => &FULL[..12],
        13 => &FULL,
        _ => return Line::Bad,
    };

    let mut values = empty();

    for (key, number) in keys.iter().zip(numbers) {
        values[index(key).unwrap()] = number;
    }

    let layout = if keys.len() == 3 { Layout::Table } else { get_layout(&values) };
    Line::Packet(Packet { layout, format: Format::List, values })
}

// JSON COM pitch É AMOSTRA; O {"t","pitch","roll"} É A MESA; O RESTO ($status!, $settings!) É RESPOSTA EM TEXTO
fn parse_json(line: &str) -> Line {
    let object: Map<String, Value> = match serde_json::from_str(line) {
        Ok(object) => object,
        Err(_) => return Line::Bad,
    };

    let numbers: Vec<(&String, f64)> = object.iter().filter_map(|(key, value)| value.as_f64().map(|number| (key, number))).collect();
    let mut values = empty();

    if numbers.len() == 3 && ["t", "pitch", "roll"].iter().all(|key| object.get(*key).map_or(false, |value| value.is_number())) {
        values[TIME] = object["t"].as_f64().unwrap();
        values[PITCH] = object["pitch"].as_f64().unwrap();
        values[ROLL] = object["roll"].as_f64().unwrap();
        return Line::Packet(Packet { layout: Layout::Table, format: Format::Json, values });
    }

    if !object.get("pitch").map_or(false, |value| value.is_number()) {
        return Line::Text(line.to_string());
    }

    for (key, number) in numbers {
        if let Some(position) = index(key) {
            values[position] = number;
        }
    }

    Line::Packet(Packet { layout: get_layout(&values), format: Format::Json, values })
}

// $GPPASHR,pitch,roll,yaw,heave*CS COM O XOR ENTRE O $ E O *
fn parse_nmea(line: &str) -> Line {
    let (content, checksum) = match line[1..].split_once('*') {
        Some(parts) => parts,
        None => return Line::Bad,
    };

    let parity = content.bytes().fold(0u8, |parity, byte| parity ^ byte);

    if checksum.len() < 2 || !checksum[..2].eq_ignore_ascii_case(&format!("{parity:02X}")) {
        return Line::Bad;
    }

    let numbers: Result<Vec<f64>, _> = content.split(',').skip(1).map(|value| value.trim().parse::<f64>()).collect();

    let numbers = match numbers {
        Ok(numbers) if numbers.len() == NMEA.len() => numbers,
        _ => return Line::Bad,
    };

    let mut values = empty();

    for (key, number) in NMEA.iter().zip(numbers) {
        values[index(key).unwrap()] = number;
    }

    Line::Packet(Packet { layout: Layout::Nmea, format: Format::Nmea, values })
}

// SEM time É O FIRMWARE ANTIGO; ACELERAÇÃO NA CASA DE 1e6 É O RAW; O RESTO SE SEPARA PELA GRAVIDADE
fn get_layout(values: &[f64; N]) -> Layout {
    if !values[Q0].is_nan() {
        return Layout::Quaternion;
    }

    if values[AX].is_nan() {
        return Layout::Nmea;
    }

    if values[AX].abs().max(values[AY].abs()).max(values[AZ].abs()) > RAW_LIMIT {
        return Layout::Raw;
    }

    if values[TIME].is_nan() {
        return Layout::Legacy;
    }

    get_frame(values)
}

// SCALE E CALIBRATED TÊM OS MESMOS CAMPOS: A GRAVIDADE PELO PITCH E ROLL DIZ SE a ESTÁ NOS EIXOS DO KERNEL (Z PARA CIMA) OU NOS DO NAVIO (z PARA BAIXO)
fn get_frame(values: &[f64; N]) -> Layout {
    let (p, r) = (values[PITCH].to_radians(), values[ROLL].to_radians());
    let accel = [values[AX], values[AY], values[AZ]];
    let kernel = [-p.cos() * r.sin(), p.sin(), p.cos() * r.cos()];
    let ship = [p.sin(), -r.sin() * p.cos(), -r.cos() * p.cos()];
    let dot = |axis: [f64; 3]| accel.iter().zip(axis).map(|(a, b)| a * b).sum::<f64>();

    if dot(kernel) > dot(ship) {
        return Layout::Scale;
    }

    Layout::Calibrated
}

#[cfg(test)]
mod tests {
    use super::*;

    fn packet(line: &str) -> Packet {
        match parse(line.as_bytes()) {
            Some(Line::Packet(packet)) => packet,
            other => panic!("{line} não virou pacote: {other:?}"),
        }
    }

    #[test]
    fn lista_da_aquisicao_na_escala() {
        let sample = packet("[1.000,25.000,0.100,-0.200,30.000,0.034,0.017,9.810,0.010,-0.020,0.000,0.002,0.001]\r");
        assert_eq!(sample.layout, Layout::Scale);
        assert_eq!(sample.format, Format::List);
        assert_eq!(sample.values[index("heave_rate").unwrap()], 0.001);
    }

    #[test]
    fn calibrado_pela_gravidade_para_baixo() {
        let sample = packet(r#"{"time":1.000,"tmp":25.000,"pitch":0.100,"roll":-0.200,"yaw":30.000,"ax":0.017,"ay":0.034,"az":-9.785,"wx":-0.020,"wy":0.010,"wz":0.000,"heave":0.002,"heave_rate":0.001}"#);
        assert_eq!(sample.layout, Layout::Calibrated);
        assert_eq!(sample.format, Format::Json);
    }

    #[test]
    fn calibrado_de_cabeca_para_baixo_em_roll() {
        let sample = packet("[2.0,25,0.5,-92.0,10,0.3,9.78,0.4,0,0,0,0,0]");
        assert_eq!(sample.layout, Layout::Calibrated);
    }

    #[test]
    fn raw_pelos_inteiros_do_kernel() {
        let sample = packet("[1.000,253,100,-200,30000,34000,17000,1000000,1000,-2000,0,0]");
        assert_eq!(sample.layout, Layout::Raw);
    }

    #[test]
    fn quaternion_e_firmware_antigo() {
        assert_eq!(packet("[1.0,25,0.1,0.2,30,1.0,0.0,0.0,0.0,0.0]").layout, Layout::Quaternion);
        assert_eq!(packet("[25,0.1,0.2,30,0.03,0.01,9.81,0.0,0.0,0.0,0.0]").layout, Layout::Legacy);
    }

    #[test]
    fn mesa_em_lista_e_em_json() {
        assert_eq!(packet("[1.0,7.13,0.0]").layout, Layout::Table);
        let table = packet(r#"{"t":1.000,"pitch":7.13,"roll":0.00}"#);
        assert_eq!(table.layout, Layout::Table);
        assert_eq!(table.values[TIME], 1.0);
    }

    #[test]
    fn nmea_com_checksum() {
        let sample = packet("$GPPASHR,0.100,-0.200,30.000,0.002*50");
        assert_eq!(sample.layout, Layout::Nmea);
        assert_eq!(sample.values[index("heave").unwrap()], 0.002);
        assert!(matches!(parse(b"$GPPASHR,0.100,-0.200,30.000,0.002*51"), Some(Line::Bad)));
    }

    #[test]
    fn respostas_viram_texto() {
        for line in ["$MICACK!", "OK", "v1.0.8", r#"{"id":"0123ABCD","firmware":"v1.0.8","port":"USB","device_mode":0}"#, r#"{"server":"http://192.168.249.12:8000/api/","protocol":0}"#] {
            assert!(matches!(parse(line.as_bytes()), Some(Line::Text(_))), "{line}");
        }
    }

    #[test]
    fn lixo_de_baud_errado_e_linha_quebrada() {
        assert!(matches!(parse(&[0x48, 0xfe, 0x9f, 0x48, 0xfe, 0x9f, 0x48, 0xfe, 0x9f]), Some(Line::Bad)));
        assert!(matches!(parse(b"[1.0,2.0,3"), Some(Line::Bad)));
        assert!(matches!(parse(b"[1.0,2.0,x]"), Some(Line::Bad)));
        assert!(matches!(parse(b"[1.0,2.0,3.0,4.0,5.0]"), Some(Line::Bad)));
        assert!(matches!(parse(b"{\"pitch\":1.0,"), Some(Line::Bad)));
        assert!(matches!(parse(b"27,-0.007,-0.059,0.000,-0.000]"), Some(Line::Bad)));
        assert!(matches!(parse(b"\"heave\":0.002}"), Some(Line::Bad)));
        assert!(matches!(parse(b"30.000,0.002*50"), Some(Line::Bad)));
        assert!(matches!(parse(b"$MICACK!"), Some(Line::Text(_))));
        assert!(parse(b"\r").is_none());
    }
}
