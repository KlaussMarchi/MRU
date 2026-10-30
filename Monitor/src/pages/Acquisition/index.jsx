import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { open } from '@tauri-apps/plugin-dialog'
import { faCircle, faStop } from '@fortawesome/free-solid-svg-icons'
import Page from '../../components/Page'
import ConnectionBar from '../../components/ConnectionBar'
import LiveChart from '../../components/LiveChart'
import QuantityPicker from '../../components/QuantityPicker'
import AsyncButton from '../../components/AsyncButton'
import Dropdown from '../../components/Dropdown'
import { useConfirm } from '../../components/Dialog'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, getBaud, getStamp, getStored, setStored, formatDuration, getQuantity, getColor, LAYOUTS, FREQUENCIES, STILL, VARIABLES } from '../../utils'
import './styles.css'

const MODES = [
    {key: 'calibration', label: 'Para calibração', layout: 'scale', detail: 'Modo aquisição do firmware: SCALE em LIST a 200 Hz, RS232/RS422 a 460800. É o que o pipeline de calibração espera.'},
    {key: 'scale', label: 'Escala do Kernel', streamer: 2, layout: 'scale', detail: 'Unidades físicas nos eixos do Kernel, sem a calibração do projeto.'},
    {key: 'calibrated', label: 'Calibrado', streamer: 0, layout: 'calibrated', detail: 'A cadeia calibrada do firmware, para validar uma calibração.'},
    {key: 'raw', label: 'Bruto (RAW)', streamer: 1, layout: 'raw', detail: 'Os inteiros que o Kernel envia, sem conversão.'},
    {key: 'keep', label: 'Como está', detail: 'Grava o que o MRU já transmite, sem mudar nada.'}
]

const PROTOCOLS = [{value: 1, label: 'LIST (recomendado)'}, {value: 0, label: 'JSON'}]
const WINDOWS   = [{value: 30, label: '30 s'}, {value: 60, label: '1 min'}, {value: 300, label: '5 min'}]
const NAMES     = {table: 'plataforma', debug: 'debug (o próprio MRU)'}
const PHASES    = [{label: 'parado', mark: '', start: 0, end: 20}, {label: 'pitch', start: 20, end: 120}, {label: 'roll', start: 120, end: 220}, {label: 'repouso', start: 220, end: 320}]    // O PROGRAMA DO Table.ino DEPOIS DOS STILL s PARADOS
const MINIMUM   = PHASES[PHASES.length - 1].end


// O QUE MANDAR AO MRU PARA ENTRAR NO MODO; NO CONVERSOR O BAUD ACOMPANHA A TAXA DO STREAM
function getChanges(mode, frequency, protocol, link){
    if(mode.key == 'keep')
        return null

    if(mode.key == 'calibration')
        return {kernel_mode: 0, device_mode: 1}

    const changes = {device_mode: 0, kernel_mode: 0, streamer_mode: mode.streamer, protocol, frequency, autostream: 1}
    return link.kind == 'converter' ? {...changes, baudrate: Math.max(getBaud(protocol, frequency), 115200)} : changes
}


export default function AcquisitionPage(){
    const navigate = useNavigate()
    const {links, configure, send} = useDevice()
    const {stats, recording} = useLive()
    const {settings, jobs, startJob, clearJob, setSelection, python} = useGlobalContext()
    const [modeKey, setModeKey]      = useState('calibration')
    const [frequency, setFrequency]  = useState(100)
    const [protocol, setProtocol]    = useState(1)
    const [debug, setDebug]          = useState(false)
    const [steps, setSteps]          = useState([])
    const [error, setError]          = useState('')
    const [pending, setPendingState] = useState(getStored('acquisition', null))
    const [name, setName]            = useState('')
    const [folder, setFolder]        = useState(null)
    const [view, setViewState]       = useState(getStored('acquisition-view', {chart: {quantity: 'attitude', keys: ['pitch', 'roll']}, seconds: 60}))
    const [confirmation, ask]        = useConfirm()

    const mode        = MODES.find(item => item.key == modeKey)
    const link        = links.mru
    const mru         = stats.mru
    const table       = stats.table
    const synced      = link.state == 'synced'
    const flowing     = (mru?.rate ?? 0) > 0
    const calibration = modeKey == 'calibration'
    const reference   = table ? (table.rate > 0 ? 'table' : null) : calibration && debug ? 'debug' : null    // PLATAFORMA ABERTA E MUDA AINDA ESTÁ NO HOMING: O start SE PERDERIA
    const job         = jobs.session
    const layout      = LAYOUTS[mru?.layout]
    const wrong       = calibration && flowing && mru?.layout != 'scale'
    const ready       = flowing && (mode.layout == null || (mru?.layout == mode.layout && (!calibration || mru?.rate > 150)))
    const missing     = [...(!synced ? ['conectar e sincronizar o MRU no alto da tela'] : !ready ? [flowing ? `aplicar o modo "${mode.label}" no MRU` : 'o MRU precisa estar transmitindo'] : []), ...(calibration && !reference ? [table ? 'esperar a plataforma terminar o homing e transmitir' : 'conectar a plataforma ou marcar a referência em debug'] : [])]
    const plan        = !calibration ? 'Grava o que o MRU transmite até você parar. A sessão sai sem o data.csv de calibração.' : reference == 'table' ? `Grava o MRU e a plataforma. No mesmo instante a plataforma recebe start: fica ${STILL} s parada, depois pitch 100 s, roll 100 s e repouso 100 s. Pare depois de ${formatDuration(MINIMUM)}, quando o ciclo fecha.` : link.simulated ? `Grava só o MRU simulado, que faz o ciclo da plataforma: ${STILL} s parado, pitch, roll e repouso. A referência sai dos ângulos dele, filtrados. Pare depois de ${formatDuration(MINIMUM)}.` : `Grava só o MRU; a referência sai dos ângulos dele, filtrados. Deixe-o parado nos primeiros ${STILL} s e depois balance em pitch e em roll.`
    const quantity    = getQuantity(view.chart.quantity)
    const platform    = quantity.key == 'attitude' && table ? view.chart.keys.filter(key => key != 'yaw') : []
    const lines       = [...view.chart.keys.map(key => ({key, label: `${VARIABLES[key].label} MRU`, color: getColor(key)})), ...platform.map(key => ({key, role: 'table', label: `${VARIABLES[key].label} plataforma`, color: getColor(key), dash: [6, 4]}))]

    function setView(changes){
        const next = {...view, ...changes}
        setViewState(next)
        setStored('acquisition-view', next)
    }

    function setPending(value){
        setPendingState(value)
        setStored('acquisition', value)
    }

    function report(message){
        setSteps(current => [...current, message].slice(-5))
    }

    async function handleApply(){
        setError('')
        setSteps([])
        const changes = getChanges(mode, frequency, protocol, link)

        try {
            if(changes)
                await configure(changes, report)

            if(!flowing && modeKey != 'calibration')
                await send('$stream_start!')

            report('pronto: confira o stream ao lado e inicie a gravação')
        }
        catch(failure) {
            setError(String(failure))
        }
    }

    async function handleStart(){
        setError('')
        const journal = `${settings.sessions}/.recording-${getStamp()}`

        try {
            await call('record_start', {folder: journal, still: calibration && reference ? STILL : null})
        }
        catch(failure) {
            setError(String(failure))
        }
    }

    async function handleStop(){
        const info = await call('record_stop')
        const meta = {
            mode: mode.label,
            reference,
            started: new Date(info.started * 1000).toISOString(),
            duration: Math.round(info.elapsed),
            still: info.still,
            released: info.released,
            align: link.status?.align ?? null,
            mru: link.status,
            settings: link.settings,
            devices: {target: stats.mru ?? null, reference: stats.table ?? null},
            warnings: [
                ...(wrong ? [`o MRU gravou em ${mru.layout}, não em SCALE: o pipeline de calibração não vai usar esta sessão`] : []),
                ...((stats.mru?.lost ?? 0) > 0 ? [`${stats.mru.lost} pacotes do MRU perdidos pelo salto no time`] : []),
                ...(info.released != null && info.elapsed < info.released ? [`a gravação terminou nos ${STILL} s parados: a plataforma não chegou a se mover`] : [])
            ]
        }

        setName(getStamp(new Date(info.started * 1000)))
        setFolder(null)
        setPending({journal: info.folder, info, meta})
    }

    async function handleSave(){
        const output = `${folder ?? settings.sessions}/${name}`
        await call('write_text', {path: `${pending.journal}/meta.json`, content: JSON.stringify(pending.meta, null, 4)})
        await startJob('session', 'Pipeline/Session/index.py', [pending.journal, output, `${pending.journal}/meta.json`])
        setPending(null)
    }

    async function handleDiscard(){
        if(!await ask('Descartar a gravação', 'Os dados brutos desta gravação serão apagados.', 'Descartar'))
            return

        await call('remove_folder', {path: pending.journal}).catch(failure => setError(String(failure)))
        setPending(null)
    }

    async function chooseFolder(){
        const chosen = await open({directory: true, defaultPath: settings.sessions, title: 'Pasta onde salvar a sessão'})

        if(chosen)
            setFolder(chosen)
    }

    const result = job?.result ?? {}
    const state  = job ? (job.status == 'running' ? 'saving' : 'saved') : pending ? 'pending' : recording ? 'recording' : 'setup'

    return (
        <Page title='Aquisição' subtitle={recording ? `Gravando em ${recording.folder}` : 'Configure o MRU, conecte a referência e grave o ensaio'} actions={<ConnectionBar role='mru'/>} className='AcquisitionPage'>
            <div className='Card AcquisitionFlow'>
                {state == 'setup' && (
                    <div className='CardBody'>
                        <div className='FlowStep'>
                            <div className={`Numbered ${ready ? 'done' : ''}`}><span>{ready ? '✓' : 1}</span>Modo do MRU<span className={`Pill ${ready ? 'ok' : flowing ? 'warn' : ''}`}>{ready ? 'pronto' : flowing ? 'aplicar' : 'sem stream'}</span></div>

                            <div className='Choices'>
                                {MODES.map(item => (
                                    <div key={item.key} className={`Choice ${item.key == modeKey ? 'active' : ''}`} onClick={() => setModeKey(item.key)}>
                                        <div className='ChoiceTitle'>{item.label}</div>
                                        {item.key == modeKey && <div className='ChoiceText'>{item.detail}</div>}
                                    </div>
                                ))}
                            </div>

                            {!['calibration', 'keep'].includes(modeKey) && (
                                <div className='Row FlowFields'>
                                    <div className='Grow'><Dropdown label='Frequência' value={frequency} onChange={setFrequency} options={FREQUENCIES.map(value => ({value, label: `${value} Hz`}))}/></div>
                                    <div className='Grow'><Dropdown label='Protocolo' value={protocol} onChange={setProtocol} options={PROTOCOLS}/></div>
                                </div>
                            )}

                            <div className='FlowNow'>
                                <span className='Muted'>O MRU transmite<b>{flowing ? `${layout?.label ?? '?'} · ${mru.format?.toUpperCase()} · ${Math.round(mru.rate)} Hz` : synced ? 'nada' : 'MRU desconectado'}</b></span>
                                {modeKey != 'keep' && <AsyncButton small text={ready ? 'Aplicar de novo' : 'Aplicar no MRU'} variant={ready ? 'ghost' : 'dark'} onClick={handleApply} disabled={!synced}/>}
                            </div>

                            {steps.length > 0 && <div className='Steps mono'>{steps.map((step, index) => <div key={index}>{step}</div>)}</div>}
                        </div>

                        <div className='FlowStep'>
                            <div className={`Numbered ${reference ? 'done' : ''}`}><span>{reference ? '✓' : 2}</span>Referência<span className={`Pill ${reference ? 'ok' : calibration ? 'warn' : ''}`}>{reference ? NAMES[reference] : calibration ? 'falta' : 'opcional'}</span></div>
                            <ConnectionBar role='table'/>

                            {!table && calibration && (
                                <label className='CheckBox FlowCheck'>
                                    <input type='checkbox' checked={debug} onChange={event => setDebug(event.target.checked)}/>
                                    <span>Sem plataforma · referência em debug<small>os ângulos do próprio MRU filtrados, só para testar o pipeline de ponta a ponta; a calibração sai marcada</small></span>
                                </label>
                            )}

                            {table && !reference && <div className='Notice warn FlowHint'>A plataforma está conectada mas não transmite: espere o homing terminar.</div>}
                            {!table && <div className='Muted FlowHint'>{calibration ? 'Conecte a plataforma (Table.ino, 115200 bps) ou marque a referência em debug.' : 'Fora do modo de calibração a referência é opcional.'}</div>}
                        </div>

                        <div className='FlowStep'>
                            <div className='Numbered'><span>3</span>Gravar</div>

                            <div className='FlowPlan'>{plan}</div>

                            {missing.length > 0 && <div className='FlowMissing'>{missing.map(item => <div key={item}>• {item}</div>)}</div>}

                            <AsyncButton text='Iniciar gravação' icon={faCircle} variant='red' large onClick={handleStart} disabled={missing.length > 0}/>
                            {error && <div className='Notice bad FlowHint'>{error}</div>}
                        </div>
                    </div>
                )}

                {state == 'recording' && (
                    <div className='FlowState'>
                        <div className='Label'>Gravando</div>
                        <div className='Elapsed'><span className='Dot pulse'/>{formatDuration(recording.elapsed)}</div>

                        {calibration && reference && (
                            <div className='Timeline'>
                                <div className='TimelineBar'>
                                    {PHASES.map(phase => <div key={phase.label} className={`TimelinePhase ${recording.elapsed >= phase.end ? 'done' : recording.elapsed >= phase.start ? 'now' : ''}`} style={{flex: phase.end - phase.start}}/>)}
                                    <div className='TimelineMark' style={{left: `${Math.min(100, 100 * recording.elapsed / MINIMUM)}%`}}/>
                                </div>

                                <div className='TimelineLabels'>
                                    {PHASES.map(phase => <span key={phase.label} style={{flex: phase.end - phase.start}} title={phase.label}>{phase.mark ?? phase.label}</span>)}
                                </div>

                                <div className='Muted'>{recording.elapsed >= MINIMUM ? 'Ciclo completo: já pode parar.' : `Fase: ${PHASES.find(phase => recording.elapsed < phase.end).label} · faltam ${formatDuration(MINIMUM - recording.elapsed)} para completar o ciclo.`}</div>
                            </div>
                        )}

                        <div className='Facts wide'>
                            <span>MRU</span><b>{(recording.rows.target ?? 0).toLocaleString('pt-BR')} linhas · {Math.round(mru?.rate ?? 0)} Hz · {mru?.lost ?? 0} perdidas</b>
                            {recording.rows.reference != null && <><span>Referência</span><b>{recording.rows.reference.toLocaleString('pt-BR')} linhas · {Math.round(table?.rate ?? 0)} Hz</b></>}
                            {recording.released != null && <><span>Plataforma</span><b>{recording.elapsed < recording.released ? `parada até ${formatDuration(recording.released)}` : `em ciclo desde ${formatDuration(recording.released)}`}</b></>}
                            {recording.rows.reference == null && <><span>Referência</span><b>{NAMES[reference] ?? 'nenhuma'}</b></>}
                        </div>

                        {wrong && <div className='Notice warn'>O MRU está em {layout?.label}, não em SCALE: esta gravação não serve para calibrar.</div>}

                        <div className='Spacer'/>
                        <AsyncButton text='Parar gravação' icon={faStop} variant='red' large onClick={handleStop}/>
                    </div>
                )}

                {state == 'pending' && (
                    <div className='FlowState'>
                        <div className='Numbered done'><span>✓</span>Gravação encerrada</div>

                        <div className='Facts wide'>
                            <span>Duração</span><b>{formatDuration(pending.info.elapsed)}</b>
                            <span>Linhas do MRU</span><b>{(pending.info.rows.target ?? 0).toLocaleString('pt-BR')}</b>
                            <span>Linhas da plataforma</span><b>{(pending.info.rows.reference ?? 0).toLocaleString('pt-BR')}</b>
                            <span>Ciclo da plataforma</span><b>{pending.info.released == null || pending.info.elapsed < pending.info.released ? '—' : `desde ${formatDuration(pending.info.released)}`}</b>
                            <span>Referência</span><b>{NAMES[pending.meta.reference] ?? 'nenhuma'}</b>
                        </div>

                        {pending.meta.warnings.map(warning => <div key={warning} className='Notice warn'>{warning}</div>)}

                        <label className='Field'>
                            <span className='Label'>Nome da sessão</span>
                            <input className='Input' value={name} onChange={event => setName(event.target.value.replace(/[\\/]/g, '-'))}/>
                        </label>

                        <div className='Field'>
                            <span className='Label'>Pasta</span>
                            <div className='Row'>
                                <input className='Input Grow' readOnly value={folder ?? `${settings.sessions} (padrão)`} title={folder ?? settings.sessions}/>
                                <AsyncButton small text='Escolher…' variant='light' onClick={chooseFolder}/>
                            </div>
                        </div>

                        {python?.missing?.length > 0 && <div className='Notice warn'>O Python configurado não tem {python.missing.join(', ')}: ajuste em Ajustes antes de salvar.</div>}

                        <div className='Spacer'/>
                        <div className='Actions end'>
                            <AsyncButton text='Descartar' variant='ghost' onClick={handleDiscard}/>
                            <AsyncButton text='Salvar sessão' onClick={handleSave} disabled={!name.trim() || python?.error}/>
                        </div>
                    </div>
                )}

                {state == 'saving' && (
                    <div className='FlowState'>
                        <div className='Numbered'><span className='Spinner'/>Salvando a sessão</div>
                        <div className='Muted'>{job.stage} · {job.message}</div>
                        <div className='Progress'><div style={{width: `${job.steps ? 100 * job.step / job.steps : 10}%`}}/></div>
                    </div>
                )}

                {state == 'saved' && (
                    <div className='FlowState'>
                        <div className={`Numbered ${job.status == 'done' ? 'done' : ''}`}><span>{job.status == 'done' ? '✓' : '!'}</span>{job.status == 'done' ? 'Sessão salva' : 'Falha ao salvar'}</div>

                        {job.status != 'done' && <div className='Notice bad'>{job.error ?? 'o script terminou com erro'}<pre className='mono'>{job.log.slice(-6).join('\n')}</pre></div>}

                        {job.status == 'done' && (
                            <>
                                <div className='Muted mono FlowPath'>{result.folder}</div>

                                <div className='Facts wide'>
                                    <span>Amostras do MRU</span><b>{result.samples?.target?.toLocaleString('pt-BR') ?? '—'}</b>
                                    <span>Amostras da plataforma</span><b>{result.samples?.reference?.toLocaleString('pt-BR') ?? '—'}</b>
                                    <span>data.csv</span><b>{result.calibration ? `${result.data.toLocaleString('pt-BR')} linhas · ${result.static.toLocaleString('pt-BR')} paradas · ${result.rate} Hz` : 'não gerado'}</b>
                                    <span>Referência</span><b>{NAMES[result.reference] ?? '—'}</b>
                                    <span>Duração</span><b>{formatDuration(result.duration)}</b>
                                </div>

                                {result.warnings?.map(warning => <div key={warning} className={`Notice ${warning.startsWith('referência em debug') ? 'info' : 'warn'}`}>{warning}</div>)}
                            </>
                        )}

                        <div className='Spacer'/>
                        <div className='Actions end'>
                            {job.status == 'done' && <AsyncButton small text='Abrir pasta' variant='light' onClick={() => call('open_path', {path: result.folder})}/>}
                            <AsyncButton small text='Nova gravação' variant='light' onClick={() => clearJob('session')}/>
                            {result.calibration && <AsyncButton small text='Calibrar esta sessão' onClick={() => { setSelection(current => ({...current, session: result.folder})); clearJob('session'); navigate('/Calibration') }}/>}
                        </div>
                    </div>
                )}
            </div>

            <div className='Card AcquisitionChart'>
                <div className='Toolbar'>
                    <QuantityPicker value={view.chart} onChange={chart => setView({chart})}/>
                    <div className='Spacer'/>
                    <span className={`Pill ${flowing ? layout?.tone ?? '' : ''}`}>MRU {flowing ? `${layout?.label ?? '?'} · ${mru.format?.toUpperCase()} · ${Math.round(mru.rate)} Hz` : 'parado'}</span>
                    <span className={`Pill ${table ? 'info' : ''}`}>plataforma {table ? `${Math.round(table.rate)} Hz` : reference == 'debug' ? 'em debug' : '—'}</span>

                    <div className='Segmented'>
                        {WINDOWS.map(option => <span key={option.value} className={view.seconds == option.value ? 'on' : ''} onClick={() => setView({seconds: option.value})}>{option.label}</span>)}
                    </div>
                </div>

                <LiveChart lines={lines} unit={quantity.unit} digits={quantity.digits} seconds={view.seconds} empty={synced ? 'o MRU não está transmitindo: aplique um modo' : 'conecte o MRU no alto da tela'}/>
            </div>

            {confirmation}
        </Page>
    )
}
