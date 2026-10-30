export const WINDOW   = 20 * 60    // s: OS MÁXIMOS DOS ÚLTIMOS 20 MINUTOS, COMO A NORMAM-223 E O GUIA BRISTOW DEFINEM
export const DEADBAND = 0.02    // m: VOLTA MENOR QUE ISSO NO HEAVE É RUÍDO, NÃO EXTREMO DE OSCILAÇÃO

// A MAIOR MEIA OSCILAÇÃO (Arf, DE EXTREMO A EXTREMO) E A VELOCIDADE MÉDIA NELA (VArf)
function getHalfOscillation(times, values){
    let [anchor, anchorTime, candidate, candidateTime] = [values[0], times[0], values[0], times[0]]
    let [direction, heave, velocity] = [0, 0, null]

    for(let n = 1; n < values.length; n++){
        const [value, time] = [values[n], times[n]]

        if(direction == 0){
            if(Math.abs(value - anchor) >= DEADBAND)
                [direction, candidate, candidateTime] = [Math.sign(value - anchor), value, time]

            continue
        }

        if((value - candidate) * direction > 0){
            [candidate, candidateTime] = [value, time]
            continue
        }

        if(Math.abs(value - candidate) < DEADBAND)
            continue

        const amplitude = Math.abs(candidate - anchor)    // VIROU: candidate É EXTREMO E FECHA A MEIA OSCILAÇÃO QUE COMEÇOU NO anchor

        if(amplitude > heave && candidateTime > anchorTime)
            [heave, velocity] = [amplitude, amplitude / (candidateTime - anchorTime)]

        ;[anchor, anchorTime, candidate, candidateTime, direction] = [candidate, candidateTime, value, time, -direction]
    }

    return {heave: heave || null, velocity}
}

// A JANELA DO HMS SOBRE O BUFFER DO MRU: MÁXIMOS DE PITCH E ROLL POR SENTIDO, INCLINAÇÃO, A MAIOR MEIA OSCILAÇÃO DO HEAVE E O SHR
export function getMotion(series, seconds = WINDOW){
    if(!series?.size)
        return null

    const capacity = series.capacity
    const newest   = (series.head - 1 + capacity) % capacity
    const end      = series.t[newest]
    const {pitch, roll, heave, heave_rate} = series.columns
    const [times, heaves] = [[], []]

    let [up, down, port, starboard, inclination, squares, rates] = [-Infinity, Infinity, Infinity, -Infinity, 0, 0, 0]
    let [previous, previousTime, first] = [null, null, null]

    for(let n = series.size - 1; n >= 0; n--){
        const index = (newest - n + capacity) % capacity
        const time  = series.t[index]

        if(time < end - seconds)
            continue

        first = first ?? time
        const p = pitch[index], r = roll[index], h = heave[index]

        if(!Number.isNaN(p) && !Number.isNaN(r)){
            up = Math.max(up, p); down = Math.min(down, p)
            port = Math.min(port, r); starboard = Math.max(starboard, r)
            inclination = Math.max(inclination, getInclination(p, r))
        }

        if(Number.isNaN(h))
            continue

        const derived = (previous == null || time <= previousTime) ? NaN : (h - previous) / (time - previousTime)    // NMEA NÃO TRAZ A TAXA: DIFERENÇA DO HEAVE
        const rate    = Number.isNaN(heave_rate[index]) ? derived : heave_rate[index]

        if(!Number.isNaN(rate)){
            squares += rate * rate
            rates++
        }

        times.push(time); heaves.push(h)
        ;[previous, previousTime] = [h, time]
    }

    if(first == null)
        return null

    const finite = value => Number.isFinite(value) ? value : null
    const shr    = rates ? 2 * Math.sqrt(squares / rates) : null
    const half   = heaves.length > 2 ? getHalfOscillation(times, heaves) : {heave: null, velocity: null}

    return {
        span: end - first,
        up: finite(up),
        down: finite(down),
        port: finite(port),
        starboard: finite(starboard),
        inclination,
        heave: half.heave,
        velocity: half.velocity,
        shr: shr == null ? null : Math.ceil(shr * 10 - 1e-9) / 10    // ARREDONDADO PARA CIMA NA PRIMEIRA CASA, COMO O STATUS USA
    }
}

export function getInclination(pitch, roll){
    const radians = Math.PI / 180
    return Math.acos(Math.min(1, Math.cos(pitch * radians) * Math.cos(roll * radians))) / radians
}
