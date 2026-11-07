import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { listen } from '@tauri-apps/api/event'
import { call, sleep, getStored, setStored, Series, ACQUISITION_BAUD } from '../utils'
import { compareVersions, getIssues, hasDiagnostics } from '../utils/diagnostics'

const DeviceContext = createContext(undefined)
const LiveContext   = createContext(undefined)
const POLL    = 30      // ms ENTRE LEITURAS DO BACKEND: CHEGA ANTES DO ATRASO DE 0,12 s COM QUE O GRÁFICO DESENHA
const REFRESH = 250     // ms ENTRE ATUALIZAÇÕES DO ESTADO AO VIVO (ESTATÍSTICAS, GRAVAÇÃO, TERMINAL)
const TEXTS   = 4000    // LINHAS DO TERMINAL NA MEMÓRIA: 20 s DE STREAM A 200 Hz, PARA AS RESPOSTAS NÃO SUMIREM AO ESCONDER O STREAM
const BOOT    = 3500    // ms QUE O MRU LEVA PARA VOLTAR DEPOIS DO REINÍCIO
const ROLES   = ['mru', 'table']
const IDLE    = {state: 'off', port: null, baud: null, kind: null, simulated: false, status: null, settings: null, message: ''}
const WATCH   = 1000    // ms ENTRE DUAS OLHADAS NA SAÚDE; O QUE MANDA PERGUNTAR AO MRU É O PERÍODO DE getPeriod
const TREND   = 10000   // ms DA JANELA DE PERDAS E LINHAS RUINS
const MISSES  = 3       // PERGUNTAS SEM RESPOSTA ATÉ DIZER QUE O MRU PAROU DE RESPONDER
const PROOF   = 12      // s RODANDO PARA O FIRMWARE NOVO TER SAÍDO DA PROVA DE 10 s
const PROVING = 25000   // ms ESPERANDO ESSA PROVA
const QUIET   = 600     // s LIGADO SEM CAIR PARA OS REINÍCIOS DE ANTES DEIXAREM DE SER NOTÍCIA
const HEALTH  = {supported: null, info: null, log: [], reboots: 0, deltas: {errors: 0, invalid: 0, skipped: 0}}


export function useDevice(){
    const context = useContext(DeviceContext)

    if(!context)
        throw new Error('useDevice precisa estar dentro de um DeviceProvider')

    return context
}

export function useLive(){
    return useContext(LiveContext)
}

export function useIssues(){
    const {links, ports, health, update, getSeries} = useDevice()
    const {stats, trend} = useLive()
    return useMemo(() => update?.status == 'running' ? [] : getIssues({link: links.mru, stat: stats.mru, table: links.table, tableStat: stats.table, health, trend, ports, series: getSeries('mru')}), [links, ports, health, update, stats, trend])
}

// A CONEXÃO COM O MRU E A PLATAFORMA DE REFERÊNCIA, VIVA EM TODAS AS TELAS: LEITURA CONTÍNUA, SINCRONIZAÇÃO, COMANDOS, CONFIGURAÇÃO COM REINÍCIO E O BANCO SIMULADO
export function DeviceProvider({children}){
    const [links, setLinks]           = useState({mru: IDLE, table: IDLE})
    const [live, setLive]             = useState({stats: {}, trend: null, recording: null, version: 0, texts: 0})
    const [ports, setPorts]           = useState([])
    const [discovery, setDiscovery]   = useState('')
    const [simulation, setSimulationState] = useState({...getStored('simulation', {enabled: false, scenario: 'table'}), fault: ''})
    const [health, setHealthState]    = useState(HEALTH)
    const [flashing, setFlashing]     = useState(null)

    const series     = useRef({mru: new Series(200 * 1200), table: new Series(100 * 1200)})    // 20 MIN NA TAXA MÁXIMA DE CADA UM
    const texts      = useRef({mru: [], table: []})
    const cursors    = useRef({})
    const busy       = useRef(false)
    const recovering = useRef({})
    const latest     = useRef({stats: {}, trend: null, recording: null, texts: 0})
    const linksRef   = useRef(links)
    const healthRef  = useRef(health)
    const trends     = useRef([])
    const watching   = useRef(false)
    const wasFlowing = useRef(false)
    const asked      = useRef(0)
    const misses     = useRef(0)
    const updating   = useRef(false)
    const expected   = useRef(false)
    const job        = useRef(null)
    linksRef.current  = links
    healthRef.current = health

    useEffect(() => {
        const unlisten = listen('discover', event => setDiscovery(event.payload))
        call('simulation_set', simulation).then(refreshPorts)
        return () => { unlisten.then(stop => stop()) }
    }, [])

    useEffect(() => {
        const reader = setInterval(update, POLL)
        const screen = setInterval(() => setLive(current => ({stats: {...latest.current.stats}, trend: latest.current.trend, recording: latest.current.recording, version: current.version + 1, texts: latest.current.texts})), REFRESH)
        const watcher = setInterval(watch, WATCH)
        return () => { clearInterval(reader); clearInterval(screen); clearInterval(watcher) }
    }, [])

    async function update(){
        if(busy.current)
            return

        busy.current = true

        try {
            const response = await call('poll', {cursors: cursors.current, max: 4000})

            for(const [role, snapshot] of Object.entries(response.devices)){
                const previous = cursors.current[role]

                if(previous && snapshot.sample_seq < previous.sample)    // O BACKEND REABRIU O APARELHO: A CONTAGEM RECOMEÇOU
                    series.current[role].clear()

                for(const sample of snapshot.samples){
                    if(series.current[role].last && series.current[role].last.layout != sample.layout)    // OUTRO MODO, OUTROS EIXOS E UNIDADES: O HISTÓRICO NÃO SE MISTURA
                        series.current[role].clear()

                    series.current[role].push(sample)
                }

                if(snapshot.texts.length){
                    texts.current[role] = texts.current[role].concat(snapshot.texts).slice(-TEXTS)
                    latest.current.texts += snapshot.texts.length

                    if(role == 'mru' && snapshot.texts.some(text => text.kind == 'log' && !text.text.startsWith('#W')))    // O ESTADO DO MRU MUDOU: A FAIXA NÃO ESPERA O PRÓXIMO PERÍODO
                        asked.current = 0
                }

                cursors.current[role] = {sample: snapshot.sample_seq, text: snapshot.text_seq}
                latest.current.stats[role] = snapshot.stats

                if(linksRef.current[role].state == 'off' && !recovering.current[role])
                    recover(role, snapshot)
            }

            for(const role of ROLES)
                if(!response.devices[role])
                    delete latest.current.stats[role]

            latest.current.recording = response.recording
        }
        catch {
            return
        }
        finally {
            busy.current = false
        }
    }

    function setHealth(changes){
        healthRef.current = {...healthRef.current, ...changes}
        setHealthState(healthRef.current)
    }

    // O QUE PASSOU NOS ÚLTIMOS SEGUNDOS, PARA UMA PERDA ANTIGA NÃO FICAR ACUSANDO PARA SEMPRE
    function updateTrend(stat){
        const now = Date.now()
        trends.current = stat ? [...trends.current, {at: now, lost: stat.lost, bad: stat.bad, bytes: stat.bytes, count: stat.count}].filter(item => now - item.at <= TREND) : []
        const [first, last] = [trends.current[0], trends.current[trends.current.length - 1]]
        latest.current.trend = first && last != first ? {lost: last.lost - first.lost, bad: last.bad - first.bad, bytes: last.bytes - first.bytes, count: last.count - first.count} : null
    }

    // PERGUNTA AO MRU O QUE ELE SABE DE SI, MAS NUNCA ATRAPALHA: FORA DA GRAVAÇÃO E DA ATUALIZAÇÃO, E RARAMENTE NA LINHA LENTA, ONDE A RESPOSTA OCUPARIA O STREAM
    async function watch(){
        const stat = latest.current.stats.mru
        const link = linksRef.current.mru
        updateTrend(stat)

        if(watching.current || updating.current || latest.current.recording)
            return

        const now     = Date.now()
        const flowing = (stat?.rate ?? 0) > 0
        const period  = !flowing ? 3000 : link.kind != 'usb' && link.baud < 57600 ? 10000 : 5000

        if(flowing != wasFlowing.current)
            asked.current = 0

        wasFlowing.current = flowing

        if(now - asked.current < period)
            return

        watching.current = true
        asked.current    = now

        try {
            if(link.state == 'synced' && healthRef.current.supported)
                await readHealth()

            if(link.state == 'open' && link.lost)    // ELE ESTAVA RESPONDENDO: VOLTA SOZINHO QUANDO RESPONDER DE NOVO
                await recoverLink()
        }
        finally {
            watching.current = false
        }
    }

    async function recoverLink(){
        const answer = await call('query', {role: 'mru', message: '$ackoneledge!', expect: ['$MICACK!'], timeout: 1000, quiet: true}).catch(() => null)

        if(answer)
            await sync('mru', 1)
    }

    function ask(message, expect, timeout = 2000){
        return call('query', {role: 'mru', message, expect, timeout, quiet: true})
    }

    async function readHealth(){
        const text = await ask('$diagnostics!', ['"uptime"']).catch(() => null)

        if(!text){
            misses.current++

            if(misses.current >= MISSES && linksRef.current.mru.state == 'synced')
                setLink('mru', {state: 'open', lost: true, message: 'o MRU parou de responder'})

            return
        }

        misses.current = 0
        const info     = JSON.parse(text)
        const before   = healthRef.current.info
        const restarted = before && info.uptime < before.uptime
        const changes  = {info, deltas: !before || restarted ? HEALTH.deltas : {errors: info.kernel.errors - before.kernel.errors, invalid: info.processing.invalid - before.processing.invalid, skipped: info.stream.skipped - before.stream.skipped}}

        if(restarted && !expected.current)
            changes.reboots = healthRef.current.reboots + 1

        if(info.uptime > QUIET)
            changes.reboots = 0

        expected.current = false
        setHealth(changes)

        if(!info.verbose)
            await ask('$verbose:1!', ['$VERBOSE']).catch(() => null)

        if(info.logs != before?.logs || restarted){
            const log = await ask('$log!', ['"log"'], 3000).then(JSON.parse).catch(() => null)

            if(log)
                setHealth({log: log.log})
        }
    }

    // OS EVENTOS NA PORTA, O DIÁRIO DO BOOT E O PRIMEIRO RETRATO: O FIRMWARE ANTIGO NÃO CONHECE NENHUM DELES
    async function startHealth(firmware){
        asked.current = Date.now()

        if(!hasDiagnostics(firmware))
            return setHealth({...HEALTH, supported: false})

        const answer = await ask('$verbose:1!', ['$VERBOSE'], 1500).catch(() => null)
        setHealth({supported: compareVersions(firmware, 'v0.0.0') != null || Boolean(answer)})

        if(answer)
            await readHealth()
    }

    // A TELA RECARREGOU COM O BACKEND AINDA CONECTADO: RETOMA O APARELHO EM VEZ DE ABRIR DE NOVO
    async function recover(role, snapshot){
        recovering.current[role] = true
        const info = (await refreshPorts()).find(item => item.name == snapshot.port)
        setLink(role, {state: 'open', port: snapshot.port, baud: snapshot.baud, kind: info?.kind ?? 'converter', simulated: snapshot.port.startsWith('sim:'), label: info?.label ?? snapshot.port, message: ''})

        if(role == 'mru')
            await sync(role)

        recovering.current[role] = false
    }

    function setLink(role, changes){
        setLinks(current => ({...current, [role]: {...current[role], ...changes}}))
    }

    async function refreshPorts(){
        const list = await call('list_ports')
        setPorts(list)
        return list
    }

    // LIGAR A SIMULAÇÃO PÕE AS PORTAS SIM0 E SIM1 NA LISTA; DESLIGAR FECHA AS QUE ESTAVAM ABERTAS
    async function setSimulation(changes){
        const next = {...simulation, ...changes}
        setSimulationState(next)
        setStored('simulation', {enabled: next.enabled, scenario: next.scenario})    // A FALHA É UM TESTE DE AGORA: NÃO VOLTA NA PRÓXIMA ABERTURA
        await call('simulation_set', next)

        if(!next.enabled)
            for(const role of ROLES)
                if(linksRef.current[role].simulated)
                    setLink(role, IDLE)

        await refreshPorts()
    }

    async function open(role, port, baud){
        await call('connect', {role, port, baud})
        cursors.current[role] = {sample: 0, text: 0}
        series.current[role].clear()
        texts.current[role] = []
        const info = (await refreshPorts()).find(item => item.name == port)
        setLink(role, {state: 'open', port, baud, kind: info?.kind ?? 'converter', simulated: port.startsWith('sim:'), label: info?.label ?? port, message: ''})
    }

    async function disconnect(role){
        await call('disconnect', {role})
        delete cursors.current[role]
        setLink(role, IDLE)

        if(role == 'mru')
            setHealth(HEALTH)
    }

    // PORTA E BAUD PEDIDOS OU, SEM ELES, A DESCOBERTA (PORTA FICTÍCIA INCLUSIVE); O MRU ACHADO JÁ SAI SINCRONIZADO
    async function connect(role, {port = null, baud = null} = {}){
        setLink(role, {state: 'searching', message: 'procurando...'})

        try {
            if(port && baud){
                await open(role, port, baud)
                return role == 'mru' ? await sync(role) : true
            }

            await refreshPorts()
            const found = await call('discover', {role, port, baud})

            if(!found){
                setLink(role, {...IDLE, state: 'error', message: role == 'mru' ? 'nenhum MRU respondeu: confira cabo, alimentação e baud, ou ligue a simulação em Ajustes' : 'nenhuma plataforma transmitindo a 115200 bps'})
                return false
            }

            await open(role, found.port, found.baud)
            return role == 'mru' ? await sync(role) : true
        }
        catch(error) {
            setLink(role, {...IDLE, state: 'error', message: String(error)})
            return false
        }
    }

    async function query(message, expect = [], timeout = 1500, role = 'mru'){
        return call('query', {role, message, expect, timeout})
    }

    async function send(message, role = 'mru', ending = '\r\n'){
        return call('send', {role, message, ending})
    }

    function getSeries(role = 'mru'){
        return series.current[role]
    }

    function getTexts(role = 'mru'){
        return texts.current[role]
    }

    function clearTexts(role = 'mru'){
        texts.current[role] = []
        latest.current.texts++
    }

    // ACK DO PIPELINE PRINCIPAL E O RETRATO DO MRU ($status!, $settings!); FIRMWARE ANTIGO SEM $status! SÓ CONFIRMA O ACK
    async function sync(role = 'mru', attempts = 3){
        setLink(role, {state: 'syncing', message: 'sincronizando...'})

        for(let attempt = 0; attempt < attempts; attempt++){
            try {
                await query('$ackoneledge!', ['$MICACK!'], 1500, role)
                const status   = await query('$status!', ['"firmware"'], 2000, role).then(JSON.parse).catch(() => null)
                const settings = await query('$settings!', ['"device_mode"', '"protocol"', '"telemetry"'], 2000, role).then(JSON.parse).catch(() => null)
                const firmware = status?.firmware ?? await query('$firmware!', ['v'], 1500, role).catch(() => null)
                setLink(role, {state: 'synced', lost: false, syncedAt: Date.now(), status, settings, firmware, message: status ? `${status.port} · firmware ${firmware}` : `firmware ${firmware ?? '?'}, anterior a v1.0.8`})
                misses.current = 0

                if(role == 'mru' && !updating.current)
                    await startHealth(firmware)

                return true
            }
            catch {
                await sleep(400)
            }
        }

        setLink(role, {state: 'open', message: 'a porta está aberta, mas o MRU não respondeu o ACK'})
        return false
    }

    // OS CS: VALEM NUM REINÍCIO SÓ; FIRMWARE ANTIGO RECEBE CF: E REINICIA A CADA UM. O BAUD DA UART PODE MUDAR NO CAMINHO
    async function configure(changes, report = () => null){
        const link    = linksRef.current.mru
        const legacy  = !link.status
        const entries = Object.entries(changes)

        for(const [index, [key, value]] of entries.entries()){
            report(`${legacy ? 'CF' : 'CS'}:${key}$${value} (${index + 1}/${entries.length})`)

            if(!legacy){
                await query(`CS:${key}$${value}!`, [`$OK:${key}=`], 2500)
                continue
            }

            await send(`CF:${key}$${value}!`)
            await reboot({...link.settings, ...Object.fromEntries(entries.slice(0, index + 1))}, report)
        }

        if(!legacy){
            report('reiniciando o MRU para aplicar')
            await send('MICRS')
            await reboot({...link.settings, ...changes}, report)
        }
    }

    // ESPERA O BOOT E VOLTA A FALAR COM O MRU: NO CONVERSOR (E NA PORTA FICTÍCIA) O BAUD SEGUE O device_mode E O baudrate GRAVADOS
    async function reboot(settings = {}, report = () => null){
        const link = linksRef.current.mru
        expected.current = true
        setHealth({info: null, deltas: HEALTH.deltas})    // O RETRATO É DO BOOT ANTERIOR
        setLink('mru', {state: 'rebooting', message: 'reiniciando...'})
        await sleep(BOOT)

        const converter = link.kind == 'converter'
        const baud      = !converter ? link.baud : Number(settings.device_mode) == 1 ? ACQUISITION_BAUD : Number(settings.baudrate ?? link.baud)

        if(converter && baud != link.baud){
            report(`reabrindo ${link.label ?? link.port} a ${baud} bps`)
            await open('mru', link.port, baud)
        }

        for(let attempt = 0; attempt < 6; attempt++){
            report('sincronizando depois do reinício')

            if(await sync('mru', 2))
                return true

            await sleep(1000)
        }

        report('o MRU não voltou na mesma porta: procurando')
        await disconnect('mru')

        if(await connect('mru'))
            return true

        throw new Error('o MRU não voltou depois do reinício')
    }

    // O FIRMWARE NOVO FICA EM PROVA POR 10 s: SÓ DEPOIS DELA SE SABE SE ELE FICOU OU SE O BOOTLOADER VOLTOU PARA O ANTERIOR
    async function proveFirmware(report){
        const end = Date.now() + PROVING
        let info  = null

        if(!hasDiagnostics(linksRef.current.mru.firmware))    // VOLTOU PARA UM FIRMWARE ANTIGO: ELE NÃO SABE RESPONDER, E TAMBÉM NÃO TEM PROVA
            return null

        while(Date.now() < end){
            const text = await ask('$diagnostics!', ['"uptime"']).catch(() => null)
            info = text ? JSON.parse(text) : info

            if(info && text && info.uptime >= PROOF)
                break

            report(`o firmware novo está em prova: ${info?.uptime ?? 0} de ${PROOF} s sem cair`)
            await sleep(1000)
        }

        return info
    }

    // SINCRONIZA, ENVIA, ESPERA VOLTAR E CONFERE: O MRU SÓ TROCA DE FIRMWARE DEPOIS DE CONFERIR O CRC, E QUALQUER FALHA DEIXA O ANTERIOR RODANDO
    async function updateFirmware(image){
        const changes = values => setFlashing(current => ({...current, ...values}))
        const before  = {firmware: linksRef.current.mru.firmware ?? null, partition: healthRef.current.info?.partition ?? null}
        updating.current = true
        setFlashing({status: 'running', stage: 'Sincronizar', message: 'conectando ao MRU', step: 0, steps: 0, log: [], started: Date.now() / 1000, image, before: before.firmware})

        try {
            if(linksRef.current.mru.state != 'synced' && !await connect('mru'))
                throw new Error(linksRef.current.mru.message || 'nenhum MRU respondeu')

            before.firmware = linksRef.current.mru.firmware ?? null
            changes({before: before.firmware})
            job.current = await call('firmware_start', {path: image.path})
            let state

            do {
                await sleep(300)
                state = await call('job_status', {id: job.current})
                changes({stage: state.stage || 'Sincronizar', message: state.message, step: state.step, steps: state.steps, log: state.log})
            } while(state.status == 'running')

            job.current = null

            if(state.status != 'done'){
                changes({stage: 'Verificar', message: 'conferindo se o MRU voltou ao normal', step: 0, steps: 0})
                const back = await sync('mru', 3)
                return changes({status: state.status, error: state.error, after: back ? linksRef.current.mru.firmware : null})
            }

            changes({stage: 'Reiniciar', message: 'esperando o MRU voltar com o firmware novo', step: 0, steps: 0, result: state.result})
            await reboot(linksRef.current.mru.settings ?? {}, message => changes({message}))
            changes({stage: 'Confirmar', message: 'conferindo a versão'})
            const info = await proveFirmware(message => changes({message}))
            await sync('mru', 3)
            const after  = linksRef.current.mru.firmware
            const rolled = info?.rolled_back && (before.partition == null || info.partition == before.partition)
            const wrong  = image.version && after != image.version
            changes({status: rolled || wrong ? 'error' : 'done', after, error: rolled ? `o firmware novo caiu e o MRU voltou sozinho para o ${after}` : wrong ? `o MRU voltou com o ${after}, e não com o ${image.version}` : null})
        }
        catch(failure) {
            changes({status: 'error', error: String(failure.message ?? failure)})
        }
        finally {
            updating.current = false
            job.current = null

            if(linksRef.current.mru.state == 'synced')
                startHealth(linksRef.current.mru.firmware).catch(() => null)
        }
    }

    function cancelUpdate(){
        if(job.current)
            call('job_cancel', {id: job.current})
    }

    const value = useMemo(() => ({links, ports, discovery, simulation, health, update: flashing, setUpdate: setFlashing, setSimulation, refreshPorts, connect, disconnect, sync, query, send, configure, reboot, updateFirmware, cancelUpdate, getSeries, getTexts, clearTexts, setLink}), [links, ports, discovery, simulation, health, flashing])
    return (
        <DeviceContext.Provider value={value}>
            <LiveContext.Provider value={live}>{children}</LiveContext.Provider>
        </DeviceContext.Provider>
    )
}
