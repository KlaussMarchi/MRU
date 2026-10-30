use crate::device::now;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::f64::consts::PI;
use std::io::{self, ErrorKind, Read, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use std::time::{Duration, Instant};

const FIRMWARE: &str = "v1.0.8";
const ID: &str = "SIMULADOR01";
const G0: f64 = 9.8106;                 // m/s² POR g DA ESCALA DO KERNEL
const GRAVITY: f64 = 9.785;             // g LOCAL DO ENSAIO
const BOOT: f64 = 2.5;                  // s QUE O MRU FICA MUDO REINICIANDO
const RATE: f64 = 200.0;                // Hz DO KERNEL EM HR: O PROCESSAMENTO ANDA NESTA TAXA E O STREAM DECIMA
const ACQUISITION_BAUD: u32 = 460800;
const TABLE_BAUD: u32 = 115200;
const TABLE_RATE: f64 = 100.0;          // Hz DO print() DO Table.ino
const TABLE_STEPS: f64 = 40.0;          // PASSOS DO MOTOR POR GRAU
const TABLE_HOMING: f64 = 0.5;          // s DO home() DEPOIS DO RESET QUE A ABERTURA DA PORTA CAUSA, COM A MESA JÁ EM CASA: A BUSCA OUVE 800 ms
const STILL: f64 = 20.0;                // s PARADA DEPOIS DO start, O TRECHO static DA CALIBRAÇÃO
const STAGE: f64 = 100.0;               // s DE CADA ETAPA DO Table.ino DEPOIS DOS 20 s: PITCH, ROLL E REPOUSO, EM CICLO
const RAMP: f64 = 2.0;                  // s DO ENVELOPE EM COSSENO NAS DUAS PONTAS DE CADA ETAPA
const AMPLITUDE: f64 = 15.0;            // graus
const MOTOR: [f64; 2] = [8000.0 / TABLE_STEPS, 6000.0 / TABLE_STEPS];    // graus/s E graus/s² DO SPEED_HZ_DEFAULT E DO ACCEL_DEFAULT DO Table.ino
const TICK: f64 = 2.5e-4;               // s ENTRE DOIS moveTo DO laço DO Table.ino
const GRID: f64 = 1e-3;                 // s DA TABELA DA ETAPA EXECUTADA PELO MOTOR
const INERTIA: f64 = 0.02;              // s DA MÉDIA COM QUE A MESA SEGUE O MOTOR, QUE ALTERNA ACELERAR E FREAR A CADA PLANEJAMENTO
const FREQUENCY: f64 = 0.3;             // Hz
const PIVOT: [f64; 3] = [0.0, 0.0, 0.30];         // m DOS EIXOS DA MESA ATÉ O KERNEL, NOS EIXOS DO KERNEL
const SHIP_LEVER: [f64; 3] = [2.5, -12.0, 4.0];   // m DO CENTRO DE GIRO DO NAVIO ATÉ O MRU
const STEP: f64 = 1e-3;                 // s DAS DERIVADAS NUMÉRICAS DA POSE
const ACCEL_NOISE: [f64; 3] = [0.0072, 0.0084, 0.0062];    // m/s²: σ PARADO DO KERNEL NO test3 A 200 Hz, EM JANELAS DE 15 s SEM TENDÊNCIA
const GYRO_NOISE: [f64; 3] = [0.068, 0.044, 0.037];         // graus/s
const ANGLE_NOISE: [f64; 3] = [0.0058, 0.0035, 0.0038];     // graus DE PITCH, ROLL E YAW
const ACCEL_BIAS: [f64; 3] = [0.012, -0.018, 0.025];
const GYRO_BIAS: [f64; 3] = [-0.024, 0.028, -0.003];
const ACCEL_SCALE: [f64; 3] = [1.0012, 0.9991, 1.0007];
const GYRO_SCALE: [f64; 3] = [0.9985, 1.0021, 1.0010];
const ACCEL_DRIFT: [f64; 3] = [0.0008, -0.0005, 0.0011];    // m/s² POR °C
const GYRO_DRIFT: [f64; 3] = [0.003, -0.002, 0.001];        // graus/s POR °C
const ANGLE_BIAS: [f64; 2] = [0.03, -0.02];                 // graus DO AHRS DO KERNEL EM PITCH E ROLL
const ANGLE_LAG: f64 = 0.008;           // s DE ATRASO DO AHRS DO KERNEL
const MOUNT: [f64; 3] = [0.0, -90.0, 0.0];          // MONTAGEM FÍSICA NA BANCADA: EM PÉ, CABO PARA CIMA (PRESET 1)
const MISALIGNMENT: [f64; 3] = [0.4, -0.25, 0.15];  // graus DA CAIXA SOBRE O CONVÉS ALÉM DA MONTAGEM NOMINAL
const TEMPERATURE: [f64; 3] = [34.5, 2.3, 1500.0];  // °C AO LIGAR, AQUECIMENTO E CONSTANTE DE TEMPO: 34,3 A 36,8 °C NO test3
const LOSS: f64 = 4e-4;                 // PACOTES PERDIDOS NO test3: 357 DE 850 141
const LATE: f64 = 0.108;                // CHANCE DE O CARIMBO EM ms SAIR 1 ms ATRASADO: 81% DOS PASSOS DE 5 ms E 9,6% DE 4 E DE 6, COMO NO test3
const BUFFER: f64 = 0.05;               // s DE LINHAS QUE O BUFFER DA UART SEGURA ANTES DE DESCARTAR
const TX_BUFFER: f64 = 512.0;           // bytes: O Serial.write ESPERA, ENTÃO UMA LINHA INTEIRA SEMPRE CABE, SÓ SAI MAIS DEVAGAR
const HEAVE: [f64; 2] = [1.0, 0.7];     // HEAVE_PERIOD E HEAVE_DAMPING COMPILADOS
const GAP: f64 = 0.5;                   // s SEM AMOSTRA: O FILTRO DO HEAVE RECOMEÇA EM REGIME
const READ: Duration = Duration::from_millis(20);    // O MESMO TIMEOUT DE LEITURA DA PORTA DE VERDADE
const POLL: Duration = Duration::from_millis(4);
const DEFAULTS: [(&str, &str); 8] = [("device_mode", "0"), ("streamer_mode", "0"), ("kernel_mode", "0"), ("protocol", "1"), ("frequency", "100"), ("autostream", "1"), ("baudrate", "115200"), ("output", "3")];    // O SIMULADOR JÁ SAI TRANSMITINDO 100 Hz EM LIST A 115200

// AS CHAVES DO CL: COM O TAMANHO DE CADA UMA NO FIRMWARE (MACHINE COM 6 ENTRADAS, 30 ESTADOS E 2 SAÍDAS)
const KEYS: [(&str, usize); 31] = [
    ("ATTITUDE_MODEL", 1), ("FILTERS_TYPE", 6), ("FILTERS_FC", 6), ("CORRECTION_T0", 1), ("CORRECTION_M", 18), ("CORRECTION_C", 6), ("CORRECTION_K", 6),
    ("ALIGN_CALIBRATION", 3), ("ALIGN_FRAME", 9), ("KALMAN_GRAVITY", 1), ("KALMAN_GYRO_NOISE", 1), ("KALMAN_BIAS_NOISE", 1), ("KALMAN_ACCEL_NOISE", 1),
    ("KALMAN_ZUPT_NOISE", 1), ("KALMAN_ACCEL_GATE", 1), ("KALMAN_GYRO_PHASE", 1), ("KALMAN_HEADING", 1), ("KALMAN_LEVER", 3), ("LINEAR_M", 9), ("LINEAR_B", 3),
    ("MACHINE_PERIOD", 1), ("MACHINE_SENSOR", 6), ("MACHINE_TARGET", 3), ("MACHINE_MEAN", 180), ("MACHINE_SCALE", 180), ("MACHINE_COEF", 360), ("MACHINE_BIAS", 2),
    ("HEAVE_PERIOD", 1), ("HEAVE_DAMPING", 1), ("HEAVE_GRAVITY", 1), ("LEVER_POINT", 3),
];

type Matrix = [[f64; 3]; 3];

// C DO CORPO PARA ENU DO ICD: Rz(−PROA) Rx(PITCH) Ry(ROLL), EIXOS DO KERNEL X BORESTE, Y PROA, Z CIMA
fn rotation(heading: f64, pitch: f64, roll: f64) -> Matrix {
    let (h, p, r) = (-heading.to_radians(), pitch.to_radians(), roll.to_radians());
    let rz = [[h.cos(), -h.sin(), 0.0], [h.sin(), h.cos(), 0.0], [0.0, 0.0, 1.0]];
    let rx = [[1.0, 0.0, 0.0], [0.0, p.cos(), -p.sin()], [0.0, p.sin(), p.cos()]];
    let ry = [[r.cos(), 0.0, r.sin()], [0.0, 1.0, 0.0], [-r.sin(), 0.0, r.cos()]];
    product(&product(&rz, &rx), &ry)
}

// PITCH, ROLL E PROA (0 A 360) DE UMA C NA CONVENÇÃO DO ICD: A TERCEIRA LINHA É [−cos θ sin φ, sin θ, cos θ cos φ]
fn get_euler(c: &Matrix) -> [f64; 3] {
    let pitch = c[2][1].clamp(-1.0, 1.0).asin().to_degrees();
    let roll = (-c[2][0]).atan2(c[2][2]).to_degrees();
    let heading = c[0][1].atan2(c[1][1]).to_degrees().rem_euclid(360.0);
    [pitch, roll, heading]
}

fn product(a: &Matrix, b: &Matrix) -> Matrix {
    let mut c = [[0.0; 3]; 3];

    for i in 0..3 {
        for j in 0..3 {
            c[i][j] = (0..3).map(|k| a[i][k] * b[k][j]).sum();
        }
    }

    c
}

fn transpose(a: &Matrix) -> Matrix {
    let mut c = [[0.0; 3]; 3];

    for i in 0..3 {
        for j in 0..3 {
            c[i][j] = a[j][i];
        }
    }

    c
}

fn apply(a: &Matrix, v: [f64; 3]) -> [f64; 3] {
    [0, 1, 2].map(|i| (0..3).map(|k| a[i][k] * v[k]).sum())
}

fn quaternion(c: &Matrix) -> [f64; 4] {
    let w = (1.0 + c[0][0] + c[1][1] + c[2][2]).max(1e-12).sqrt() / 2.0;
    [w, (c[2][1] - c[1][2]) / (4.0 * w), (c[0][2] - c[2][0]) / (4.0 * w), (c[1][0] - c[0][1]) / (4.0 * w)]
}

fn wrap(angle: f64) -> f64 {
    (angle + 180.0).rem_euclid(360.0) - 180.0
}

// (R v)_z: A TERCEIRA LINHA DE R = Rz Ry Rx NOS EIXOS DO NAVIO, A MESMA vertical() DO FIRMWARE
fn vertical(v: [f64; 3], pitch: f64, roll: f64) -> f64 {
    let (p, r) = (pitch.to_radians(), roll.to_radians());
    -p.sin() * v[0] + r.sin() * p.cos() * v[1] + r.cos() * p.cos() * v[2]
}

// GERADOR xorshift64* COM BOX-MULLER: RUÍDO SEM DEPENDÊNCIA EXTERNA
struct Noise(u64);

impl Noise {
    fn get(&mut self) -> f64 {
        self.0 ^= self.0 >> 12;
        self.0 ^= self.0 << 25;
        self.0 ^= self.0 >> 27;
        (self.0.wrapping_mul(0x2545F4914F6CDD1D) >> 11) as f64 / (1u64 << 53) as f64
    }

    fn gauss(&mut self, sigma: f64) -> f64 {
        let (u, v) = (self.get().max(1e-12), self.get());
        sigma * (-2.0 * u.ln()).sqrt() * (2.0 * PI * v).cos()
    }
}

// O MOVIMENTO QUE O MRU E A MESA SIMULADOS DIVIDEM: NAVIO EM ONDAS, O PROGRAMA DO Table.ino OU REPOUSO
pub struct Motion {
    pub scenario: String,
    pub released: Option<f64>,
    previous: Option<f64>,
    changed: f64,
}

#[derive(Clone, Copy, Default)]
struct Pose {
    pitch: f64,
    roll: f64,
    heading: f64,
    position: [f64; 3],
}

impl Motion {
    pub fn new(scenario: &str, released: Option<f64>) -> Motion {
        Motion { scenario: scenario.to_string(), released, previous: None, changed: f64::NEG_INFINITY }
    }

    // OUTRO PROGRAMA NO LUGAR DO ATUAL: O ANTIGO SAI EM RAMP s, SEM O SALTO DE ÂNGULO QUE O KERNEL VERIA COMO GIRO ENORME
    fn release(&mut self, released: Option<f64>) {
        (self.previous, self.released, self.changed) = (self.released, released, now());
    }

    // SEM GRAVAÇÃO A PLATAFORMA SIMULADA RODA O CICLO DIRETO, SEM OS 20 s PARADOS: O GRÁFICO NUNCA FICA PARADO
    fn cycle(&mut self) {
        self.release(Some(now() - STILL));
    }

    fn get(&self, time: f64) -> Pose {
        let wave = |amplitude: f64, period: f64, phase: f64| amplitude * (2.0 * PI * time / period + phase).sin();

        if self.scenario == "ship" {
            let position = [wave(0.2, 11.0, 0.4), wave(0.3, 9.5, 1.3), wave(0.8, 8.5, 0.0) + wave(0.3, 5.3, 0.5)];
            return Pose { pitch: wave(2.5, 7.2, 1.0) + wave(0.8, 4.9, 2.1), roll: wave(6.0, 9.5, 0.0) + wave(1.5, 6.1, 0.7), heading: 30.0 + wave(2.0, 40.0, 0.3), position };
        }

        if self.scenario != "table" {
            return Pose::default();
        }

        let fade = ((time - self.changed) / RAMP).clamp(0.0, 1.0);
        let weight = 0.5 * (1.0 - (PI * fade).cos());
        let ([p0, r0], [p1, r1]) = (get_program(self.previous, time), get_program(self.released, time));
        Pose { pitch: p0 + weight * (p1 - p0), roll: r0 + weight * (r1 - r0), ..Pose::default() }
    }

    fn get_lever(&self) -> [f64; 3] {
        match self.scenario.as_str() {
            "ship" => SHIP_LEVER,
            "table" => PIVOT,
            _ => [0.0; 3],
        }
    }
}

// O ALVO DO Table.ino EM UMA ETAPA: SENOIDE COM ENVELOPE EM COSSENO DE RAMP s NAS DUAS PONTAS
fn get_target(local: f64) -> f64 {
    let edge = local.min(STAGE - local);
    let envelope = if edge < RAMP { 0.5 * (1.0 - (PI * edge / RAMP).cos()) } else { 1.0 };
    AMPLITUDE * envelope * (2.0 * PI * FREQUENCY * local).sin()
}

// A ETAPA COMO O MOTOR A EXECUTA: O FastAccelStepper SÓ ACELERA ENQUANTO A DISTÂNCIA ATÉ O ALVO PASSA A DE FRENAGEM, ENTÃO FICA ATÉ v²/2a ATRÁS DA SENOIDE
fn get_stage() -> &'static [f64] {
    static TABLE: OnceLock<Vec<f64>> = OnceLock::new();

    TABLE.get_or_init(|| {
        let ([speed, accel], half) = (MOTOR, 0.5 / TABLE_STEPS);
        let (mut position, mut velocity, mut path) = (0.0, 0.0, Vec::new());

        for tick in 0..=(STAGE / TICK) as usize {
            let time = tick as f64 * TICK;
            path.push(position);
            let error = (get_target(time) * TABLE_STEPS).round() / TABLE_STEPS - position;
            let braking = velocity * error > 0.0 && error.abs() <= velocity * velocity / (2.0 * accel);
            let wanted = if braking { 0.0 } else { error.signum() * speed };
            velocity += (wanted - velocity).clamp(-accel * TICK, accel * TICK);
            position += velocity * TICK;

            if error.abs() < half && velocity.abs() < accel * TICK {
                (position, velocity) = (position + error, 0.0);
            }
        }

        let span = (INERTIA / TICK / 2.0) as usize;
        let sums: Vec<f64> = std::iter::once(0.0).chain(path.iter().scan(0.0, |sum, value| { *sum += value; Some(*sum) })).collect();

        let average = |i: usize| {
            let (low, high) = (i.saturating_sub(span), (i + span + 1).min(path.len()));
            (sums[high] - sums[low]) / (high - low) as f64
        };

        (0..path.len()).step_by((GRID / TICK) as usize).map(average).collect()
    })
}

// O PROGRAMA DO Table.ino SOLTO EM released: STILL s PARADA, DEPOIS PITCH, ROLL E REPOUSO EM CICLO, NA POSIÇÃO QUE O MOTOR ALCANÇA
fn get_program(released: Option<f64>, time: f64) -> [f64; 2] {
    let Some(released) = released.filter(|released| time - released >= STILL) else { return [0.0; 2] };
    let elapsed = (time - released - STILL) % (3.0 * STAGE);
    let (stage, local) = ((elapsed / STAGE) as usize, elapsed % STAGE);
    let (path, at) = (get_stage(), local / GRID);
    let index = (at as usize).min(path.len() - 2);
    let swing = path[index] + (at - index as f64) * (path[index + 1] - path[index]);
    [[swing, 0.0], [0.0, swing], [0.0, 0.0]][stage.min(2)]
}

// O QUE O SENSOR NO BRAÇO SENTE NA POSE: FORÇA ESPECÍFICA Cᵀ(a + g) PELA SEGUNDA DERIVADA DA POSIÇÃO DELE E A TAXA DO CORPO PELA DERIVADA DE C
struct Truth {
    pose: Pose,
    c: Matrix,
    accel: [f64; 3],
    gyro: [f64; 3],
}

fn measure(motion: &Motion, time: f64) -> Truth {
    let lever = motion.get_lever();
    let locate = |time: f64| {
        let pose = motion.get(time);
        let c = rotation(pose.heading, pose.pitch, pose.roll);
        let arm = apply(&c, lever);
        (pose, c, [0, 1, 2].map(|i| pose.position[i] + arm[i]))
    };

    let ((pose, c, p), (_, c0, p0), (_, c1, p1)) = (locate(time), locate(time - STEP), locate(time + STEP));
    let force = [0, 1, 2].map(|i| (p1[i] - 2.0 * p[i] + p0[i]) / (STEP * STEP) + if i == 2 { GRAVITY } else { 0.0 });
    let ct = transpose(&c);
    let mut derivative = [[0.0; 3]; 3];

    for i in 0..3 {
        for j in 0..3 {
            derivative[i][j] = (c1[i][j] - c0[i][j]) / (2.0 * STEP);
        }
    }

    let w = product(&ct, &derivative);
    let gyro = [(w[2][1] - w[1][2]) / 2.0, (w[0][2] - w[2][0]) / 2.0, (w[1][0] - w[0][1]) / 2.0].map(f64::to_degrees);
    Truth { pose, c, accel: apply(&ct, force), gyro }
}

// SEÇÃO z'' = u − 2ζω z' − ω² z COM A ENTRADA LINEAR NO PASSO, O Section DO FIRMWARE
#[derive(Clone, Copy, Default)]
struct Section {
    w: f64,
    zeta: f64,
    z0: f64,
    z1: f64,
    z2: f64,
    u: f64,
    primed: bool,
}

impl Section {
    fn new(period: f64, damping: f64) -> Section {
        Section { w: 2.0 * PI / (10.0 * period), zeta: damping, ..Section::default() }
    }

    fn update(&mut self, u: f64, dt: f64) -> &Section {
        if !self.primed || dt > GAP {
            (self.z0, self.z1, self.z2, self.u, self.primed) = (u / (self.w * self.w), 0.0, 0.0, u, true);
            return self;
        }

        let (e, w) = (self.zeta, self.w);
        let w0 = self.u - 2.0 * e * w * self.z1 - w * w * self.z0;
        let w1 = u - 2.0 * e * w * self.z1 - w * w * self.z0;
        self.z0 += self.z1 * dt + dt * dt * (2.0 * w0 + w1) / 6.0;
        self.z1 += dt * (w0 + w1) / 2.0;
        self.z2 = u - 2.0 * e * w * self.z1 - w * w * self.z0;
        self.u = u;
        self
    }
}

// HEAVE NO PONTO DO LEVER_POINT: DUAS SEÇÕES NA ACELERAÇÃO VERTICAL, AS BANDAS DE CADA EIXO E A TAXA POR DIFERENÇA, COMO heave/ E lever/ DO FIRMWARE
struct Heave {
    velocity: Section,
    position: Section,
    bands: [[Section; 2]; 3],
    previous: Option<f64>,
}

impl Heave {
    fn new(period: f64, damping: f64) -> Heave {
        let section = Section::new(period, damping);
        Heave { velocity: section, position: section, bands: [[section; 2]; 3], previous: None }
    }

    fn update(&mut self, accel: [f64; 3], pitch: f64, roll: f64, point: [f64; 3], dt: f64) -> (f64, f64) {
        let velocity = self.velocity.update(vertical(accel, pitch, roll) + GRAVITY, dt).z1;
        let mut heave = self.position.update(velocity, dt).z1;

        for (axis, [first, second]) in self.bands.iter_mut().enumerate() {
            let row = vertical([0, 1, 2].map(|k| if k == axis { 1.0 } else { 0.0 }), pitch, roll);
            heave += second.update(first.update(row, dt).z2, dt).z2 * point[axis];
        }

        let rate = match self.previous {
            Some(previous) if dt > 0.0 && dt <= GAP => (heave - previous) / dt,
            _ => 0.0,
        };

        self.previous = Some(heave);
        (heave, rate)
    }
}

// O FIRMWARE DO MRU EM SOFTWARE SOBRE UM KERNEL SIMULADO: COMANDOS, REINÍCIO, CONFIGURAÇÕES, CALIBRAÇÃO PELA SERIAL E O STREAM EM CADA MODO
struct Mru {
    settings: HashMap<String, String>,
    applied: HashMap<String, String>,
    calibration: HashMap<&'static str, Vec<f32>>,
    pending: Option<HashMap<&'static str, Vec<f32>>>,
    stored: bool,
    align: [f64; 3],
    frame: Matrix,
    powered: f64,
    booting: Option<f64>,
    active: bool,
    linked: bool,
    started: f64,
    origin: f64,
    count: u64,
    emit: f64,
    budget: f64,
    previous: Option<f64>,
    lag: [f64; 2],
    heave: Heave,
    noise: Noise,
    inbox: Vec<u8>,
    out: String,
}

impl Mru {
    fn new() -> Mru {
        let settings = DEFAULTS.iter().map(|(key, value)| (key.to_string(), value.to_string())).collect();
        let calibration = KEYS.iter().map(|(key, size)| (*key, vec![0.0f32; *size])).collect();
        let host = now();
        Mru { applied: HashMap::new(), settings, calibration, pending: None, stored: false, align: MOUNT, frame: [[0.0; 3]; 3], powered: host, booting: Some(host), active: false, linked: false, started: host, origin: host, count: 0, emit: host, budget: 0.0, previous: None, lag: [0.0; 2], heave: Heave::new(HEAVE[0], HEAVE[1]), noise: Noise(host.to_bits() | 1), inbox: Vec::new(), out: String::new() }
    }

    // O QUE VALE É O QUE O BOOT LEU DA Preferences: CS: SÓ GRAVA, O REINÍCIO APLICA
    fn get(&self, key: &str) -> f64 {
        self.applied.get(key).and_then(|value| value.parse::<f64>().ok()).unwrap_or(0.0)
    }

    fn get_baud(&self) -> u32 {
        if self.get("device_mode") == 1.0 {
            return ACQUISITION_BAUD;
        }

        self.applied.get("baudrate").and_then(|value| value.parse().ok()).unwrap_or(9600)
    }

    fn get_rate(&self) -> f64 {
        if self.get("device_mode") == 1.0 {
            return RATE;
        }

        self.get("frequency").clamp(1.0, RATE)
    }

    fn get_modes(&self) -> (u8, u8, u8) {
        let acquisition = self.get("device_mode") == 1.0;
        let streamer = if acquisition { 2 } else { self.get("streamer_mode") as u8 };
        let protocol = if acquisition { 1 } else { self.get("protocol") as u8 };
        (streamer, protocol, if acquisition { 0 } else { self.get("kernel_mode") as u8 })
    }

    fn say(&mut self, line: &str) {
        self.out.push_str(line);
        self.out.push_str("\r\n");
    }

    fn restart(&mut self, message: Option<&str>) {
        if let Some(message) = message {
            self.say(message);
        }

        self.booting = Some(now());
        self.active = false;
    }

    // O align GRAVADO GIRA A CAIXA FÍSICA PARA OS EIXOS DE SAÍDA: SÓ COM ELE IGUAL À MONTAGEM O KERNEL SAI NOS EIXOS DO CONVÉS
    fn boot(&mut self, host: f64) {
        let mount = product(&rotation(MOUNT[0], MOUNT[1], MOUNT[2]), &rotation(MISALIGNMENT[0], MISALIGNMENT[1], MISALIGNMENT[2]));
        self.frame = product(&rotation(self.align[0], self.align[1], self.align[2]), &transpose(&mount));
        self.booting = None;
        self.applied = self.settings.clone();
        self.linked = self.get("output") == 3.0;
        self.active = self.get("device_mode") == 1.0 || self.get("autostream") == 1.0 || self.applied.get("autostream").is_some_and(|value| value == "true");
        self.heave = Heave::new(self.get_heave(0, HEAVE[0]), self.get_heave(1, HEAVE[1]));
        (self.started, self.origin, self.count, self.emit, self.previous) = (host, host, 0, host, None);
    }

    fn get_heave(&self, index: usize, fallback: f64) -> f64 {
        let value = self.calibration[["HEAVE_PERIOD", "HEAVE_DAMPING"][index]][0] as f64;
        if value > 0.0 { value } else { fallback }
    }

    fn get_chain(&self) -> String {
        let (streamer, _, kernel) = self.get_modes();

        if streamer == 1 || kernel == 1 {
            return "kernel scale".to_string();
        }

        if streamer == 2 {
            return "kernel scale + heave + lever".to_string();
        }

        let model = ["kalman_fusion", "linear_fit", "machine_learning"][(self.calibration["ATTITUDE_MODEL"][0] as usize).min(2)];
        format!("{model} + filters + correction + heave + lever")
    }

    fn get_status(&self) -> String {
        let (streamer, protocol, kernel) = self.get_modes();
        json!({"id": ID, "firmware": FIRMWARE, "port": "RS232", "baud": self.get_baud(), "device_mode": self.get("device_mode"), "streamer_mode": streamer, "protocol": protocol, "kernel_mode": kernel, "frequency": self.get_rate(), "autostream": self.get("autostream") == 1.0, "streaming": self.active, "sensor": true, "kernel_baud": ACQUISITION_BAUD, "processing": self.get_chain(), "calibration": if self.stored { "flash" } else { "firmware" }, "model": self.calibration["ATTITUDE_MODEL"][0], "align": self.align, "simulated": true}).to_string()
    }

    fn get_check(&self) -> String {
        let source = self.pending.as_ref().unwrap_or(&self.calibration);
        let keys: serde_json::Map<String, Value> = KEYS.iter().map(|(key, size)| {
            let bytes: Vec<u8> = source[key].iter().flat_map(|value| value.to_le_bytes()).collect();
            (key.to_string(), json!([size, format!("{:X}", crc32(&bytes))]))
        }).collect();
        json!({"source": if self.stored { "flash" } else { "firmware" }, "staging": self.pending.is_some(), "model": source["ATTITUDE_MODEL"][0], "keys": keys}).to_string()
    }

    // A MESMA ORDEM DE DESPACHO DO Protocol::check DO FIRMWARE; O COMANDO CHEGOU PELO RS232, QUE PASSA A RECEBER O STREAM
    fn respond(&mut self, command: &str) {
        self.linked = true;

        let field = |start: char, end: char| -> Option<(String, String)> {
            let (a, b) = (command.find(start)?, command.find(end)?);
            let mid = command.find('$')?;
            (a < mid && mid <= b).then(|| (command[a + 1..mid].to_string(), command[mid + 1..b].to_string()))
        };

        if command.contains("MICRS") {
            return self.restart(None);
        }

        if command.contains("CL:") {
            let response = match field(':', '!') {
                Some((key, values)) => self.set_calibration(&key, &values),
                None => "$ERROR!".to_string(),
            };

            return self.say(&response);
        }

        if command.contains("CS:") || command.contains("F:") {
            let reboot = !command.contains("CS:");
            let Some((key, value)) = field(':', '!') else { return self.say("NONE") };
            self.settings.insert(key.clone(), value.clone());

            if reboot {
                return self.restart(Some(&format!("{key} set to {value}")));
            }

            return self.say(&format!("$OK:{key}={value}!"));
        }

        if command.contains("calibration_save") {
            if let Some(pending) = self.pending.take() {
                self.calibration = pending;
            }

            self.stored = true;
            return self.restart(Some("$CALIBRATION SAVED!"));
        }

        if command.contains("calibration_erase") {
            self.calibration = KEYS.iter().map(|(key, size)| (*key, vec![0.0f32; *size])).collect();
            self.pending = None;
            self.stored = false;
            return self.restart(Some("$CALIBRATION ERASED!"));
        }

        if command.contains("calibration_check") {
            let check = self.get_check();
            return self.say(&check);
        }

        if command.contains("status") {
            let status = self.get_status();
            return self.say(&status);
        }

        if command.contains("D:") {
            let key = command.split_once(':').map(|(_, rest)| rest.trim_end_matches('$')).unwrap_or_default().to_string();
            let response = self.settings.get(&key).map_or("ERROR".to_string(), |value| format!("${value}!"));
            return self.say(&response);
        }

        if command.contains("firmware") {
            return self.say(FIRMWARE);
        }

        if command.contains("stream_start") {
            if !self.active {
                self.started = now();
            }

            self.active = true;
            return;
        }

        if command.contains("stream_stop") {
            self.active = false;
            return;
        }

        if command.contains("calibrate") {
            let chain = self.get_chain();
            return self.say(&chain);
        }

        if command.contains("check_sensor") {
            return self.say("OK");
        }

        if command.contains("align") {
            let preset = command.split_once(':').and_then(|(_, rest)| rest.trim_end_matches('!').parse::<u8>().ok()).unwrap_or(0);
            self.align = match preset { 1 => [0.0, -90.0, 0.0], 2 => [0.0, 90.0, 0.0], 4 => [180.0, 0.0, 180.0], _ => [0.0, 0.0, 0.0] };
            return self.say(&format!("ALIGNMENT COMPLETE: {preset}"));
        }

        if command.contains("ackoneledge") {
            return self.say("$MICACK!");
        }

        if command.contains("settings") {
            let settings = json!(self.settings).to_string();
            return self.say(&settings);
        }

        if command.contains("$ERASE!") {
            self.settings = DEFAULTS.iter().map(|(key, value)| (key.to_string(), value.to_string())).collect();
            self.restart(None);
        }
    }

    fn set_calibration(&mut self, key: &str, values: &str) -> String {
        let (name, offset) = key.split_once('@').map_or((key, 0), |(name, offset)| (name, offset.parse().unwrap_or(usize::MAX)));
        let Some((name, size)) = KEYS.iter().find(|(candidate, _)| *candidate == name).copied() else { return format!("$ERROR:{name}!") };
        let parsed: Result<Vec<f32>, _> = values.split(',').map(|value| value.trim().parse::<f32>()).collect();

        let parsed = match parsed {
            Ok(parsed) if !parsed.is_empty() && offset.saturating_add(parsed.len()) <= size => parsed,
            _ => return format!("$ERROR:{name}!"),
        };

        let pending = self.pending.get_or_insert_with(|| self.calibration.clone());
        pending.get_mut(name).unwrap()[offset..offset + parsed.len()].copy_from_slice(&parsed);
        format!("$OK:{name}@{offset}+{}!", parsed.len())
    }

    // UM PACOTE DO KERNEL NO INSTANTE time: SENSOR COM ESCALA, VIÉS, DERIVA TÉRMICA E RUÍDO NOS EIXOS DE SAÍDA, AHRS COM ATRASO, E O HEAVE DO FIRMWARE
    fn get_sample(&mut self, motion: &Motion, time: f64) -> String {
        let truth = measure(motion, time);
        let dt = self.previous.map_or(0.0, |previous| time - previous);
        self.previous = Some(time);

        let temperature = TEMPERATURE[0] + TEMPERATURE[1] * (1.0 - (-(time - self.powered).max(0.0) / TEMPERATURE[2]).exp());
        let delta = temperature - TEMPERATURE[0];
        let (accel, gyro) = (apply(&self.frame, truth.accel), apply(&self.frame, truth.gyro));
        let accel = [0, 1, 2].map(|i| ACCEL_SCALE[i] * accel[i] + ACCEL_BIAS[i] + ACCEL_DRIFT[i] * delta + self.noise.gauss(ACCEL_NOISE[i]));
        let gyro = [0, 1, 2].map(|i| GYRO_SCALE[i] * gyro[i] + GYRO_BIAS[i] + GYRO_DRIFT[i] * delta + self.noise.gauss(GYRO_NOISE[i]));

        let output = product(&truth.c, &transpose(&self.frame));
        let [pitch, roll, heading] = get_euler(&output);
        let alpha = if dt > 0.0 && dt <= GAP { dt / (ANGLE_LAG + dt) } else { 1.0 };
        self.lag = [0, 1].map(|k| wrap(self.lag[k] + alpha * wrap([pitch, roll][k] - self.lag[k])));
        let angles = [self.lag[0] + ANGLE_BIAS[0] + self.noise.gauss(ANGLE_NOISE[0]), wrap(self.lag[1] + ANGLE_BIAS[1] + self.noise.gauss(ANGLE_NOISE[1])), (heading + self.noise.gauss(ANGLE_NOISE[2])).rem_euclid(360.0)];

        let (streamer, protocol, kernel) = self.get_modes();
        let ship = |v: [f64; 3]| [v[1], v[0], -v[2]];
        let point = [0, 1, 2].map(|i| self.calibration["LEVER_POINT"][i] as f64);
        let pose = truth.pose;
        let (input, tilt) = if streamer == 2 { (ship(accel), [angles[0], angles[1]]) } else { (ship(truth.accel), [pose.pitch, pose.roll]) };
        let (heave, rate) = self.heave.update(input, tilt[0], tilt[1], point, dt);

        let calibrated = [0, 1, 2].map(|k| [pose.pitch, pose.roll, pose.heading.rem_euclid(360.0)][k] + self.noise.gauss(0.5 * ANGLE_NOISE[k]));
        let (truth_ship, rate_ship, accel_noise, gyro_noise) = (ship(truth.accel), ship(truth.gyro), ship(ACCEL_NOISE), ship(GYRO_NOISE));
        let accel_ship = [0, 1, 2].map(|i| truth_ship[i] + self.noise.gauss(0.5 * accel_noise[i]));
        let gyro_ship = [0, 1, 2].map(|i| rate_ship[i] + self.noise.gauss(0.5 * gyro_noise[i]));
        let temperature = (temperature * 10.0).round() / 10.0;
        let stamp = ((time - self.started) * 1000.0).round() / 1000.0 + if self.noise.get() < LATE { 1e-3 } else { 0.0 };

        let (keys, values): (Vec<&str>, Vec<f64>) = match (streamer, kernel) {
            (_, 1) => {
                let q = quaternion(&output);
                (vec!["tmp", "pitch", "roll", "yaw", "q0", "q1", "q2", "q3", "heave"], vec![temperature, angles[0], angles[1], angles[2], q[0], q[1], q[2], q[3], if streamer == 1 { 0.0 } else { heave }])
            }
            (1, _) => {
                let (a, w, angle) = if kernel == 2 { (4000.0 / G0, 50.0, 100.0) } else { (1e6 / G0, 1e5, 1e3) };
                (vec!["tmp", "pitch", "roll", "yaw", "ax", "ay", "az", "wx", "wy", "wz", "heave"], vec![(temperature * 10.0).round(), (angles[0] * angle).round(), (angles[1] * angle).round(), (angles[2] * angle).round(), (accel[0] * a).round(), (accel[1] * a).round(), (accel[2] * a).round(), (gyro[0] * w).round(), (gyro[1] * w).round(), (gyro[2] * w).round(), 0.0])
            }
            (0, _) => (vec!["tmp", "pitch", "roll", "yaw", "ax", "ay", "az", "wx", "wy", "wz", "heave", "heave_rate"], vec![temperature, calibrated[0], calibrated[1], calibrated[2], accel_ship[0], accel_ship[1], accel_ship[2], gyro_ship[0], gyro_ship[1], gyro_ship[2], heave, rate]),
            _ => (vec!["tmp", "pitch", "roll", "yaw", "ax", "ay", "az", "wx", "wy", "wz", "heave", "heave_rate"], vec![temperature, angles[0], angles[1], angles[2], accel[0], accel[1], accel[2], gyro[0], gyro[1], gyro[2], heave, rate]),
        };

        let digits = if streamer == 1 { 0 } else { 3 };

        if protocol == 2 {
            let heave = values[keys.iter().position(|key| *key == "heave").unwrap()];
            let sentence = format!("GPPASHR,{:.*},{:.*},{:.*},{:.*}", digits, values[1], digits, values[2], digits, values[3], digits, heave);
            let checksum = sentence.bytes().fold(0u8, |parity, byte| parity ^ byte);
            return format!("${sentence}*{checksum:02X}");
        }

        if protocol == 0 {
            let fields: Vec<String> = keys.iter().zip(&values).map(|(key, value)| format!("\"{key}\":{value:.digits$}")).collect();
            return format!("{{\"time\":{stamp:.3},{}}}", fields.join(","));
        }

        let fields: Vec<String> = values.iter().map(|value| format!("{value:.digits$}")).collect();
        format!("[{stamp:.3},{}]", fields.join(","))
    }

    // O KERNEL ANDA A 200 Hz MESMO SEM STREAM; NO NORMAL O STREAM DECIMA NA frequency E A UART DESCARTA O QUE O BAUD NÃO DÁ CONTA
    fn update(&mut self, motion: &Motion, received: &[u8]) -> String {
        let host = now();
        self.inbox.extend_from_slice(received);

        if self.booting.is_some_and(|started| host - started >= BOOT) {
            self.inbox.clear();
            self.boot(host);
        }

        while let Some(position) = self.inbox.iter().position(|byte| *byte == b'\n') {
            let line: Vec<u8> = self.inbox.drain(..=position).collect();
            let command = String::from_utf8_lossy(&line).replace(['\r', '\n', '\t'], "");

            if command.len() >= 3 && self.booting.is_none() {
                self.respond(&command);
            }
        }

        if self.booting.is_some() {
            return std::mem::take(&mut self.out);
        }

        let (period, capacity, acquisition) = (1.0 / RATE, self.get_baud() as f64 / 10.0, self.get("device_mode") == 1.0);
        self.count = self.count.max(((host - 1.0 - self.origin) / period).ceil().max(0.0) as u64);    // PC ATRASADO: PULA EM VEZ DE DESPEJAR UM SEGUNDO DE UMA VEZ

        loop {
            let time = self.origin + self.count as f64 * period;    // ORIGEM MAIS n PERÍODOS: SOMAR 5 ms A UM TEMPO DE 1,8e9 s ACUMULA ERRO DE PONTO FLUTUANTE

            if time > host {
                break;
            }

            self.count += 1;
            self.budget = (self.budget + capacity * period).min((capacity * BUFFER).max(TX_BUFFER));

            if self.noise.get() < LOSS {
                continue;
            }

            let sample = self.get_sample(motion, time);

            if !self.active || !self.linked || (!acquisition && time < self.emit) {
                continue;
            }

            self.emit = time + 1.0 / self.get_rate() - 1e-6;    // O Listener DO FIRMWARE REANCORA NO AGORA

            if (sample.len() + 1) as f64 > self.budget {
                continue;
            }

            self.budget -= (sample.len() + 1) as f64;
            self.say(&sample);
        }

        std::mem::take(&mut self.out)
    }
}

// O Table.ino EM SOFTWARE: home() DEPOIS DO RESET DA ABERTURA DA PORTA, ESPERA O start E IMPRIME TEMPO, PITCH E ROLL A 100 Hz
struct Table {
    booting: Option<f64>,
    started: f64,
    count: u64,
    inbox: Vec<u8>,
    out: String,
}

impl Table {
    fn new() -> Table {
        let host = now();
        Table { booting: Some(host), started: host, count: 0, inbox: Vec::new(), out: String::new() }
    }

    fn update(&mut self, motion: &mut Motion, received: &[u8]) -> String {
        let host = now();
        self.inbox.extend_from_slice(received);

        if self.booting.is_some_and(|started| host - started >= TABLE_HOMING) {
            (self.booting, self.started, self.count) = (None, host, 0);
            self.inbox.clear();
        }

        while let Some(position) = self.inbox.iter().position(|byte| *byte == b'\n') {
            let command = String::from_utf8_lossy(&self.inbox.drain(..=position).collect::<Vec<u8>>()).to_string();

            if command.contains("reset") {
                self.booting = Some(host);
                continue;
            }

            if command.contains("home") {
                (self.started, self.count) = (host, 0);
                continue;
            }

            if command.contains("stop") {
                motion.cycle();
                continue;
            }

            if command.contains("start") {
                motion.release(Some(host));
            }
        }

        if self.booting.is_some() {
            return String::new();
        }

        self.count = self.count.max(((host - 1.0 - self.started) * TABLE_RATE).ceil().max(0.0) as u64);
        let step = |angle: f64| (angle * TABLE_STEPS).round() / TABLE_STEPS;

        while self.started + self.count as f64 / TABLE_RATE <= host {
            let time = self.started + self.count as f64 / TABLE_RATE;
            let pose = motion.get(time);
            self.out.push_str(&format!("{{\"t\":{:.3},\"pitch\":{:.2},\"roll\":{:.2}}}\n", time - self.started, step(pose.pitch) as f32, step(pose.roll) as f32));    // O print() DO Table.ino FORMATA float
            self.count += 1;
        }

        std::mem::take(&mut self.out)
    }
}

// O BANCO SIMULADO: MRU E MESA DIVIDEM O MOVIMENTO E CONTINUAM LIGADOS COM A PORTA FECHADA, ENQUANTO A SIMULAÇÃO ESTIVER LIGADA
pub struct Rig {
    pub enabled: AtomicBool,
    motion: Mutex<Motion>,
    mru: Mutex<Mru>,
    table: Mutex<Table>,
}

impl Rig {
    pub fn new() -> Rig {
        Rig { enabled: AtomicBool::new(false), motion: Mutex::new(Motion::new("table", None)), mru: Mutex::new(Mru::new()), table: Mutex::new(Table::new()) }
    }

    pub fn get(&self) -> Value {
        let motion = self.motion.lock().unwrap();
        json!({"enabled": self.enabled.load(Ordering::SeqCst), "scenario": motion.scenario, "moving": motion.scenario != "still"})
    }

    // LIGAR A SIMULAÇÃO É LIGAR O MRU, QUE GUARDA NA FLASH CONFIGURAÇÕES, CALIBRAÇÃO E ALIGN; NA PLATAFORMA SEM A MESA DO APP, O PROGRAMA ANDA SOZINHO
    pub fn set(&self, enabled: bool, scenario: &str) {
        if enabled && !self.enabled.swap(true, Ordering::SeqCst) {
            let mut mru = self.mru.lock().unwrap();
            mru.powered = now();
            mru.restart(None);
            self.motion.lock().unwrap().cycle();
        }

        self.enabled.store(enabled, Ordering::SeqCst);
        let mut motion = self.motion.lock().unwrap();

        if motion.scenario != scenario {
            motion.scenario = scenario.to_string();
            motion.cycle();
        }
    }

    pub fn reset(&self) {
        *self.mru.lock().unwrap() = Mru::new();
    }

    // A GRAVAÇÃO SEM A MESA DO APP RECOMEÇA O PROGRAMA DA PLATAFORMA DO MRU SIMULADO, COMO O start FARIA NA MESA
    pub fn start(&self) {
        self.motion.lock().unwrap().release(Some(now()));
    }

    fn open(&self, table: bool) {
        if table {
            *self.table.lock().unwrap() = Table::new();
        }
    }

    // O QUE O APARELHO TRANSMITIU DESDE A ÚLTIMA LEITURA E O BAUD DA UART DELE; COMANDO EM OUTRO BAUD NÃO CHEGA INTEIRO
    fn update(&self, table: bool, received: &[u8], baud: u32) -> (String, u32) {
        let mut motion = self.motion.lock().unwrap();

        if table {
            let fed = if baud == TABLE_BAUD { received } else { &[] };
            return (self.table.lock().unwrap().update(&mut motion, fed), TABLE_BAUD);
        }

        let mut mru = self.mru.lock().unwrap();
        let uart = mru.get_baud();
        let fed = if baud == uart { received } else { &[] };
        (mru.update(&motion, fed), uart)
    }
}

// A PORTA FICTÍCIA: LÊ O QUE O APARELHO SIMULADO TRANSMITIU, VIRADO LIXO SE O BAUD ABERTO NÃO FOR O DA UART DELE
struct SimPort {
    rig: Arc<Rig>,
    table: bool,
    baud: u32,
    inbox: Arc<Mutex<Vec<u8>>>,
    pending: Vec<u8>,
    noise: Noise,
}

impl Read for SimPort {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        let deadline = Instant::now() + READ;

        while self.pending.is_empty() {
            if !self.rig.enabled.load(Ordering::SeqCst) {
                return Err(io::Error::new(ErrorKind::BrokenPipe, "a simulação foi desligada"));
            }

            let received = std::mem::take(&mut *self.inbox.lock().unwrap());
            let (output, uart) = self.rig.update(self.table, &received, self.baud);

            if output.is_empty() {
                if Instant::now() >= deadline {
                    return Err(io::Error::from(ErrorKind::TimedOut));
                }

                thread::sleep(POLL);
                continue;
            }

            let count = (output.len() as f64 * (self.baud as f64 / uart as f64).min(1.0)).ceil() as usize;
            self.pending = if uart == self.baud { output.into_bytes() } else { (0..count).map(|_| (self.noise.get() * 256.0) as u8).collect() };
        }

        let count = buffer.len().min(self.pending.len());
        buffer[..count].copy_from_slice(&self.pending[..count]);
        self.pending.drain(..count);
        Ok(count)
    }
}

struct SimWriter(Arc<Mutex<Vec<u8>>>);

impl Write for SimWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.0.lock().unwrap().extend_from_slice(bytes);
        Ok(bytes.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

pub type Link = (Box<dyn Read + Send>, Box<dyn Write + Send>);

pub fn open(rig: &Arc<Rig>, table: bool, baud: u32) -> io::Result<Link> {
    if !rig.enabled.load(Ordering::SeqCst) {
        return Err(io::Error::new(ErrorKind::NotFound, "a simulação está desligada em Ajustes"));
    }

    rig.open(table);
    let inbox = Arc::new(Mutex::new(Vec::new()));
    let port = SimPort { rig: rig.clone(), table, baud, inbox: inbox.clone(), pending: Vec::new(), noise: Noise(now().to_bits() | 3) };
    Ok((Box::new(port), Box::new(SimWriter(inbox))))
}

fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = 0xFFFFFFFFu32;

    for byte in bytes {
        crc ^= *byte as u32;

        for _ in 0..8 {
            crc = (crc >> 1) ^ (0xEDB88320 & 0u32.wrapping_sub(crc & 1));
        }
    }

    !crc
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::packet::{self, Format, Layout, Line};

    fn booted(settings: &[(&str, &str)]) -> Mru {
        let mut mru = Mru::new();

        for (key, value) in settings {
            mru.settings.insert(key.to_string(), value.to_string());
        }

        mru.boot(now());
        mru
    }

    fn still() -> Motion {
        Motion::new("still", None)
    }

    fn parse(line: &str) -> (Layout, Format) {
        match packet::parse(line.as_bytes()) {
            Some(Line::Packet(sample)) => (sample.layout, sample.format),
            other => panic!("amostra ilegível: {other:?} em {line}"),
        }
    }

    #[test]
    fn cada_modo_sai_no_layout_que_o_parser_reconhece() {
        let cases = [
            (vec![("streamer_mode", "2"), ("protocol", "1")], Layout::Scale, Format::List),
            (vec![("streamer_mode", "0"), ("protocol", "0")], Layout::Calibrated, Format::Json),
            (vec![("streamer_mode", "1"), ("protocol", "1")], Layout::Raw, Format::List),
            (vec![("streamer_mode", "1"), ("protocol", "1"), ("kernel_mode", "2")], Layout::Raw, Format::List),
            (vec![("streamer_mode", "0"), ("kernel_mode", "1"), ("protocol", "1")], Layout::Quaternion, Format::List),
            (vec![("streamer_mode", "0"), ("protocol", "2")], Layout::Nmea, Format::Nmea),
            (vec![("device_mode", "1"), ("protocol", "0")], Layout::Scale, Format::List),
        ];

        for scenario in ["ship", "table", "still"] {
            let motion = Motion::new(scenario, Some(now() - 130.0));

            for (settings, expected, format) in &cases {
                let mut mru = booted(settings);

                for second in 0..60 {
                    let line = mru.get_sample(&motion, mru.started + second as f64 * 0.37);
                    assert_eq!(parse(&line), (*expected, *format), "{settings:?} em {second} s no cenário {scenario}");
                }
            }
        }
    }

    #[test]
    fn angulos_voltam_da_matriz_na_convencao_do_icd() {
        for (heading, pitch, roll) in [(0.0, 0.0, 0.0), (30.0, 12.0, -7.0), (250.0, -40.0, 170.0), (359.0, 5.0, -178.0)] {
            let [p, r, h] = get_euler(&rotation(heading, pitch, roll));
            assert!((p - pitch).abs() < 1e-9 && wrap(r - roll).abs() < 1e-9 && wrap(h - heading).abs() < 1e-9, "{heading} {pitch} {roll} voltou {h} {p} {r}");
        }
    }

    #[test]
    fn gravidade_e_braco_batem_com_a_pose() {
        let motion = Motion::new("still", None);
        let truth = measure(&motion, 1234.5);
        assert!((truth.accel[2] - GRAVITY).abs() < 1e-6 && truth.accel[0].abs() < 1e-6, "{:?}", truth.accel);

        let motion = Motion::new("table", Some(1000.0));
        let time = 1000.0 + STILL + 30.83;    // PERTO DO PICO DO PITCH: θ̈ GRANDE, O BRAÇO APARECE
        let truth = measure(&motion, time);
        let (p, r) = (truth.pose.pitch.to_radians(), truth.pose.roll.to_radians());
        let tilt = [-p.cos() * r.sin(), p.sin(), p.cos() * r.cos()].map(|value| value * GRAVITY);
        let arm = [0, 1, 2].map(|i| truth.accel[i] - tilt[i]);
        let rate = (motion.get(time + 1e-3).pitch - motion.get(time - 1e-3).pitch).to_radians() / 2e-3;
        let accel = (motion.get(time + 1e-3).pitch - 2.0 * truth.pose.pitch + motion.get(time - 1e-3).pitch).to_radians() / 1e-6;
        assert!(accel.abs() > 0.5 && (arm[1] + PIVOT[2] * accel).abs() < 0.01, "o Kernel acima do eixo vai para ré quando a proa acelera para cima: tangencial {} contra {}", arm[1], -PIVOT[2] * accel);
        assert!((arm[2] + PIVOT[2] * rate * rate).abs() < 0.01, "centrípeta {} contra {}", arm[2], -PIVOT[2] * rate * rate);
    }

    #[test]
    fn kernel_parado_tem_o_ruido_do_test3() {
        let mut mru = booted(&[("device_mode", "1")]);
        let motion = still();
        let values: Vec<Vec<f64>> = (0..2000).map(|n| {
            let line = mru.get_sample(&motion, mru.started + n as f64 / RATE);
            line.trim_matches(['[', ']']).split(',').map(|value| value.parse().unwrap()).collect()
        }).collect();

        let sigma = |column: usize| {
            let mean = values.iter().map(|row| row[column]).sum::<f64>() / values.len() as f64;
            (values.iter().map(|row| (row[column] - mean).powi(2)).sum::<f64>() / values.len() as f64).sqrt()
        };

        for i in 0..3 {
            assert!((sigma(5 + i) / ACCEL_NOISE[i] - 1.0).abs() < 0.15, "σ do acelerômetro {i}: {}", sigma(5 + i));
            assert!((sigma(8 + i) / GYRO_NOISE[i] - 1.0).abs() < 0.15, "σ do giro {i}: {}", sigma(8 + i));
        }

        let steps: Vec<f64> = values.windows(2).map(|pair| ((pair[1][0] - pair[0][0]) * 1000.0).round()).collect();
        let share = |step: f64| steps.iter().filter(|value| **value == step).count() as f64 / steps.len() as f64;
        assert!((share(5.0) - 0.81).abs() < 0.04 && (share(4.0) - 0.096).abs() < 0.03 && (share(6.0) - 0.096).abs() < 0.03, "passos de 4, 5 e 6 ms: {} {} {}", share(4.0), share(5.0), share(6.0));

        let az = values.iter().map(|row| row[7]).sum::<f64>() / values.len() as f64;
        assert!((az - GRAVITY).abs() < 0.1, "em pé com o align certo, a gravidade fica em Z: {az}");
    }

    #[test]
    fn baud_errado_vira_lixo_e_o_certo_responde() {
        let rig = Arc::new(Rig::new());
        rig.set(true, "still");
        rig.mru.lock().unwrap().booting = Some(now() - BOOT);

        let ask = |baud: u32| {
            let (mut reader, mut writer) = open(&rig, false, baud).unwrap();
            writer.write_all(b"$ackoneledge!\r\n").unwrap();
            let mut bytes = Vec::new();
            let mut buffer = [0u8; 4096];
            let start = Instant::now();

            while start.elapsed() < Duration::from_millis(150) {
                if let Ok(count) = reader.read(&mut buffer) {
                    bytes.extend_from_slice(&buffer[..count]);
                }
            }

            String::from_utf8_lossy(&bytes).to_string()
        };

        assert!(!ask(9600).contains("$MICACK!"), "a 9600 o MRU simulado de fábrica (115200) não entende o ACK");
        assert!(ask(115200).contains("$MICACK!"));
    }

    #[test]
    fn stream_respeita_frequencia_e_banda() {
        let motion = still();
        let mut mru = booted(&[("autostream", "1"), ("protocol", "1"), ("frequency", "10"), ("baudrate", "115200")]);
        (mru.origin, mru.count) = (now() - 2.0, 0);
        mru.emit = mru.origin;
        let lines = mru.update(&motion, &[]).lines().filter(|line| line.starts_with('[')).count();
        assert!((9..=11).contains(&lines), "10 Hz por 1 s (o PC atrasado pula o resto): {lines}");

        let mut slow = booted(&[("autostream", "1"), ("protocol", "0"), ("frequency", "100"), ("baudrate", "9600")]);
        let mut total = 0;
        (slow.origin, slow.count) = (now(), 0);

        for _ in 0..50 {
            thread::sleep(Duration::from_millis(20));
            total += slow.update(&motion, &[]).lines().count();
        }

        assert!((2..12).contains(&total), "JSON a 100 Hz em 9600 bps sai a ~4 linhas/s, não 100 nem 0: {total} linhas em 1 s");
    }

    #[test]
    fn programa_da_mesa_para_20_s_e_cicla() {
        let motion = Motion::new("table", Some(1000.0));
        let swing = |time: f64| { let pose = motion.get(1000.0 + time); (pose.pitch.abs() > 1.0, pose.roll.abs() > 1.0) };
        assert_eq!([swing(10.0), swing(19.9)], [(false, false); 2], "parada nos 20 s depois do start");
        assert!([45.6, 61.2, 88.0].iter().any(|time| swing(*time).0), "pitch de 20 a 120 s");
        assert!([145.6, 161.2, 188.0].iter().any(|time| swing(*time).1), "roll de 120 a 220 s");
        assert!([230.0, 260.0, 310.0].iter().all(|time| swing(*time) == (false, false)), "repouso de 220 a 320 s");
        assert!([345.6, 361.2, 388.0].iter().any(|time| swing(*time).0), "o ciclo recomeça no pitch");
    }

    #[test]
    fn mesa_segue_o_alvo_como_o_motor_de_passo() {
        let motion = Motion::new("table", Some(0.0));
        let pitch = |local: f64| motion.get(STILL + local).pitch;
        let behind = pitch(10.0);
        assert!((-2.6..-2.0).contains(&behind), "no cruzamento do alvo subindo o motor vem até v²/2a atrás: {behind}");
        let peak = (0..100_000).map(|n| pitch(n as f64 * 1e-3).abs()).fold(0.0, f64::max);
        assert!((peak - AMPLITUDE).abs() < 0.05, "mas chega ao pico de {AMPLITUDE}°: {peak}");
        let curvature = |time: f64| (motion.get(time + 1e-3).pitch - 2.0 * motion.get(time).pitch + motion.get(time - 1e-3).pitch) / 1e-6;
        assert!((curvature(STILL + 21.37) + 28.0).abs() < 2.0, "fora dos picos a mesa acelera como a senoide, sem a trepidação do motor: {}", curvature(STILL + 21.37));
    }

    #[test]
    fn mesa_imprime_como_o_table_ino() {
        let mut motion = Motion::new("table", None);
        let mut table = Table::new();
        table.booting = Some(now() - TABLE_HOMING);
        table.update(&mut motion, b"start\n");
        assert!(motion.released.is_none(), "o que chega durante o home() se perde");
        thread::sleep(Duration::from_millis(30));
        let output = table.update(&mut motion, b"start\n");
        let line = output.lines().last().unwrap();
        assert!(line.starts_with("{\"t\":") && line.contains("\"pitch\":") && line.split("\"roll\":").nth(1).unwrap().trim_end_matches('}').split('.').nth(1).unwrap().len() == 2, "{line}");
        assert!(motion.released.is_some(), "o start solta a mesa");
        assert_eq!(parse(line).0, Layout::Table);
        table.update(&mut motion, b"stop\n");
        assert!(motion.released.is_some_and(|released| now() - released >= STILL), "o stop devolve a plataforma simulada ao ciclo livre, sem os 20 s parados");
    }

    #[test]
    fn troca_de_programa_nao_salta() {
        let mut motion = Motion::new("table", Some(now() - STILL - 4.0));
        let before = motion.get(now()).pitch;
        assert!(before.abs() > 1.0, "o ciclo livre já balança em pitch: {before}");
        motion.release(Some(now()));
        let host = now();
        let steps: Vec<f64> = (0..=400).map(|n| motion.get(host + n as f64 * 0.005).pitch).collect();
        let jump = steps.windows(2).map(|pair| (pair[1] - pair[0]).abs()).fold(0.0, f64::max);
        assert!(jump < 0.5, "a rampa leva o pitch a zero sem salto: {jump} graus em 5 ms");
        assert!(steps[steps.len() - 1].abs() < 1e-9, "depois da rampa a mesa está parada para o trecho static");
    }

    #[test]
    fn comandos_respondem_como_o_firmware() {
        let motion = still();
        let mut mru = booted(&[]);
        let mut ask = |command: &str| mru.update(&motion, format!("{command}\r\n").as_bytes());

        assert!(ask("$ackoneledge!").contains("$MICACK!"));
        assert!(ask("CS:protocol$2!").contains("$OK:protocol=2!"));
        assert!(ask("CL:FILTERS_FC$1.5,2,3,4,5,6!").contains("$OK:FILTERS_FC@0+6!"));
        assert!(ask("CL:FILTERS_FC@5$1,2!").contains("$ERROR:FILTERS_FC!"));
        assert!(ask("CL:NOPE$1!").contains("$ERROR:NOPE!"));

        let check = ask("$calibration_check!");
        let crc = serde_json::from_str::<Value>(check.trim()).unwrap()["keys"]["FILTERS_FC"][1].as_str().unwrap().to_string();
        let bytes: Vec<u8> = [1.5f32, 2.0, 3.0, 4.0, 5.0, 6.0].iter().flat_map(|value| value.to_le_bytes()).collect();
        assert_eq!(crc, format!("{:X}", crc32(&bytes)));

        let status: Value = serde_json::from_str(ask("$status!").lines().find(|line| line.starts_with('{')).unwrap()).unwrap();
        assert_eq!(status["firmware"], FIRMWARE);
        assert_eq!(status["baud"], 115200);
        assert!(ask("$calibration_save!").contains("$CALIBRATION SAVED!"));
        assert!(ask("$ackoneledge!").is_empty(), "reiniciando não responde");
    }
}
