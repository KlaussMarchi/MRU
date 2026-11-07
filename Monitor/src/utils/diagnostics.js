import { getBaud, getLoad } from './index'

const LEVELS = {error: 0, warn: 1, info: 2}
const RESETS = {
    panic: ['o firmware travou (panic)', 'Um erro de execução derrubou o firmware. Se repetir, veja os eventos abaixo e reenvie o firmware.'],
    int_wdt: ['o watchdog de interrupção disparou', 'Alguma rotina prendeu o processador. Se repetir, atualize o firmware.'],
    task_wdt: ['o watchdog de tarefa disparou', 'Uma tarefa ficou sem rodar. Se repetir, atualize o firmware.'],
    wdt: ['o watchdog disparou', 'O processador ficou preso. Se repetir, atualize o firmware.'],
    brownout: ['a alimentação caiu (brownout)', 'A tensão caiu abaixo do mínimo do ESP32: confira fonte, conector e o consumo do Kernel.']
}
const RECENT   = 600     // s DEPOIS DO BOOT EM QUE UM RESET ANORMAL AINDA É NOTÍCIA
const WINDOW   = 100     // AMOSTRAS QUE A TELA OLHA PARA VER DADOS CONGELADOS OU IMPOSSÍVEIS
const GRAVITY  = [5, 15]    // m/s²: A MÉDIA DA ACELERAÇÃO FORA DISSO NÃO É MOVIMENTO, É SENSOR
const LOSS     = 0.01    // FRAÇÃO DE PACOTES PERDIDOS QUE MERECE AVISO
const SLOW     = 0.7     // FRAÇÃO DA TAXA CONFIGURADA ABAIXO DA QUAL O STREAM ESTÁ ATRASADO
const LEGACY   = [1, 0, 9]    // O PRIMEIRO FIRMWARE COM $diagnostics!
const SETTLE   = 4000    // ms DEPOIS DE SINCRONIZAR ATÉ A FALTA DE STREAM QUERER DIZER ALGUMA COISA


function getRecent(series, key){
    const column = series.columns[key]
    const count  = Math.min(WINDOW, series.size)
    return Array.from({length: count}, (_, index) => column[(series.head - 1 - index + series.capacity) % series.capacity])
}


// O QUE OS PRÓPRIOS DADOS DIZEM, MESMO EM FIRMWARE SEM DIAGNÓSTICO: NaN, TUDO CONGELADO, ACELERAÇÃO IMPOSSÍVEL
function checkData(series, layout){
    if(!series || series.size < WINDOW || !['scale', 'calibrated'].includes(layout))
        return []

    const issues  = []
    const columns = ['pitch', 'roll', 'yaw', 'ax', 'ay', 'az', 'wx', 'wy', 'wz'].map(key => getRecent(series, key))

    if(columns.some(values => values.some(Number.isNaN)))
        return [{key: 'nan', level: 'error', title: 'O MRU está enviando NaN', detail: 'A saída tem campos sem número: a cadeia de processamento divergiu ou a calibração não serve para este MRU. Reiniciar zera os filtros; se voltar, regrave a calibração.', action: 'restart'}]

    if(columns.every(values => values.every(value => value == values[0])))
        issues.push({key: 'frozen-data', level: 'error', title: 'Os dados estão congelados', detail: 'O tempo anda, mas nenhum campo muda (um sensor real sempre tem ruído): o Kernel travou. Desligue e ligue o MRU.'})

    const mean = index => columns[index].reduce((sum, value) => sum + value, 0) / columns[index].length
    const norm = Math.hypot(mean(3), mean(4), mean(5))

    if(norm < GRAVITY[0] || norm > GRAVITY[1])
        issues.push({key: 'gravity', level: 'warn', title: `Aceleração média de ${norm.toFixed(1)} m/s²`, detail: 'Parado ou em movimento lento ela fica perto de 9,8. Longe disso, o acelerômetro ou a escala estão errados.'})

    return issues
}


function checkPort(link, stat, trend, ports){
    if(link.state == 'error' && !ports.length)
        return [{key: 'no-port', level: 'error', title: 'Nenhuma porta serial encontrada', detail: 'O computador não enxerga nenhum cabo: confira o USB e o driver do conversor (CH340, FTDI, CP210x). Sem hardware, ligue a simulação em Ajustes.', action: 'search'}]

    if(link.state == 'error')
        return [{key: 'no-mru', level: 'error', title: 'Nenhum MRU respondeu', detail: `${ports.length} porta(s) testada(s) em todos os bauds. Confira a alimentação do MRU, o cabo e se o conversor é o certo (RS232 ou RS422).`, action: 'search'}]

    const error = stat?.error

    if(error && /permission|acesso negado|access is denied/i.test(error))
        return [{key: 'permission', level: 'error', title: 'Sem permissão para abrir a porta', detail: 'No Linux: sudo usermod -aG dialout "$USER" e entre de novo na sessão.'}]

    if(error && /busy|ocupad|in use/i.test(error))
        return [{key: 'busy', level: 'error', title: 'A porta está em uso por outro programa', detail: 'Feche a IDE do Arduino, o monitor serial ou outra janela que esteja com ela aberta.'}]

    if(error)
        return [{key: 'port-down', level: 'error', title: 'A porta caiu', detail: `${error}. O app tenta reabrir sozinho; confira o cabo.`}]

    if(link.state != 'open')
        return []

    if((stat?.rate ?? 0) > 0)
        return [{key: 'one-way', level: 'warn', title: 'O stream chega, mas o MRU não responde ao ACK', detail: 'Os dados saem do MRU, mas os comandos não chegam nele: confira o fio TX do conversor. Sem ACK o app não configura nem atualiza.', action: 'sync'}]

    if((trend?.bytes ?? 0) > 0)
        return [{key: 'garbage', level: 'error', title: 'Chegam bytes, mas nada legível', detail: `Quase sempre é baud errado: a porta está em ${link.baud} bps. Procure o baud certo.`, action: 'search'}]

    return [{key: 'silent', level: 'error', title: 'A porta abriu, mas o MRU está mudo', detail: 'Nada chega: MRU desligado, TX e RX invertidos, ou o MRU transmitindo em outra porta (USB, RS232 ou RS422).', action: 'search'}]
}


function checkFirmware(health, link){
    const info   = health.info
    const issues = []

    if(!info)
        return issues

    const kernel = info.kernel

    if(!kernel.found)
        issues.push({key: 'kernel-dead', level: 'error', title: 'O Kernel não respondeu no boot', detail: 'O ESP32 está vivo, mas não achou o Kernel em 460800, 115200, 230400 nem 921600 bps, então não há o que transmitir. Confira a alimentação do Kernel e a UART1 (TX pino 4, RX pino 3) e reinicie.', action: 'restart'})
    else if(!kernel.alive)
        issues.push({key: 'kernel-silent', level: 'error', title: `O Kernel parou de transmitir há ${Math.round(kernel.silence / 1000)} s`, detail: 'Sem pacotes do Kernel o MRU não tem o que enviar: é por isso que o stream parou. Confira a alimentação e o cabo do Kernel.', action: 'restart'})
    else if(kernel.frozen)
        issues.push({key: 'kernel-frozen', level: 'error', title: 'O Kernel está congelado', detail: 'Os pacotes chegam, mas com valores idênticos há mais de 3 s. Desligue e ligue o MRU.'})

    if(health.deltas.errors > 0)
        issues.push({key: 'checksum', level: 'warn', title: `${health.deltas.errors} pacotes do Kernel com checksum errado`, detail: 'Ruído ou mau contato entre o Kernel e o ESP32 (UART1): os pacotes ruins são descartados, e a taxa cai.'})

    if(health.deltas.invalid > 0)
        issues.push({key: 'invalid', level: 'error', title: 'O processamento gerou NaN', detail: 'A cadeia calibrada divergiu. Reiniciar zera os filtros; se voltar, regrave a calibração.', action: 'restart'})

    if(health.deltas.skipped > 0)
        issues.push({key: 'skipped', level: 'warn', title: `O MRU não deu conta de enviar ${health.deltas.skipped} pacotes`, detail: 'A porta está saturada na aquisição: confira o baud e o conversor.'})

    if(info.stall >= 100)
        issues.push({key: 'stall', level: 'warn', title: `O processamento travou por ${info.stall} ms`, detail: 'Uma travada dessas perde pacotes e deixa o dt errado no próximo: é a maior desde o boot.'})

    if(info.rolled_back)
        issues.push({key: 'rolled', level: 'warn', title: 'Um firmware novo caiu e o MRU voltou ao anterior', detail: `O bootloader voltou sozinho para ${link.firmware}. Confira o arquivo antes de enviar de novo.`, action: 'firmware'})

    if(RESETS[info.reset] && info.uptime < RECENT)
        issues.push({key: 'reset', level: 'error', title: `O MRU reiniciou: ${RESETS[info.reset][0]}`, detail: RESETS[info.reset][1]})

    if(health.reboots > 0)
        issues.push({key: 'reboots', level: 'warn', title: `O MRU reiniciou sozinho ${health.reboots} vez(es)`, detail: `Motivo do último: ${info.reset}. Confira a alimentação e os eventos abaixo.`})

    return issues
}


function checkStream(link, stat, trend, health){
    const status = link.status
    const rate   = stat?.rate ?? 0
    const issues = []

    if(Date.now() - link.syncedAt < SETTLE)
        return issues

    if(rate == 0 && status && !status.streaming && health.info?.kernel?.alive !== false)
        issues.push({key: 'stopped', level: 'warn', title: 'O stream está parado', detail: `O MRU responde, mas não transmite${status.autostream ? '' : ': o autostream está desligado, então ele espera o comando'}.`, action: 'stream'})

    if(rate == 0 && status?.streaming && health.info?.kernel?.alive !== false)
        issues.push({key: 'no-data', level: 'error', title: 'O MRU diz que transmite, mas nada chega', detail: `Ele está enviando por ${status.port}. Confira se é a mesma porta em que o app está conectado.`, action: 'restart'})

    const expected = status ? (status.device_mode == 1 ? 200 : Math.min(status.frequency, 200)) : 0

    if(rate > 0 && expected && rate < SLOW * expected && link.kind != 'usb'){
        const load = getLoad(status.protocol, expected, status.baud)
        issues.push({key: 'slow', level: 'warn', title: `Chegam ${Math.round(rate)} Hz de ${Math.round(expected)} Hz`, detail: load > 0.9 ? `A linha não comporta: ${Math.round(expected)} Hz ocupam ${Math.round(load * 100)}% de ${status.baud} bps. Use ao menos ${getBaud(status.protocol, expected)} bps, ou menos Hz.` : 'A banda da porta comporta: o atraso está no MRU ou no conversor.'})
    }

    const packets = trend?.count ?? 0

    if(packets > 20 && (trend?.lost ?? 0) / packets > LOSS)
        issues.push({key: 'loss', level: 'warn', title: `${(100 * trend.lost / packets).toFixed(1)}% dos pacotes perdidos`, detail: 'O tempo do stream deu saltos nos últimos segundos: linha saturada ou mau contato.'})

    if((trend?.bad ?? 0) > 2)
        issues.push({key: 'bad-lines', level: 'warn', title: `${trend.bad} linhas corrompidas em 10 s`, detail: 'Ruído na linha, cabo longo sem blindagem ou baud no limite.'})

    return issues
}


// O PORQUÊ DE O MRU NÃO ESTAR ENVIANDO, OU ENVIANDO MAL, NA ORDEM EM QUE SE DIAGNOSTICA: PORTA, MRU, KERNEL, STREAM E DADOS
export function getIssues({link, stat, table, tableStat, health, trend, ports, series}){
    if(['off', 'searching', 'syncing', 'rebooting'].includes(link.state))
        return []

    const issues = [...checkPort(link, stat, trend, ports)]

    if(link.state == 'synced'){
        issues.push(...checkFirmware(health, link), ...checkStream(link, stat, trend, health))

        if(!issues.some(issue => issue.level == 'error'))
            issues.push(...checkData(series, stat?.layout))

        if(health.supported === false)
            issues.push({key: 'old-firmware', level: 'info', title: `O firmware ${link.firmware ?? 'em uso'} não tem diagnóstico completo`, detail: 'Só o que chega pela porta dá para analisar: sem saber do Kernel nem do motivo dos reinícios. Atualize para a v1.0.9 ou mais nova.', action: 'firmware'})
    }

    if(table?.state == 'open' && tableStat && !tableStat.rate && Date.now() / 1000 - tableStat.opened > 15)
        issues.push({key: 'table-silent', level: 'warn', title: 'A plataforma está aberta, mas não transmite', detail: 'Mais de 15 s sem dados: o homing não terminou ou o cabo soltou.'})

    return issues.sort((a, b) => LEVELS[a.level] - LEVELS[b.level])
}


// A LISTA DE CONFERÊNCIA DO DISPOSITIVO: O QUE ESTÁ BEM TAMBÉM APARECE, PARA NÃO SOBRAR DÚVIDA
export function getChecks({link, stat, health}){
    const info = health.info
    const rate = stat?.rate ?? 0
    const ok   = link.state == 'synced'

    return [
        {label: 'Porta', state: stat?.error ? 'bad' : stat?.connected ? 'ok' : '', text: stat?.error ? 'caiu' : stat?.connected ? (link.kind == 'usb' ? 'USB nativo' : `${link.baud} bps`) : 'fechada'},
        {label: 'ACK do MRU', state: ok ? 'ok' : link.state == 'open' ? 'bad' : '', text: ok ? `${link.firmware ?? 'respondeu'}` : link.state == 'open' ? 'sem resposta' : '—'},
        {label: 'Kernel', state: !info ? '' : !info.kernel.found || !info.kernel.alive || info.kernel.frozen ? 'bad' : 'ok', text: !info ? '—' : !info.kernel.found ? 'não achado no boot' : !info.kernel.alive ? 'mudo' : info.kernel.frozen ? 'congelado' : `${info.kernel.rate} Hz · ${info.kernel.baud} bps`},
        {label: 'Checksum', state: !info ? '' : health.deltas.errors > 0 ? 'warn' : 'ok', text: !info ? '—' : `${info.kernel.errors} erros em ${info.kernel.packets.toLocaleString('pt-BR')}`},
        {label: 'Stream', state: !ok ? '' : rate > 0 ? 'ok' : 'warn', text: !ok ? '—' : rate > 0 ? `${Math.round(rate)} Hz recebidos` : 'nada chegando'},
        {label: 'Temperatura', state: !info ? '' : info.kernel.found && info.kernel.alive ? 'ok' : '', text: info?.kernel.alive ? `${info.kernel.temperature.toFixed(1)} °C` : '—'},
        {label: 'Último boot', state: !info ? '' : RESETS[info.reset] ? 'bad' : 'ok', text: !info ? '—' : `há ${formatUptime(info.uptime)} · ${info.reset}`},
        {label: 'Travadas', state: !info ? '' : info.stall >= 100 ? 'warn' : 'ok', text: !info ? '—' : `até ${info.stall} ms`},
        {label: 'Memória livre', state: !info ? '' : 'ok', text: !info ? '—' : `${Math.round(info.heap / 1024)} KB · partição ${info.partition}`}
    ]
}


function formatUptime(seconds){
    return seconds < 120 ? `${seconds} s` : seconds < 7200 ? `${Math.round(seconds / 60)} min` : `${(seconds / 3600).toFixed(1)} h`
}


// v1.0.9 CONTRA v1.0.8: NEGATIVO, ZERO OU POSITIVO; null SE ALGUM LADO NÃO FOR UMA VERSÃO
export function compareVersions(a, b){
    const parse = text => text?.match(/^v(\d+)\.(\d+)\.(\d+)/)?.slice(1).map(Number)
    const [x, y] = [parse(a), parse(b)]

    if(!x || !y)
        return null

    return x[0] - y[0] || x[1] - y[1] || x[2] - y[2]
}


export function hasDiagnostics(firmware){
    const value = compareVersions(firmware, `v${LEGACY.join('.')}`)
    return value == null || value >= 0
}
