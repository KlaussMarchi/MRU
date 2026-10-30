import { Fragment, useEffect, useState } from 'react'
import Page from '../../components/Page'
import ConnectionBar from '../../components/ConnectionBar'
import AsyncButton from '../../components/AsyncButton'
import Dropdown from '../../components/Dropdown'
import Terminal from '../../components/Terminal'
import Dialog, { useConfirm } from '../../components/Dialog'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { getBaud, getLoad, formatNumber, ALIGNS, BAUDS, DEVICE_MODES, FREQUENCIES, KERNEL_MODES, MODELS, OUTPUTS, PROTOCOLS, STREAMER_MODES } from '../../utils'
import './styles.css'

const FIELDS = [
    {key: 'device_mode', label: 'Modo', options: DEVICE_MODES},
    {key: 'streamer_mode', label: 'Processamento', options: STREAMER_MODES},
    {key: 'kernel_mode', label: 'Pacote do Kernel', options: KERNEL_MODES},
    {key: 'protocol', label: 'Protocolo', options: PROTOCOLS},
    {key: 'frequency', label: 'Frequência', options: FREQUENCIES.map(value => ({value, label: `${value} Hz`}))},
    {key: 'baudrate', label: 'Baud da UART', options: BAUDS.map(value => ({value, label: String(value)}))},
    {key: 'output', label: 'Porta ao ligar', options: OUTPUTS},
    {key: 'autostream', label: 'Autostream', options: [{value: 1, label: 'sim'}, {value: 0, label: 'não'}]}
]

const FALLBACK = {frequency: 100, baudrate: 9600, output: 3}    // O QUE O FIRMWARE USA SEM VALOR GRAVADO


// OS VALORES GRAVADOS COMO NÚMEROS (O FIRMWARE GUARDA TEXTO; autostream PODE SER true/false)
function getForm(settings){
    const form = {}

    for(const field of FIELDS){
        const value = settings?.[field.key] ?? FALLBACK[field.key] ?? 0
        form[field.key] = value === true || value === 'true' ? 1 : value === false || value === 'false' ? 0 : Number(value)
    }

    return form
}


export default function DevicePage(){
    const {links, query, send, configure, reboot, sync} = useDevice()
    const {stats} = useLive()
    const link   = links.mru
    const synced = link.state == 'synced'
    const active = !['off', 'error'].includes(link.state)
    const status = link.status
    const [json, setJson] = useState(null)
    const [confirmation, ask] = useConfirm()
    const [form, setForm]   = useState(getForm(link.settings))
    const [align, setAlign] = useState(1)
    const [log, setLog]     = useState([])
    const [error, setError] = useState('')
    const saved    = getForm(link.settings)
    const changes  = Object.fromEntries(Object.entries(form).filter(([key, value]) => saved[key] != value))
    const load     = getLoad(form.protocol, form.frequency, form.baudrate)

    useEffect(() => {
        setForm(getForm(link.settings))
    }, [link.settings])

    function report(message){
        setLog(current => [...current, message].slice(-4))
    }

    async function run(action){
        setError('')
        setLog([])

        try {
            await action()
        }
        catch(failure) {
            setError(String(failure.message ?? failure))
        }
    }

    const legacy = link.settings && !status ? [
        ['Firmware', `${link.firmware ?? '?'} (sem $status!: atualize para v1.0.8)`],
        ['Gravado', `${DEVICE_MODES.find(item => item.value == saved.device_mode)?.label} · ${STREAMER_MODES.find(item => item.value == saved.streamer_mode)?.label} · ${PROTOCOLS.find(item => item.value == saved.protocol)?.label} · ${saved.frequency} Hz`],
        ['Link', `${link.port} · ${link.baud} bps`]
    ] : []

    // O $status! (EFETIVO) E O $settings! (GRAVADO) COMO O MRU RESPONDE AGORA
    async function showJson(){
        const read = (command, expect) => query(command, expect, 2500).then(text => JSON.stringify(JSON.parse(text), null, 2)).catch(failure => `sem resposta: ${failure}`)
        setJson({status: await read('$status!', ['"firmware"']), settings: await read('$settings!', ['"device_mode"', '"protocol"', '"telemetry"'])})
    }

    const tiles = [
        ['Porta', active ? (link.simulated ? link.label?.split(' · ')[0] : link.port) : '—'],
        ['Link', status?.port ?? (active ? (link.kind == 'usb' ? 'USB' : 'RS232/RS422') : '—')],
        ['Baud', active ? `${link.kind == 'usb' ? 'USB' : link.baud}` : '—'],
        ['Recebendo', active ? `${Math.round(stats.mru?.rate ?? 0)} Hz` : '—']
    ]

    const facts = status ? [
        ['Modo', `${DEVICE_MODES.find(item => item.value == status.device_mode)?.label} · ${STREAMER_MODES.find(item => item.value == status.streamer_mode)?.label} · ${PROTOCOLS.find(item => item.value == status.protocol)?.label}`],
        ['Kernel', `${KERNEL_MODES.find(item => item.value == status.kernel_mode)?.label} · ${status.kernel_baud} bps · ${status.sensor ? 'respondendo' : 'SEM RESPOSTA'}`],
        ['Stream', `${status.device_mode == 1 ? '200 Hz (aquisição)' : `${formatNumber(status.frequency, 0)} Hz`} · ${status.streaming ? 'transmitindo' : 'parado'} · autostream ${status.autostream ? 'ligado' : 'desligado'}`],
        ['Align do Kernel', status.align?.map(value => value == null ? '?' : formatNumber(value, 0)).join(' · ') ?? '—'],
        ['Calibração', `${status.calibration == 'flash' ? 'gravada na flash' : 'compilada'} · ${MODELS[status.model] ?? '—'}`],
        ['Cadeia', status.processing]
    ] : []

    return (
        <Page title='Dispositivo' subtitle='Estado, configuração e terminal do MRU: os comandos ficam liberados depois do ACK' actions={<ConnectionBar role='mru'/>} className='DevicePage'>
            <div className='DeviceStatus'>
                <div className='Card'>
                    <div className='Identity'>
                        <div>
                            <div className='IdentityName'>{status?.id ?? (active ? 'MRU' : 'Nenhum MRU')}{status?.simulated && <span className='Pill info'>simulado</span>}</div>
                            <div className='Muted'>{link.firmware ? `firmware ${link.firmware}` : active ? 'sincronize para identificar' : 'conecte no alto da tela'}{active ? ` · ${link.label ?? link.port}` : ''}</div>
                        </div>

                        <button className='LinkButton' onClick={() => sync()} disabled={!active}>atualizar</button>
                    </div>

                    <div className='MruTiles'>
                        {tiles.map(([label, value]) => <div key={label} className='MruTile'><span>{label}</span><b title={value}>{value}</b></div>)}
                    </div>

                    <div className='Facts'>
                        {[...facts, ...legacy].map(([label, value]) => <Fragment key={label}><span>{label}</span><b className={label == 'Cadeia' ? 'small' : ''} title={value}>{value}</b></Fragment>)}
                    </div>

                    <div className='DeviceActions'>
                        <AsyncButton small variant='accent' text='Reiniciar MRU' disabled={!active} onClick={() => run(async () => { await send('MICRS'); await reboot(link.settings ?? {}, report) })}/>
                        <AsyncButton small variant='light' text='Ver configuração (JSON)' disabled={!active} onClick={() => run(showJson)}/>
                        <AsyncButton small variant='light' text={status?.streaming ? 'Parar stream' : 'Iniciar stream'} disabled={!synced} onClick={() => run(async () => { await send(status?.streaming ? '$stream_stop!' : '$stream_start!'); await sync() })}/>
                        <AsyncButton small variant='light' text='Verificar sensor' disabled={!synced} onClick={() => run(async () => report(`sensor: ${await query('$check_sensor!', ['OK', 'NOT WORKING'])}`))}/>
                        <AsyncButton small variant='ghost' text='Restaurar padrões' disabled={!synced} onClick={() => run(async () => { if(!await ask('Restaurar padrões', 'Restaurar as configurações de fábrica do ESP32? Não apaga a calibração nem o align do Kernel.', 'Restaurar')) return; await send('$ERASE!'); await reboot({}, report) })}/>
                    </div>
                </div>

                <div className='Card'>
                    <div className='CardTitle'>Montagem do Kernel (align) <span className='hint'>X do Kernel para boreste</span></div>

                    <div className='Row'>
                        <div className='Grow'><Dropdown value={align} options={ALIGNS} onChange={setAlign} disabled={!synced}/></div>
                        <AsyncButton text='Gravar' variant='light' disabled={!synced} onClick={() => run(async () => report(await query(`$align:${align}!`, ['ALIGNMENT COMPLETE'], 5000)))}/>
                    </div>

                    <div className='Muted' style={{marginTop: '.6rem'}}>Depois de gravar, desligue e ligue o MRU: reiniciar só o ESP32 não reinicia o Kernel. Calibre na posição em que ele vai operar.</div>
                </div>
            </div>

            <div className='Card DeviceConfig'>
                <div className='CardTitle'>Configuração <span className='hint'>{Object.keys(changes).length ? `${Object.keys(changes).length} alteração(ões) · aplicadas num reinício só` : 'igual ao gravado no MRU'}</span></div>

                <div className='FormGrid'>
                    {FIELDS.map(field => (
                        <div key={field.key} className={changes[field.key] != null ? 'changed' : ''}>
                            <Dropdown label={field.label} value={form[field.key]} disabled={!synced} options={field.options} onChange={value => setForm({...form, [field.key]: Number(value)})}/>
                        </div>
                    ))}
                </div>

                <div className='DeviceApply'>
                    {form.device_mode == 1
                        ? <div className='Notice info'>No modo aquisição o firmware fixa SCALE, LIST, 200 Hz e 460800 bps: os outros campos valem quando o MRU voltar ao modo normal.</div>
                        : <div className={`Notice ${load > 1 ? 'bad' : load > 0.6 ? 'warn' : ''}`}>{formatNumber(form.frequency, 0)} Hz em {PROTOCOLS.find(item => item.value == form.protocol)?.label} ocupam {(load * 100).toFixed(0)}% de {form.baudrate} bps{load > 0.6 ? `: use ao menos ${getBaud(form.protocol, form.frequency)}` : ''}.</div>}

                    <AsyncButton variant='ghost' text='Desfazer' disabled={!Object.keys(changes).length} onClick={() => setForm(saved)}/>
                    <AsyncButton text='Aplicar e reiniciar' disabled={!synced || !Object.keys(changes).length} onClick={() => run(() => configure(changes, report))}/>
                </div>

                {log.length > 0 && <div className='Steps mono'>{log.map((line, index) => <div key={index}>{line}</div>)}</div>}
                {error && <div className='Notice bad' style={{marginTop: '.6rem'}}>{error}</div>}
            </div>

            {confirmation}

            {json && (
                <Dialog title='Configuração do MRU' onClose={() => setJson(null)} actions={<><AsyncButton small variant='light' text='Perguntar de novo' onClick={showJson}/><AsyncButton small text='Fechar' onClick={() => setJson(null)}/></>}>
                    <div className='Label'>Estado efetivo · $status!</div>
                    <pre className='DialogJson mono'>{json.status}</pre>
                    <div className='Label' style={{marginTop: '.8rem'}}>Gravado na flash · $settings!</div>
                    <pre className='DialogJson mono'>{json.settings}</pre>
                </Dialog>
            )}

            <div className='Card DeviceTerminal'>
                <div className='CardTitle'>Terminal serial</div>
                <Terminal role='mru' hint='CF:chave$valor! grava e reinicia · CS:chave$valor! só grava · ID:chave$ consulta'/>
            </div>
        </Page>
    )
}
