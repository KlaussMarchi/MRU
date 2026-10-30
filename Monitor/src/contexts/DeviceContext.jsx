import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { listen } from '@tauri-apps/api/event'
import { call, sleep, getStored, setStored, Series, ACQUISITION_BAUD } from '../utils'

const DeviceContext = createContext(undefined)
const LiveContext   = createContext(undefined)
const POLL    = 30      // ms ENTRE LEITURAS DO BACKEND: CHEGA ANTES DO ATRASO DE 0,12 s COM QUE O GRÁFICO DESENHA
const REFRESH = 250     // ms ENTRE ATUALIZAÇÕES DO ESTADO AO VIVO (ESTATÍSTICAS, GRAVAÇÃO, TERMINAL)
const TEXTS   = 4000    // LINHAS DO TERMINAL NA MEMÓRIA: 20 s DE STREAM A 200 Hz, PARA AS RESPOSTAS NÃO SUMIREM AO ESCONDER O STREAM
const BOOT    = 3500    // ms QUE O MRU LEVA PARA VOLTAR DEPOIS DO REINÍCIO
const ROLES   = ['mru', 'table']
const IDLE    = {state: 'off', port: null, baud: null, kind: null, simulated: false, status: null, settings: null, message: ''}


export function useDevice(){
    const context = useContext(DeviceContext)

    if(!context)
        throw new Error('useDevice precisa estar dentro de um DeviceProvider')

    return context
}

export function useLive(){
    return useContext(LiveContext)
}

// A CONEXÃO COM O MRU E A PLATAFORMA DE REFERÊNCIA, VIVA EM TODAS AS TELAS: LEITURA CONTÍNUA, SINCRONIZAÇÃO, COMANDOS, CONFIGURAÇÃO COM REINÍCIO E O BANCO SIMULADO
export function DeviceProvider({children}){
    const [links, setLinks]           = useState({mru: IDLE, table: IDLE})
    const [live, setLive]             = useState({stats: {}, recording: null, version: 0, texts: 0})
    const [ports, setPorts]           = useState([])
    const [discovery, setDiscovery]   = useState('')
    const [simulation, setSimulationState] = useState(getStored('simulation', {enabled: false, scenario: 'table'}))

    const series     = useRef({mru: new Series(200 * 1200), table: new Series(100 * 1200)})    // 20 MIN NA TAXA MÁXIMA DE CADA UM
    const texts      = useRef({mru: [], table: []})
    const cursors    = useRef({})
    const busy       = useRef(false)
    const recovering = useRef({})
    const latest     = useRef({stats: {}, recording: null, texts: 0})
    const linksRef   = useRef(links)
    linksRef.current = links

    useEffect(() => {
        const unlisten = listen('discover', event => setDiscovery(event.payload))
        call('simulation_set', simulation).then(refreshPorts)
        return () => { unlisten.then(stop => stop()) }
    }, [])

    useEffect(() => {
        const reader = setInterval(update, POLL)
        const screen = setInterval(() => setLive(current => ({stats: {...latest.current.stats}, recording: latest.current.recording, version: current.version + 1, texts: latest.current.texts})), REFRESH)
        return () => { clearInterval(reader); clearInterval(screen) }
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
        setStored('simulation', next)
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
                setLink(role, {state: 'synced', status, settings, firmware, message: status ? `${status.port} · firmware ${firmware}` : `firmware ${firmware ?? '?'}, anterior a v1.0.8`})
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

    const value = useMemo(() => ({links, ports, discovery, simulation, setSimulation, refreshPorts, connect, disconnect, sync, query, send, configure, reboot, getSeries, getTexts, clearTexts, setLink}), [links, ports, discovery, simulation])
    return (
        <DeviceContext.Provider value={value}>
            <LiveContext.Provider value={live}>{children}</LiveContext.Provider>
        </DeviceContext.Provider>
    )
}
