import { useEffect, useRef } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { version } from '../../package.json'

export const APP_VERSION = `v${version}`
export const CHANNELS    = ['time', 'tmp', 'pitch', 'roll', 'yaw', 'ax', 'ay', 'az', 'wx', 'wy', 'wz', 'heave', 'heave_rate', 'q0', 'q1', 'q2', 'q3']
export const BAUDS       = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
export const FREQUENCIES = [1, 2, 5, 10, 20, 25, 50, 100, 200]
export const ACQUISITION_BAUD = 460800    // RS232/RS422 NA AQUISIÇÃO (ACQUISITION_BAUD DO FIRMWARE)
export const STILL = 20                   // s DE MRU PARADO ANTES DE LIBERAR A PLATAFORMA DE REFERÊNCIA

export const DEVICE_MODES   = [{value: 0, label: 'Normal'}, {value: 1, label: 'Aquisição'}]
export const STREAMER_MODES = [{value: 0, label: 'CALIBRATED'}, {value: 1, label: 'RAW'}, {value: 2, label: 'SCALE'}]
export const KERNEL_MODES   = [{value: 0, label: 'HR'}, {value: 1, label: 'QT'}, {value: 2, label: 'OR'}]
export const PROTOCOLS      = [{value: 2, label: 'NMEA ($GPPASHR)'}, {value: 1, label: 'LIST'}, {value: 0, label: 'JSON'}]
export const OUTPUTS        = [{value: 3, label: 'RS232'}, {value: 2, label: 'RS422'}, {value: 1, label: 'USB'}]
export const MODELS         = ['KalmanFusion', 'LinearFit', 'MachineLearning']
export const LINE_BYTES     = {0: 210, 1: 95, 2: 46}    // bytes POR LINHA EM JSON, LIST E NMEA, COM O \n

export const ALIGNS = [
    {value: 1, angles: [0, -90, 0], label: 'Em pé · cabo para cima (preset 1)'},
    {value: 2, angles: [0, 90, 0], label: 'Cabeça para baixo (preset 2)'},
    {value: 0, angles: [0, 0, 0], label: 'De lado · base na antepara de vante (preset 0)'},
    {value: 4, angles: [180, 0, 180], label: 'De lado · base na antepara de ré (preset 4)'}
]

export const LAYOUTS = {
    scale: {label: 'SCALE', detail: 'Kernel em unidades físicas · X boreste, Y proa, Z cima', tone: 'info'},
    calibrated: {label: 'CALIBRADO', detail: 'cadeia calibrada · x proa, y boreste, z baixo', tone: 'ok'},
    raw: {label: 'RAW', detail: 'inteiros do Kernel, convertidos para a tela', tone: 'warn'},
    quaternion: {label: 'QT', detail: 'quaternion, ângulos e temperatura', tone: 'info'},
    nmea: {label: 'NMEA', detail: '$GPPASHR: pitch, roll, yaw e heave', tone: 'info'},
    legacy: {label: 'ANTIGO', detail: 'firmware sem o campo time', tone: 'warn'},
    table: {label: 'PLATAFORMA', detail: 'referência [t, pitch, roll]', tone: 'info'}
}

export const VARIABLES = {
    tmp: {label: 'Temperatura', unit: '°C'},
    pitch: {label: 'Pitch', unit: '°'},
    roll: {label: 'Roll', unit: '°'},
    yaw: {label: 'Yaw', unit: '°'},
    ax: {label: 'ax', unit: 'm/s²'},
    ay: {label: 'ay', unit: 'm/s²'},
    az: {label: 'az', unit: 'm/s²'},
    wx: {label: 'wx', unit: '°/s'},
    wy: {label: 'wy', unit: '°/s'},
    wz: {label: 'wz', unit: '°/s'},
    heave: {label: 'Heave', unit: 'm'},
    heave_rate: {label: 'Vel. heave', unit: 'm/s'},
    q0: {label: 'q0', unit: ''},
    q1: {label: 'q1', unit: ''},
    q2: {label: 'q2', unit: ''},
    q3: {label: 'q3', unit: ''}
}

export const SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100']    // PALETA CATEGÓRICA VALIDADA, SEMPRE NESTA ORDEM

// AS GRANDEZAS DO GRÁFICO: UM EIXO POR VEZ, CADA VARIÁVEL COM A COR DA POSIÇÃO DELA NA GRANDEZA
export const QUANTITIES = [
    {key: 'attitude', label: 'Atitude', unit: '°', digits: 2, keys: ['pitch', 'roll', 'yaw'], shown: ['pitch', 'roll']},
    {key: 'heave', label: 'Heave', unit: 'm · + para baixo', digits: 3, keys: ['heave']},
    {key: 'heave_rate', label: 'Vel. heave', unit: 'm/s', digits: 3, keys: ['heave_rate']},
    {key: 'accel', label: 'Aceleração', unit: 'm/s²', digits: 3, keys: ['ax', 'ay', 'az']},
    {key: 'gyro', label: 'Giro', unit: '°/s', digits: 3, keys: ['wx', 'wy', 'wz']},
    {key: 'tmp', label: 'Temperatura', unit: '°C', digits: 1, keys: ['tmp']},
    {key: 'quaternion', label: 'Quaternion', unit: '', digits: 4, keys: ['q0', 'q1', 'q2', 'q3']}
]

export function getQuantity(key){
    return QUANTITIES.find(quantity => quantity.key == key) ?? QUANTITIES[0]
}

export function getColor(key){
    const quantity = QUANTITIES.find(item => item.keys.includes(key))
    return SERIES[quantity ? quantity.keys.indexOf(key) : 0]
}

// RAW DO HR E DO OR PARA m/s², °/s, ° E °C: OS FATORES DO KernelSensor::SCALE
const RAW_SCALE = {
    hr: {accel: 9.8106e-6, gyro: 1e-5, angle: 1e-3, temperature: 0.1},
    or: {accel: 9.8106 / 4000, gyro: 0.02, angle: 1e-2, temperature: 0.1}
}

const GROUPS = {ax: 'accel', ay: 'accel', az: 'accel', wx: 'gyro', wy: 'gyro', wz: 'gyro', pitch: 'angle', roll: 'angle', yaw: 'angle', tmp: 'temperature'}

export function call(command, args = {}){
    return invoke(command, args)
}

export function sleep(ms){
    return new Promise(resolve => setTimeout(resolve, ms))
}

export function useInterval(callback, delay){
    const saved = useRef(callback)
    saved.current = callback

    useEffect(() => {
        if(delay == null)
            return

        const id = setInterval(() => saved.current(), delay)
        return () => clearInterval(id)
    }, [delay])
}

export function getStored(key, fallback = null){
    try {
        const value = localStorage.getItem(key)
        return value ? JSON.parse(value) : fallback
    }
    catch {
        return fallback
    }
}

export function setStored(key, value){
    try {
        localStorage.setItem(key, JSON.stringify(value))
    }
    catch {
        return
    }
}

// O RAW DO HR TEM ACELERAÇÃO NA CASA DE 1e6; O DO OR, DE 4000
export function getRawFactor(key, values){
    const group = GROUPS[key]

    if(!group)
        return 1

    const norm  = Math.hypot(values?.ax ?? 0, values?.ay ?? 0, values?.az ?? 0)
    const scale = norm > 1e5 ? RAW_SCALE.hr : RAW_SCALE.or
    return scale[group]
}

export function getBaud(protocol, frequency){
    const need = 10 * LINE_BYTES[protocol] * frequency * 1.3    // 8N1 = 10 bits POR BYTE, 30% DE FOLGA
    return BAUDS.find(baud => baud >= need) ?? BAUDS[BAUDS.length - 1]
}

export function getLoad(protocol, frequency, baud){
    return 10 * LINE_BYTES[protocol] * frequency / baud
}

export function formatNumber(value, digits = 3){
    if(value == null || Number.isNaN(value))
        return '—'

    return Number(value).toFixed(digits)
}

export function formatDuration(seconds){
    if(seconds == null || Number.isNaN(seconds))
        return '—'

    const total = Math.max(0, Math.floor(seconds))
    const [h, m, s] = [Math.floor(total / 3600), Math.floor(total / 60) % 60, total % 60]
    return h > 0 ? `${h}h ${String(m).padStart(2, '0')}min` : `${m}:${String(s).padStart(2, '0')}`
}

export function formatBytes(bytes){
    if(!bytes)
        return '0 B'

    const units = ['B', 'KB', 'MB', 'GB']
    const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
    return `${(bytes / 1024 ** power).toFixed(power ? 1 : 0)} ${units[power]}`
}

export function getStamp(date = new Date()){
    const pad = value => String(value).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}_${pad(date.getHours())}-${pad(date.getMinutes())}-${pad(date.getSeconds())}`
}

// CRC-32 IEEE, O MESMO DO Calibration::getCRC DO FIRMWARE
const CRC_TABLE = Array.from({length: 256}, (_, n) => {
    let crc = n

    for(let k = 0; k < 8; k++)
        crc = (crc & 1) ? (0xEDB88320 ^ (crc >>> 1)) : (crc >>> 1)

    return crc >>> 0
})

export function getCRC(values){
    const bytes = new Uint8Array(new Float32Array(values.map(value => value ?? NaN)).buffer)
    let crc = 0xFFFFFFFF

    for(const byte of bytes)
        crc = CRC_TABLE[(crc ^ byte) & 0xFF] ^ (crc >>> 8)

    return ((crc ^ 0xFFFFFFFF) >>> 0).toString(16).toUpperCase()
}

// VALOR float QUE VOLTA IGUAL PELO strtof DO FIRMWARE
export function formatFloat(value){
    if(value == null || Number.isNaN(value))
        return 'nan'

    const single = Math.fround(value)
    return Number.isInteger(single) ? String(single) : single.toPrecision(9).replace(/\.?0+(e|$)/, '$1')
}

// AMOSTRAS DE UM APARELHO EM COLUNAS CIRCULARES: A TELA LÊ A JANELA SEM COPIAR O HISTÓRICO
export class Series {
    constructor(capacity = 200 * 1200){
        this.capacity = capacity
        this.t        = new Float64Array(capacity)
        this.columns  = Object.fromEntries(CHANNELS.map(key => [key, new Float64Array(capacity)]))
        this.clear()
    }

    clear(){
        this.size = 0
        this.head = 0
        this.last = null
    }

    push(sample){
        const index = this.head
        this.t[index] = sample.t

        for(let c = 0; c < CHANNELS.length; c++)
            this.columns[CHANNELS[c]][index] = sample.values[c] ?? NaN

        this.head = (index + 1) % this.capacity
        this.size = Math.min(this.size + 1, this.capacity)
        this.last = {t: sample.t, layout: sample.layout, format: sample.format, values: Object.fromEntries(CHANNELS.map((key, c) => [key, sample.values[c]]))}
    }

    // POSIÇÃO (0 = MAIS NOVA) DA PRIMEIRA AMOSTRA COM t >= start: BUSCA BINÁRIA, O TEMPO SÓ CRESCE ENTRE REINÍCIOS
    getCount(start){
        const newest = (this.head - 1 + this.capacity) % this.capacity
        let [low, high] = [0, this.size]

        while(low < high){
            const middle = (low + high) >> 1

            if(this.t[(newest - middle + this.capacity) % this.capacity] >= start)
                low = middle + 1
            else
                high = middle
        }

        return low
    }

    // A JANELA DE seconds ATÉ until (RELÓGIO DO PC; SEM ELE, A ÚLTIMA AMOSTRA), COM O TEMPO RELATIVO A until. TODAS AS AMOSTRAS POR PADRÃO: O uPlot JUNTA O MÍNIMO E O MÁXIMO DE CADA PIXEL, E DECIMAR AQUI SERRILHARIA O SINAL
    getWindow(seconds, keys, {points = Infinity, factor = () => 1, until = null} = {}){
        if(!this.size)
            return null

        const newest = (this.head - 1 + this.capacity) % this.capacity
        const end    = until ?? this.t[newest]
        const skip   = until == null ? 0 : this.getCount(end + 1e-9)    // AMOSTRAS QUE CHEGARAM DEPOIS DO INSTANTE DESENHADO
        const count  = this.getCount(end - seconds) - skip

        if(count <= 0)
            return null

        const stride = Math.max(1, Math.ceil(count / points))
        const length = Math.ceil(count / stride)
        const x      = new Array(length)
        const ys     = keys.map(() => new Array(length))
        const scales = keys.map(key => factor(key))

        for(let n = 0; n < length; n++){
            const index = (newest - skip - (length - 1 - n) * stride + this.capacity) % this.capacity
            x[n] = this.t[index] - end

            for(let k = 0; k < keys.length; k++){
                const value = this.columns[keys[k]][index]
                ys[k][n] = Number.isNaN(value) ? null : value * scales[k]
            }
        }

        return [x, ...ys]
    }

    // OS VALORES DE key NOS INSTANTES times (RELÓGIO DO PC), PELA AMOSTRA MAIS RECENTE ATÉ CADA UM: OUTRO APARELHO NO EIXO DO PRINCIPAL
    sample(times, key){
        const newest = (this.head - 1 + this.capacity) % this.capacity

        return times.map(time => {
            const back = this.size ? this.getCount(time) : 0

            if(back >= this.size)
                return null

            const index = (newest - back + this.capacity) % this.capacity
            const value = this.columns[key][index]
            return Number.isNaN(value) || time - this.t[index] > 1 ? null : value
        })
    }

    getLast(){
        return this.size ? this.t[(this.head - 1 + this.capacity) % this.capacity] : null
    }

    // MÍNIMO, MÁXIMO E MÉDIA NA JANELA, EM NO MÁXIMO points AMOSTRAS: 20 MIN A 200 Hz NÃO SÃO VARRIDOS A CADA QUADRO
    getStats(key, seconds, points = 4000){
        if(!this.size)
            return null

        const newest = (this.head - 1 + this.capacity) % this.capacity
        const end    = this.t[newest]
        const stride = Math.max(1, Math.ceil(this.getCount(end - seconds) / points))
        let [min, max, sum, count] = [Infinity, -Infinity, 0, 0]

        for(let n = 0; n < this.size; n += stride){
            const index = (newest - n + this.capacity) % this.capacity

            if(this.t[index] < end - seconds)
                break

            const value = this.columns[key][index]

            if(Number.isNaN(value))
                continue

            min = Math.min(min, value); max = Math.max(max, value)
            sum += value; count++
        }

        return count ? {min, max, mean: sum / count} : null
    }
}
