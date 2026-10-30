// NORMAM-223/DPC TABELA 1: B/C (±°), Inc (°), VArf E SVArf (m/s), Arf (m) POR CATEGORIA, CLASSE DE HELIDEQUE E PERÍODO; null É OPERAÇÃO NÃO PERMITIDA
export const NORMAM = {
    A: {
        1: {day: [3, 3.5, 1.3, 5.0], night: [3, 3.5, 1.0, 4.0]},
        2: {day: [2, 2.5, 1.0, 3.0], night: [2, 2.5, 0.5, 1.5]},
        3: {day: [2, 2.5, 1.0, 3.0], night: null}
    },
    B: {
        1: {day: [4, 4.5, 1.3, 5.0], night: [4, 4.5, 1.0, 4.0]},
        2: {day: [3, 3.5, 1.0, 3.0], night: [2, 2.5, 0.5, 1.5]},
        3: {day: [3, 3.5, 1.0, 3.0], night: null}
    }
}

export const RISE    = 2 * 60     // s COM O SHR ACIMA DO LIMITE PARA FECHAR (GUIA BRISTOW 9c)
export const FALL    = 10 * 60    // s COM O SHR ABAIXO DO LIMITE PARA REABRIR
export const WARNING = 0.9        // FRAÇÃO DO LIMITE QUE ACENDE O ÂMBAR
export const STALE   = 2          // s SEM PACOTE: O PAINEL NÃO VALE MAIS

export const CATEGORIES = [{value: 'A', label: 'Cat. A · grande porte'}, {value: 'B', label: 'Cat. B · médio'}]
export const DECKS      = [{value: 1, label: 'Classe 1'}, {value: 2, label: 'Classe 2'}, {value: 3, label: 'Classe 3'}]
export const PERIODS    = [{value: 'day', label: 'Diurno'}, {value: 'night', label: 'Noturno'}]

export function getLimits(options){
    const row = NORMAM[options.category]?.[options.deck]?.[options.period]

    if(!row)
        return null

    const [angle, inclination, rate, heave] = row
    return {angle, inclination, rate, heave}
}

export function getTone(value, limit){
    if(value == null || limit == null)
        return ''

    if(Math.abs(value) > limit)
        return 'bad'

    return Math.abs(value) > WARNING * limit ? 'warn' : 'ok'
}

// FECHA SÓ COM O SHR ACIMA DO LIMITE EM TODO O RISE E REABRE SÓ COM ELE ABAIXO EM TODO O FALL
export function getHeaveStatus(history, limit, previous){
    if(!history.length || limit == null)
        return 'ok'

    const now    = history[history.length - 1].time
    const within = seconds => history.filter(item => item.time >= now - seconds).map(item => item.shr)

    if(previous != 'bad')
        return Math.min(...within(RISE)) > limit ? 'bad' : 'ok'

    return Math.max(...within(FALL)) <= limit ? 'ok' : 'bad'
}
