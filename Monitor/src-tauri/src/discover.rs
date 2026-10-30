use crate::device;
use crate::packet::{self, Layout, Line};
use crate::simulate::Rig;
use serde::Serialize;
use serialport::{SerialPortType, UsbPortInfo};
use std::io::{ErrorKind, Read, Write};
use std::sync::atomic::Ordering;
use std::sync::Arc;
use std::time::{Duration, Instant};

pub const BAUDS: [u32; 9] = [460800, 115200, 9600, 921600, 230400, 57600, 38400, 19200, 4800];    // AQUISIÇÃO, PADRÃO DO GUIA E DE FÁBRICA PRIMEIRO
pub const TABLE_BAUD: u32 = 115200;                // Table.ino: Serial.begin(115200)
pub const USB_BAUD: u32 = 115200;                  // NO USB NATIVO O BAUD É IGNORADO
const ESPRESSIF: u16 = 0x303A;                     // VID DO USB NATIVO DO ESP32-S3
const LISTEN: Duration = Duration::from_millis(800);     // O STREAM MAIS LENTO QUE INTERESSA (10 Hz) MANDA OITO PACOTES; ABAIXO DISSO O ACK RESPONDE
const ANSWER: Duration = Duration::from_millis(700);
const ENOUGH: usize = 3;                           // PACOTES IGUAIS QUE BASTAM PARA DIZER QUEM FALA

#[derive(Clone, Serialize)]
pub struct PortInfo {
    pub name: String,
    pub kind: &'static str,
    pub label: String,
    pub vid: Option<u16>,
    pub pid: Option<u16>,
}

#[derive(Clone, Serialize, Default)]
pub struct Probe {
    pub port: String,
    pub baud: u32,
    pub kind: Option<&'static str>,
    pub link: &'static str,
    pub layout: Option<Layout>,
    pub streaming: bool,
    pub packets: usize,
    pub bad: usize,
    pub bytes: usize,
}

fn describe(info: &UsbPortInfo) -> String {
    let product = info.product.clone().or(info.manufacturer.clone()).unwrap_or_else(|| "USB serial".to_string());
    format!("{product} ({:04x}:{:04x})", info.vid, info.pid)
}

// AS PORTAS DE VERDADE (USB E PLACAS PCI, O USB NATIVO DO ESP32-S3 PRIMEIRO) E, COM A SIMULAÇÃO LIGADA, AS DUAS FICTÍCIAS NO FIM
pub fn list_ports(rig: &Rig) -> Vec<PortInfo> {
    let mut ports: Vec<PortInfo> = serialport::available_ports()
        .unwrap_or_default()
        .into_iter()
        .filter_map(|port| match &port.port_type {
            SerialPortType::UsbPort(info) if info.vid == ESPRESSIF => Some(PortInfo { label: format!("{} · USB nativo do MRU", port.port_name), name: port.port_name.clone(), kind: "usb", vid: Some(info.vid), pid: Some(info.pid) }),
            SerialPortType::UsbPort(info) => Some(PortInfo { label: format!("{} · {}", port.port_name, describe(info)), name: port.port_name.clone(), kind: "converter", vid: Some(info.vid), pid: Some(info.pid) }),
            SerialPortType::PciPort => Some(PortInfo { label: format!("{} · porta PCI", port.port_name), name: port.port_name.clone(), kind: "converter", vid: None, pid: None }),
            _ => None,
        })
        .collect();

    ports.sort_by_key(|port| (port.kind != "usb", port.name.clone()));

    if rig.enabled.load(Ordering::SeqCst) {
        ports.push(PortInfo { name: "sim:mru".to_string(), kind: "converter", label: "SIM0 · MRU simulado (RS232)".to_string(), vid: None, pid: None });
        ports.push(PortInfo { name: "sim:table".to_string(), kind: "converter", label: "SIM1 · plataforma simulada (Table.ino)".to_string(), vid: None, pid: None });
    }

    ports
}

pub fn get_bauds(port: &PortInfo, baud: Option<u32>) -> Vec<u32> {
    if port.kind == "usb" {
        return vec![USB_BAUD];
    }

    baud.map_or(BAUDS.to_vec(), |baud| vec![baud])
}

// OUVE A PORTA NUM BAUD POR listen E, SE PEDIDO E ELA ESTIVER MUDA, PERGUNTA PELO ACK DO MRU
pub fn probe(port: &PortInfo, baud: u32, listen: Duration, ask: bool, rig: &Arc<Rig>) -> Probe {
    let mut result = Probe { port: port.name.clone(), baud, link: if port.kind == "usb" { "USB" } else { "RS232/RS422" }, ..Default::default() };

    let (mut serial, mut writer) = match device::open(&port.name, baud, rig) {
        Ok(link) => link,
        Err(_) => return result,
    };

    let mut buffer = vec![0u8; 1 << 16];
    let mut pending: Vec<u8> = Vec::new();
    let (mut mru, mut table, mut answered) = (0usize, 0usize, false);
    let mut asked: Option<Instant> = None;
    let start = Instant::now();

    while mru < ENOUGH && table < ENOUGH && !answered {
        if asked.map_or(false, |time| time.elapsed() > ANSWER) {
            break;
        }

        if asked.is_none() && start.elapsed() > listen {
            if !ask || result.bytes > 0 || writer.write_all(b"$ackoneledge!\r\n").is_err() {
                break;
            }

            asked = Some(Instant::now());
        }

        let count = match serial.read(&mut buffer) {
            Ok(count) => count,
            Err(error) if error.kind() == ErrorKind::TimedOut => continue,
            Err(_) => break,
        };

        result.bytes += count;
        pending.extend_from_slice(&buffer[..count]);

        while let Some(position) = pending.iter().position(|byte| *byte == b'\n') {
            let line: Vec<u8> = pending.drain(..=position).collect();

            match packet::parse(&line) {
                Some(Line::Packet(packet)) if packet.layout == Layout::Table => table += 1,
                Some(Line::Packet(packet)) => {
                    mru += 1;
                    result.layout = Some(packet.layout);
                }
                Some(Line::Text(text)) if text.contains("$MICACK!") => answered = true,
                Some(Line::Bad) => result.bad += 1,
                _ => {}
            }
        }

        if pending.len() > 4096 {
            result.bad += 1;
            pending.clear();
        }
    }

    result.packets = mru.max(table);
    result.streaming = mru + table > 0;
    result.kind = if mru > table || answered { Some("mru") } else if table > 0 { Some("table") } else { None };
    result
}

// UMA PORTA: OUVE UMA VEZ; MUDA, PERGUNTA O ACK EM CADA BAUD; FALANDO, OUVE BAUD A BAUD ATÉ ENTENDER. A MESA SÓ SE OUVE: QUALQUER BYTE A FAZ ANDAR
pub fn search(port: &PortInfo, role: &str, baud: Option<u32>, rig: &Arc<Rig>, report: &dyn Fn(String)) -> Option<Probe> {
    let bauds = if role == "table" { vec![TABLE_BAUD] } else { get_bauds(port, baud) };
    report(format!("ouvindo {} a {} bps", port.name, bauds[0]));
    let first = probe(port, bauds[0], LISTEN, false, rig);

    if first.kind == Some(role) {
        return Some(first);
    }

    if first.kind.is_some() || (first.bytes == 0 && role == "table") {
        return None;
    }

    for baud in bauds.iter().skip(if first.bytes == 0 { 0 } else { 1 }) {
        report(format!("{} {} a {} bps", if first.bytes == 0 { "perguntando ao MRU em" } else { "ouvindo" }, port.name, baud));
        let result = if first.bytes == 0 { probe(port, *baud, Duration::ZERO, true, rig) } else { probe(port, *baud, LISTEN, false, rig) };

        if result.kind == Some(role) {
            return Some(result);
        }

        if result.kind.is_some() {
            return None;
        }
    }

    None
}
