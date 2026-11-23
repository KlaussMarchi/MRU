import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { open } from '@tauri-apps/plugin-dialog'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faBullseye, faCircle, faFileCsv, faStop } from '@fortawesome/free-solid-svg-icons'
import Page from '../../components/Page'
import ConnectionBar from '../../components/ConnectionBar'
import LiveChart from '../../components/LiveChart'
import QuantityPicker from '../../components/QuantityPicker'
import AsyncButton from '../../components/AsyncButton'
import Dropdown from '../../components/Dropdown'
import { useConfirm } from '../../components/Dialog'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, getBaud, getStamp, getStored, setStored, formatBytes, formatDuration, getQuantity, getColor, LAYOUTS, FREQUENCIES, STILL, VARIABLES } from '../../utils'
import './styles.css'

const MODES = [
    {key: 'calibration', label: 'Calibração', hint: 'SCALE · LIST · 200 Hz', layout: 'scale', detail: 'Modo aquisição do firmware: SCALE em LIST a 200 Hz, RS232/RS422 a 460800. Com a referência, a gravação vira um ensaio de calibração.'},
    {key: 'scale', label: 'Escala', hint: 'unidades físicas', streamer: 2, layout: 'scale', detail: 'Unidades físicas nos eixos do Kernel, sem a calibração do projeto.'},
    {key: 'calibrated', label: 'Calibrado', hint: 'saída de operação', streamer: 0, layout: 'calibrated', detail: 'A cadeia calibrada do firmware: a saída de operação, para validar uma calibração ou monitorar.'},
    {key: 'raw', label: 'Bruto', hint: 'inteiros do Kernel', streamer: 1, layout: 'raw', detail: 'Os inteiros que o Kernel envia, sem conversão.'}
]

const PROTOCOLS = [{value: 1, label: 'LIST (recomendado)'}, {value: 0, label: 'JSON'}]
const WINDOWS   = [{value: 30, label: '30 s'}, {value: 60, label: '1 min'}, {value: 300, label: '5 min'}]
const NAMES     = {table: 'plataforma', debug: 'debug (o próprio MRU)'}
const PHASES    = [{label: 'parado', mark: '', start: 0, end: 20}, {label: 'pitch', start: 20, end: 120}, {label: 'roll', start: 120, end: 220}, {label: 'repouso', start: 220, end: 320}]    // O PROGRAMA DO Table.ino DEPOIS DOS STILL s PARADOS
const MINIMUM   = PHASES[PHASES.length - 1].end


// UMA GRAVAÇÃO NÃO SALVA VOLTA COMO PENDENTE: O recording.json DIZ COMO PAROU; SEM ELE O APP OU O PC CAIU E O DIÁRIO VAI ATÉ O ÚLTIMO SEGUNDO GRAVADO
function getRecovered(item){
    const meta    = item.meta ?? {mode: 'desconhecido', reference: null}
    const started = item.recording?.started ?? (meta.started ? Date.parse(meta.started) / 1000 : null)
    const info    = item.recording ?? {folder: item.path, started, elapsed: item.modified && started ? item.modified - started : null, rows: {}, released: meta.released ?? null}
    const still   = info.released != null && info.elapsed != null && info.elapsed < info.released ? [`a gravação terminou nos ${STILL} s parados: a plataforma não chegou a se mover`] : []
    const how     = !item.recording ? ['a gravação foi interrompida (o app fechou ou o PC desligou): os dados vão até o último segundo gravado'] : item.recording.limit && item.recording.elapsed >= item.recording.limit ? [`parou sozinha pela duração programada (${formatDuration(item.recording.limit)})`] : []
    const error   = item.recording?.error ? [item.recording.error] : []
    return {journal: item.path, info, meta: {...meta, duration: Math.round(info.elapsed ?? 0), warnings: [...new Set([...(meta.warnings ?? []), ...still, ...how, ...error])]}}    // O meta.json DE UMA TENTATIVA DE SALVAR QUE FALHOU JÁ TRAZ OS AVISOS
}


// O QUE MANDAR AO MRU PARA ENTRAR NO MODO; NO CONVERSOR O BAUD ACOMPANHA A TAXA DO STREAM
function getChanges(mode, frequency, protocol, link){
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
    const [choice, setChoice]        = useState(null)
    const [frequency, setFrequency]  = useState(100)
    const [protocol, setProtocol]    = useState(1)
    const [debug, setDebug]          = useState(false)
    const [applying, setApplying]    = useState(false)
    const [progress, setProgress]    = useState('')
    const [failure, setFailure]      = useState('')
    const [error, setError]          = useState('')
    const [pending, setPendingState] = useState(getStored('acquisition', null))
    const [name, setName]            = useState('')
    const [folder, setFolder]        = useState(null)
    const [view, setViewState]       = useState(getStored('acquisition-view', {chart: {quantity: 'attitude', keys: ['pitch', 'roll']}, seconds: 60}))
    const [hours, setHours]          = useState('')
    const [orphans, setOrphans]      = useState([])
    const [confirmation, ask]        = useConfirm()
    const active                     = useRef(null)    // A PASTA QUE ESTA TELA VIU GRAVANDO: SE ELA PARAR SEM O CLIQUE, FOI A DURAÇÃO PROGRAMADA

    const mode        = MODES.find(item => item.key == choice)
    const link        = links.mru
    const mru         = stats.mru
    const table       = stats.table
    const synced      = link.state == 'synced'
    const flowing     = (mru?.rate ?? 0) > 0
    const stream      = flowing ? `${LAYOUTS[mru.layout]?.label ?? '?'} · ${mru.format?.toUpperCase()} · ${Math.round(mru.rate)} Hz` : null
    const prepared    = flowing && mru.layout == 'scale' && mru.rate > 150    // O QUE O MODO AQUISIÇÃO ENTREGA E O PIPELINE DE CALIBRAÇÃO ESPERA
    const current     = prepared ? 'calibration' : MODES.find(item => flowing && item.key != 'calibration' && item.layout == mru.layout)?.key
    const homing      = Boolean(table) && !(table.rate > 0)    // PLATAFORMA ABERTA E MUDA AINDA ESTÁ NO HOMING: O start SE PERDERIA
    const reference   = !prepared || homing ? null : table ? 'table' : debug ? 'debug' : null
    const calibration = reference != null
    const job         = jobs.session
    const quantity    = getQuantity(view.chart.quantity)
    const platform    = quantity.key == 'attitude' && table ? view.chart.keys.filter(key => key != 'yaw') : []
    const lines       = [...view.chart.keys.map(key => ({key, label: `${VARIABLES[key].label} MRU`, color: getColor(key)})), ...platform.map(key => ({key, role: 'table', label: `${VARIABLES[key].label} plataforma`, color: getColor(key), dash: [6, 4]}))]

    const parsed   = Number(hours.trim().replace(',', '.'))    // O CAMPO É TEXTO: type=number NO WebKit DEVOLVE VAZIO PARA "0,01" E A GRAVAÇÃO SAÍA SEM LIMITE
    const limit    = hours.trim() && parsed > 0 ? parsed * 3600 : null
    const badLimit = hours.trim() != '' && !limit

    const tag = !prepared ? {tone: '', text: 'só na calibração'} :
                reference ? {tone: 'ok', text: NAMES[reference]} :
                            {tone: 'warn', text: homing ? 'no homing' : 'falta'}

    const hint = !prepared  ? 'Para um ensaio de calibração, prepare o MRU em Calibração e conecte a plataforma.' :
                 homing     ? 'A plataforma está conectada mas ainda não transmite: espere o homing terminar.' :
                 !reference ? 'Conecte a plataforma (Table.ino, 115200 bps) ou use a referência em debug. Sem referência, grava só os dados.' : ''

    const plan = !calibration         ? `Salva ${stream ?? 'o que o MRU transmitir'} num CSV só com as colunas do stream.` :
                 reference == 'table' ? `A plataforma recebe start: ${STILL} s parada, depois pitch, roll e repouso de 100 s cada. Pare depois de ${formatDuration(MINIMUM)}.` :
                 link.simulated       ? `O MRU simulado faz o ciclo da plataforma e a referência sai dos ângulos dele, filtrados. Pare depois de ${formatDuration(MINIMUM)}.` :
                                        `A referência sai dos ângulos do próprio MRU, filtrados: deixe-o parado ${STILL} s e depois balance em pitch e em roll.`

    const reason = !flowing && link.state == 'off' ? 'Conecte o MRU no alto da tela.' :
                   !flowing                        ? 'O MRU não está transmitindo.' :
                   applying                        ? 'Esperando o MRU voltar no modo novo.' :
                   homing && prepared              ? 'Espere a plataforma terminar o homing.' :
                   badLimit                        ? 'Duração inválida: use, por exemplo, 48 ou 0,5.' : ''

    async function refreshOrphans(){
        const list = await call('list_recordings', {folder: settings.sessions}).catch(() => [])
        setOrphans(list)
        return list
    }

    useEffect(() => {
        if(recording){
            active.current = recording.folder
            return
        }

        const folder = active.current    // AINDA MARCADA: PAROU SEM O CLIQUE, PELA DURAÇÃO PROGRAMADA
        active.current = null
        refreshOrphans().then(list => {
            const item = folder && list.find(entry => entry.path == folder)

            if(item && !getStored('acquisition', null))
                setPending(getRecovered(item))
        })
    }, [recording?.folder, settings.sessions])

    // O TIPO E A REFERÊNCIA VÊM DA GRAVAÇÃO, NÃO DA TELA: SAIR DA PÁGINA NO MEIO NÃO OS MUDA; ended = false NO INÍCIO, QUANDO O AVISO DOS s PARADOS NÃO FAZ SENTIDO
    function getMeta(info, ended = true){
        const source = info.still == null ? null : info.rows.reference != null ? 'table' : 'debug'
        return {
            mode: stream ?? '—',
            reference: source,
            started: new Date(info.started * 1000).toISOString(),
            duration: Math.round(info.elapsed),
            still: info.still,
            released: info.released,
            limit: info.limit,
            align: link.status?.align ?? null,
            mru: link.status,
            settings: link.settings,
            devices: {target: stats.mru ?? null, reference: source == 'table' ? stats.table ?? null : null},
            warnings: [
                ...((stats.mru?.lost ?? 0) > 0 ? [`${stats.mru.lost} pacotes do MRU perdidos pelo salto no time`] : []),
                ...(ended && info.released != null && info.elapsed < info.released ? [`a gravação terminou nos ${STILL} s parados: a plataforma não chegou a se mover`] : [])
            ]
        }
    }

    function setView(changes){
        const next = {...view, ...changes}
        setViewState(next)
        setStored('acquisition-view', next)
    }

    function setPending(value){
        setPendingState(value)
        setStored('acquisition', value)
    }

    async function handleApply(){
        setFailure('')
        setApplying(true)

        try {
            await configure(getChanges(mode, frequency, protocol, link), setProgress)

            if(!flowing && mode.key != 'calibration')
                await send('$stream_start!')

            setProgress(`Modo ${mode.label} aplicado: confira o stream no gráfico ao lado.`)
            setChoice(null)
        }
        catch(failed) {
            setFailure(String(failed))
        }
        finally {
            setApplying(false)
        }
    }

    async function handleStart(){
        setError('')
        const journal = `${settings.sessions}/.recording-${getStamp()}`

        try {
            const info = await call('record_start', {folder: journal, still: calibration ? STILL : null, limit})
            active.current = info.folder
            await call('write_text', {path: `${journal}/meta.json`, content: JSON.stringify(getMeta(info, false), null, 4)})    // JÁ NO INÍCIO: SE O APP CAIR, A GRAVAÇÃO AINDA SE DESCREVE
        }
        catch(failed) {
            setError(String(failed))
        }
    }

    async function handleStop(){
        active.current = null
        const info = await call('record_stop')
        setName(getStamp(new Date(info.started * 1000)))
        setFolder(null)
        setPending({journal: info.folder, info, meta: getMeta(info)})
    }

    function handleResume(item){
        const recovered = getRecovered(item)
        setName(getStamp(new Date((recovered.info.started ?? Date.now() / 1000) * 1000)))
        setFolder(null)
        setPending(recovered)
    }

    async function handleSave(){
        const output = `${folder ?? settings.sessions}/${name}`
        await call('write_text', {path: `${pending.journal}/meta.json`, content: JSON.stringify(pending.meta, null, 4)})
        await startJob('session', 'Pipeline/Session/index.py', [pending.journal, output, `${pending.journal}/meta.json`])
        setPending(null)
        setOrphans(current => current.filter(item => item.path != pending.journal))
    }

    async function handleDiscard(){
        if(!await ask('Descartar a gravação', 'Os dados brutos desta gravação serão apagados.', 'Descartar'))
            return

        await call('remove_folder', {path: pending.journal}).catch(failed => setError(String(failed)))
        setPending(null)
        refreshOrphans()
    }

    async function chooseFolder(){
        const chosen = await open({directory: true, defaultPath: settings.sessions, title: 'Pasta onde salvar a sessão'})

        if(chosen)
            setFolder(chosen)
    }

    const result = job?.result ?? {}
    const state  = job ? (job.status == 'running' ? 'saving' : 'saved') : pending ? 'pending' : recording ? 'recording' : 'setup'

    return (
        <Page title='Aquisição' subtitle={recording ? `Gravando em ${recording.folder}` : 'Grave o que o MRU transmite ou prepare-o para um ensaio de calibração'} actions={<ConnectionBar role='mru'/>} className='AcquisitionPage'>
            <div className='Card AcquisitionFlow'>
                {state == 'setup' && (
                    <div className='AcquireSetup'>
                        {orphans.length > 0 && (
                            <div className='Notice warn RecoveredList'>
                                <b>{orphans.length == 1 ? 'Uma gravação não foi salva' : `${orphans.length} gravações não foram salvas`}</b>
                                {orphans.map(item => (
                                    <div key={item.path} className='RecoveredItem'>
                                        <span>{item.name}<small>{item.meta?.reference ? 'calibração' : 'dados'} · {item.meta?.mode ?? '?'} · {formatBytes(item.size)} · {item.recording ? (item.recording.error ? 'parou com erro' : 'parada') : 'interrompida'}</small></span>
                                        <AsyncButton small text='Abrir' variant='light' onClick={() => handleResume(item)}/>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className='AcquireSteps'>
                            <div className='AcquireSection'>
                                <div className='AcquireHead'>Preparar o MRU<span className='Pill'>opcional</span></div>

                                <div className='ModeGrid'>
                                    {MODES.map(item => (
                                        <button key={item.key} className={`ModeTile ${item.key == choice ? 'active' : ''}`} title={item.detail} disabled={!synced || applying} onClick={() => setChoice(item.key == choice ? null : item.key)}>
                                            <span className='ModeName'>{item.label}{item.key == current && <span className='ModeNow'>agora</span>}</span>
                                            <small>{item.hint}</small>
                                        </button>
                                    ))}
                                </div>

                                {mode && (
                                    <div className='ModeFields'>
                                        {mode.key == 'calibration' ? <div className='ModeFixed'>RS232/RS422 a 460800 bps<small>o MRU reinicia no modo aquisição</small></div> : <><Dropdown label='Frequência' value={frequency} onChange={setFrequency} options={FREQUENCIES.map(value => ({value, label: `${value} Hz`}))}/><Dropdown label='Protocolo' value={protocol} onChange={setProtocol} options={PROTOCOLS}/></>}
                                        <AsyncButton text='Aplicar' onClick={handleApply} loading={applying}/>
                                    </div>
                                )}

                                <div className={`ModeHint ${applying ? 'mono' : ''}`}>{applying ? progress : mode ? mode.detail : progress || (synced ? 'Escolha um modo para reconfigurar o MRU. Sem isso, grava como ele está.' : 'Sincronize o MRU para mudar o modo. Sem isso, grava como ele está.')}</div>
                                {failure && <div className='Notice bad ModeFailure'>{failure}</div>}
                            </div>

                            <div className='AcquireSection'>
                                <div className='AcquireHead'>Referência<span className={`Pill ${tag.tone}`}>{tag.text}</span></div>
                                <ConnectionBar role='table'/>

                                {prepared && !table && (
                                    <label className='CheckBox AcquireDebug'>
                                        <input type='checkbox' checked={debug} onChange={event => setDebug(event.target.checked)}/>
                                        <span>Referência em debug<small>os ângulos do próprio MRU filtrados, só para testar o pipeline; a calibração sai marcada</small></span>
                                    </label>
                                )}

                                {hint && <div className='Muted AcquireHint'>{hint}</div>}
                            </div>
                        </div>

                        <div className={`RecordBox ${calibration ? 'calibration' : ''}`}>
                            <div className='RecordKind'>
                                <span className='RecordIcon'><FontAwesomeIcon icon={calibration ? faBullseye : faFileCsv}/></span>
                                <span><b>{calibration ? 'Ensaio de calibração' : 'Gravação de dados'}</b><small>{calibration ? `referência: ${NAMES[reference]} · sai pronta para calibrar` : 'sai um mru.csv com o que o MRU transmitir'}</small></span>
                            </div>

                            <div className='RecordPlan'>{plan}</div>

                            <label className='RecordLimit'>
                                <span>Parar sozinha após</span>
                                <input className={`Input mono ${badLimit ? 'bad' : ''}`} inputMode='decimal' placeholder='—' value={hours} onChange={event => setHours(event.target.value)}/>
                                <span>horas</span>
                                <small>{limit ? formatDuration(limit) : 'sem limite'}</small>
                            </label>

                            {(reason || error) && <div className={`RecordReason ${error ? 'bad' : ''}`}>{error || reason}</div>}
                            <AsyncButton text={calibration ? 'Gravar ensaio de calibração' : 'Gravar dados'} icon={faCircle} variant='red' large onClick={handleStart} disabled={Boolean(reason)}/>
                        </div>
                    </div>
                )}

                {state == 'recording' && (
                    <div className='FlowState'>
                        <div className='Label'>{recording.still != null ? 'Gravando ensaio de calibração' : 'Gravando dados'}</div>
                        <div className='Elapsed'><span className='Dot pulse'/>{formatDuration(recording.elapsed)}</div>
                        {recording.limit && <div className='Muted'>Para sozinha em {formatDuration(recording.limit)} · faltam {formatDuration(recording.limit - recording.elapsed)}</div>}

                        {recording.still != null && (
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
                            <span>Stream</span><b>{stream ?? 'parado'}</b>
                            {recording.rows.reference != null && <><span>Referência</span><b>{recording.rows.reference.toLocaleString('pt-BR')} linhas · {Math.round(table?.rate ?? 0)} Hz</b></>}
                            {recording.released != null && <><span>Plataforma</span><b>{recording.elapsed < recording.released ? `parada até ${formatDuration(recording.released)}` : `em ciclo desde ${formatDuration(recording.released)}`}</b></>}
                            {recording.still != null && recording.rows.reference == null && <><span>Referência</span><b>{NAMES.debug}</b></>}
                        </div>

                        {!recording.awake && <div className='Notice warn'>Não consegui impedir a suspensão do PC: desative a suspensão automática nas configurações de energia.</div>}

                        <div className='Spacer'/>
                        <AsyncButton text='Parar gravação' icon={faStop} variant='red' large onClick={handleStop}/>
                    </div>
                )}

                {state == 'pending' && (
                    <div className='FlowState'>
                        <div className='Numbered done'><span>✓</span>{pending.meta.reference ? 'Ensaio de calibração encerrado' : 'Gravação de dados encerrada'}</div>

                        <div className='Facts wide'>
                            <span>Duração</span><b>{formatDuration(pending.info.elapsed)}</b>
                            <span>Stream</span><b>{pending.meta.mode ?? '—'}</b>
                            <span>Linhas do MRU</span><b>{pending.info.rows.target?.toLocaleString('pt-BR') ?? '—'}</b>
                            {pending.meta.reference && <><span>Referência</span><b>{NAMES[pending.meta.reference]}</b></>}
                            {pending.meta.reference == 'table' && <><span>Linhas da plataforma</span><b>{pending.info.rows.reference?.toLocaleString('pt-BR') ?? '—'}</b></>}
                            {pending.meta.reference == 'table' && <><span>Ciclo da plataforma</span><b>{pending.info.released == null || pending.info.elapsed < pending.info.released ? '—' : `desde ${formatDuration(pending.info.released)}`}</b></>}
                        </div>

                        <div className='FlowWarnings'>
                            {pending.meta.warnings.map((warning, index) => <div key={index} className='Notice warn'>{warning}</div>)}
                        </div>

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
                        <div className={`Numbered ${job.status == 'done' ? 'done' : ''}`}><span>{job.status == 'done' ? '✓' : '!'}</span>{job.status != 'done' ? 'Falha ao salvar' : result.calibration ? 'Sessão de calibração salva' : 'Dados salvos'}</div>

                        {job.status != 'done' && <div className='Notice bad'>{job.error ?? 'o script terminou com erro'}<pre className='mono'>{job.log.slice(-6).join('\n')}</pre></div>}

                        {job.status == 'done' && (
                            <>
                                <div className='Muted mono FlowPath'>{result.columns ? `${result.folder}/mru.csv` : result.folder}</div>

                                {result.columns ? (
                                    <div className='Facts wide'>
                                        <span>Linhas</span><b>{result.samples?.target?.toLocaleString('pt-BR') ?? '—'}</b>
                                        <span>Stream</span><b>{result.mode ?? '—'}</b>
                                        <span>Duração</span><b>{formatDuration(result.duration)}</b>
                                        <span>Colunas</span><b className='small mono'>{result.columns.join(', ')}</b>
                                    </div>
                                ) : (
                                    <div className='Facts wide'>
                                        <span>Amostras do MRU</span><b>{result.samples?.target?.toLocaleString('pt-BR') ?? '—'}</b>
                                        <span>Amostras da plataforma</span><b>{result.samples?.reference?.toLocaleString('pt-BR') ?? '—'}</b>
                                        <span>data.csv</span><b>{result.calibration ? `${result.data.toLocaleString('pt-BR')} linhas · ${result.static.toLocaleString('pt-BR')} paradas · ${result.rate} Hz` : 'não gerado'}</b>
                                        <span>Referência</span><b>{NAMES[result.reference] ?? '—'}</b>
                                        <span>Duração</span><b>{formatDuration(result.duration)}</b>
                                    </div>
                                )}

                                <div className='FlowWarnings'>
                                    {result.warnings?.map((warning, index) => <div key={index} className={`Notice ${warning.startsWith('referência em debug') ? 'info' : 'warn'}`}>{warning}</div>)}
                                </div>
                            </>
                        )}

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

                    <div className='Segmented'>
                        {WINDOWS.map(option => <span key={option.value} className={view.seconds == option.value ? 'on' : ''} onClick={() => setView({seconds: option.value})}>{option.label}</span>)}
                    </div>
                </div>

                <LiveChart lines={lines} unit={quantity.unit} digits={quantity.digits} seconds={view.seconds} empty={link.state == 'off' ? 'conecte o MRU no alto da tela' : 'o MRU não está transmitindo'}/>
            </div>

            {confirmation}
        </Page>
    )
}
