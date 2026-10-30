import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { open, save } from '@tauri-apps/plugin-dialog'
import Page from '../../components/Page'
import AsyncButton from '../../components/AsyncButton'
import Dropdown from '../../components/Dropdown'
import Overlay from '../../components/Overlay'
import StaticChart from '../../components/StaticChart'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, getStamp, getColor, formatNumber, formatDuration, formatBytes, ALIGNS, MODELS } from '../../utils'
import './styles.css'

const STRATEGIES = {
    KalmanFusion: 'Fusão de acelerômetro e giro (MEKF) com ruídos e braço buscados pela CMA-ES contra a referência; a do firmware atual. Uns 4 min num ensaio de 5 min a 200 Hz.',
    LinearFit: 'Ajuste linear dos ângulos do próprio Kernel contra a referência; o mais rápido, menos de 30 s.',
    MachineLearning: 'Regressão sobre uma janela de 30 estados dos sensores corrigidos; menos de 1 min.'
}

const STAGES = ['Format', 'Filtros', 'Correção', 'Atitude', 'Heave', 'Braço de alavanca', 'Análise', 'Certificado']    // AS ETAPAS DO Pipeline, NA ORDEM E COM OS NOMES DOS EVENTOS DE PROGRESSO

const METRICS  = ['pitch', 'roll', 'yaw', 'heave', 'hr']
const SENSORS  = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
const PREVIEW  = ['time', 'static', 'target_pitch', 'target_roll', 'ref_pitch', 'ref_roll']
const NO_ALIGN = 'none'
const AXES     = ['x · proa', 'y · boreste', 'z · baixo']

const LINES = [
    {label: 'pitch MRU', color: getColor('pitch')},
    {label: 'roll MRU', color: getColor('roll')},
    {label: 'pitch referência', color: getColor('pitch'), dash: [6, 4]},
    {label: 'roll referência', color: getColor('roll'), dash: [6, 4]}
]


function getPreview(response){
    if(!response?.rows.length)
        return null

    const columns = Object.fromEntries(response.columns.map((name, index) => [name, response.rows.map(row => row[index])]))
    const angles  = ['target_pitch', 'target_roll', 'ref_pitch', 'ref_roll'].map(name => columns[name] ?? response.rows.map(() => null))
    return {angles: [columns.time, ...angles], still: columns.static?.filter(value => value == 1).length / response.rows.length}
}


export default function CalibrationPage(){
    const navigate = useNavigate()
    const {settings, python, jobs, startJob, cancelJob, clearJob, selection, setSelection} = useGlobalContext()
    const [sessions, setSessions] = useState([])
    const [library, setLibrary]   = useState([])
    const [source, setSource]     = useState(selection.session)
    const [preview, setPreview]   = useState(null)
    const [strategy, setStrategy] = useState('LinearFit')
    const [point, setPoint]       = useState(['0', '0', '0'])
    const [gravity, setGravity]   = useState('9.785')
    const [serial, setSerial]     = useState('')
    const [align, setAlign]       = useState(NO_ALIGN)
    const [chosen, setChosen]     = useState(null)
    const [error, setError]       = useState('')
    const job = jobs.pipeline

    useEffect(() => {
        if(settings.sessions)
            refresh()
    }, [settings.sessions, settings.calibrations])

    useEffect(() => {
        if(job?.status == 'done'){
            refresh()
            setChosen(job.result?.folder ?? null)
        }
    }, [job?.status])

    async function refresh(){
        const [sessionList, calibrationList] = await Promise.all([call('list_sessions', {folder: settings.sessions}), call('list_calibrations', {folder: settings.calibrations})])
        const usable = sessionList.filter(item => item.files['data.csv'] || item.files['target.csv'])
        setSessions(usable)
        setLibrary(calibrationList.filter(item => item.info))
        setSource(current => current ?? usable.find(item => item.info?.calibration)?.path ?? null)
    }

    const current = useMemo(() => {
        if(!source)
            return null

        return sessions.find(item => item.path == source) ?? {name: source.split(/[\\/]/).pop(), path: source, info: null, files: {}}
    }, [source, sessions])

    const dataPath = current ? `${current.path}/data.csv` : null

    useEffect(() => {
        setPreview(null)

        if(!current)
            return

        const known  = current.info?.align
        const preset = ALIGNS.find(item => JSON.stringify(item.angles) == JSON.stringify(known))
        setAlign(preset ? preset.value : NO_ALIGN)

        if(current.info?.mru?.id)
            setSerial(current.info.mru.id)

        call('csv_preview', {path: dataPath, columns: PREVIEW}).then(response => setPreview(getPreview(response))).catch(() => setPreview(false))
    }, [current?.path, Boolean(current?.info)])    // A SESSÃO VINDA DA AQUISIÇÃO CHEGA ANTES DA LISTA: O info DELA (SÉRIE, ALIGN) SÓ VEM DEPOIS

    async function chooseFolder(){
        const folder = await open({directory: true, defaultPath: settings.sessions, title: 'Sessão com data.csv'})

        if(folder)
            setSource(folder)
    }

    async function handleRun(){
        setError('')
        const angles  = align == NO_ALIGN ? null : ALIGNS.find(item => item.value == align).angles
        const request = {session: current.path, output: settings.calibrations, strategy, gravity: Number(gravity), id: serial || null, align: angles, point: point.map(Number), copy_data: true}
        const path    = `${settings.calibrations}/.jobs/${getStamp()}.json`

        try {
            await call('write_text', {path, content: JSON.stringify(request, null, 4)})
            await startJob('pipeline', 'Pipeline/index.py', [path])
        }
        catch(failure) {
            setError(String(failure))
        }
    }

    async function exportPdf(item){
        const target = await save({defaultPath: `certificado_${item.info.id ?? 'MRU'}_${item.name}.pdf`, filters: [{name: 'PDF', extensions: ['pdf']}]})

        if(target)
            await call('copy_file', {from: `${item.path}/certificate.pdf`, to: target})
    }

    const ready    = current?.files?.['data.csv'] && point.every(value => Number.isFinite(Number(value)))
    const missing  = Boolean(python?.error || python?.missing?.length)
    const selected = library.find(item => item.path == chosen)
    const info     = current?.info
    const debug    = info?.reference == 'debug'

    return (
        <Page title='Calibração' subtitle='Filtros, correção, atitude, heave e braço sobre uma sessão gravada; o resultado vira um pacote com certificado e parâmetros' className='CalibrationPage'>
            {job?.status == 'running' && (
                <Overlay title={`Calibrando ${serial || 'o MRU'} · ${strategy}`} stage={job.stage} message={job.message} progress={job.steps ? job.step / job.steps : null} started={job.started} log={job.log} stages={STAGES}>
                    <AsyncButton text='Cancelar' variant='light' onClick={() => cancelJob('pipeline')}/>
                </Overlay>
            )}

            <div className='Card CalibrationSessions'>
                <div className='CardTitle'>Sessões <span className='hint'><button className='LinkButton' onClick={chooseFolder}>outra pasta…</button></span></div>

                <div className='List'>
                    {sessions.length == 0 && (
                        <div className='Empty'>
                            <span>Nenhuma sessão gravada ainda.</span>
                            <AsyncButton small text='Gravar em Aquisição' variant='light' onClick={() => navigate('/Acquisition')}/>
                        </div>
                    )}

                    {sessions.map(item => (
                        <div key={item.path} className={`ListItem ${source == item.path ? 'selected' : ''}`} onClick={() => setSource(item.path)}>
                            <div className='ListName'><span>{item.name}</span>{item.info?.reference == 'debug' && <span className='Pill info'>debug</span>}</div>
                            <div className='ListMeta'>{item.info?.calibration ? `${formatDuration(item.info.duration)} · ${item.info.rate} Hz · ${item.info.mru?.id ?? item.info.mode ?? ''}` : 'sem data.csv de calibração'}</div>
                        </div>
                    ))}
                </div>
            </div>

            <div className='Card CalibrationPreview'>
                <div className='CardTitle'>
                    {current ? current.name : 'Prévia da sessão'}
                    {info?.calibration && <span className='Pill ok'>pronta para calibrar</span>}
                    {debug && <span className='Pill info'>referência em debug</span>}
                    {info?.data && <span className='hint'>{info.data.toLocaleString('pt-BR')} amostras · {info.rate} Hz · {formatDuration(info.duration)} · {((preview?.still ?? 0) * 100).toFixed(0)}% parado</span>}
                </div>

                {preview === false && <div className='Notice warn'>Não há data.csv nesta pasta: grave com o MRU e a referência no modo de calibração.</div>}
                {current && preview !== false && <StaticChart unit='°' data={preview?.angles} lines={LINES}/>}
                {!current && <div className='Empty'>A prévia mostra os ângulos do MRU contra os da referência. Os eixos do MRU ainda são os do Kernel: o Format os reordena.</div>}
                {info?.warnings?.filter(warning => !warning.startsWith('referência em debug')).map(warning => <div key={warning} className='Notice warn' style={{marginTop: '.5rem'}}>{warning}</div>)}
            </div>

            <div className='Card CalibrationPipeline'>
                <div className='PipelineTop'>
                    <div className='Grow'>
                        <div className='Label'>Estratégia de atitude</div>
                        <div className='Segmented wide'>
                            {MODELS.map(model => <span key={model} className={strategy == model ? 'on' : ''} onClick={() => setStrategy(model)}>{model}</span>)}
                        </div>
                        <div className='Muted PipelineHint'>{STRATEGIES[strategy]}</div>
                    </div>

                    <AsyncButton text='Calibrar' large onClick={handleRun} disabled={!ready || missing || !Number(gravity)}/>
                </div>

                <div className='PipelineFields'>
                    <label className='Field'>
                        <span className='Label'>Gravidade (m/s²)</span>
                        <input className='Input mono' value={gravity} onChange={event => setGravity(event.target.value)}/>
                    </label>

                    <label className='Field'>
                        <span className='Label'>Número de série</span>
                        <input className='Input mono' value={serial} placeholder='id do MRU' onChange={event => setSerial(event.target.value)}/>
                    </label>

                    <div className='Field Wide'>
                        <Dropdown label='Montagem no ensaio (align)' value={align} onChange={setAlign} options={[{value: NO_ALIGN, label: 'Não registrada'}, ...ALIGNS]}/>
                    </div>

                    <div className='Field Wide' title='LEVER_POINT: do MRU até o ponto de interesse, como o centro do helideque; zero deixa o heave no sensor'>
                        <span className='Label'>Ponto do heave x · y · z (m)</span>
                        <div className='PointFields'>
                            {AXES.map((label, index) => <input key={label} className='Input mono' value={point[index]} title={`LEVER_POINT ${label}`} onChange={event => setPoint(point.map((value, k) => k == index ? event.target.value : value))}/>)}
                        </div>
                    </div>
                </div>

                {debug && <div className='Notice info PipelineNotice'>Referência em debug: a calibração roda inteira, mas compara o MRU com ele mesmo e o certificado sai marcado.</div>}
                {missing && <div className='Notice warn PipelineNotice'>Python {settings.python}: {python.error ?? `faltam ${python.missing.join(', ')}`}. Ajuste em Ajustes.</div>}
                {error && <div className='Notice bad PipelineNotice'>{error}</div>}

                {job && job.status != 'running' && (
                    <div className={`Notice ${job.status == 'done' ? 'ok' : 'bad'} PipelineNotice`}>
                        {job.status == 'done' ? `Calibração concluída em ${formatDuration((job.finished ?? job.started) - job.started)}: o pacote está selecionado ao lado.` : job.status == 'cancelled' ? 'Pipeline cancelado.' : `O pipeline parou: ${job.error}`}
                        <button className='LinkButton' style={{marginLeft: '.6rem'}} onClick={() => clearJob('pipeline')}>ok</button>
                    </div>
                )}
            </div>

            <div className='CalibrationLibrary'>
                <div className='Card fill'>
                    <div className='CardTitle'>Calibrações <span className='hint'><button className='LinkButton' onClick={() => call('open_path', {path: settings.calibrations})}>abrir pasta</button></span></div>

                    <div className='List'>
                        {library.length == 0 && <div className='Empty'>Nenhuma calibração ainda.</div>}

                        {library.map(item => (
                            <div key={item.path} className={`ListItem ${chosen == item.path ? 'selected' : ''}`} onClick={() => setChosen(item.path)}>
                                <div className='ListName'><span>{item.info.id ?? 'MRU'} · {item.info.strategy}</span>{item.info.reference == 'debug' && <span className='Pill info'>debug</span>}</div>
                                <div className='ListMeta'>{item.info.created?.replace('T', ' ')} · roll {formatNumber(item.info.metrics?.roll?.rms_dyn, 3)}° · heave {formatNumber(item.info.metrics?.heave?.rmse, 3)} m</div>
                            </div>
                        ))}
                    </div>
                </div>

                {selected && (
                    <div className='Card CalibrationResult'>
                        <div className='CardTitle'>Resultado <span className='hint'>{formatDuration(Object.values(selected.info.timings ?? {}).reduce((sum, value) => sum + value, 0))} de processamento</span></div>

                        <div className='CardBody'>
                            {selected.info.reference == 'debug' && <div className='Notice info' style={{marginBottom: '.5rem'}}>Referência em debug: os números comparam o MRU com ele mesmo.</div>}

                            <table className='Table'>
                                <thead>
                                    <tr><th>RMS</th><th>parado</th><th>balanço</th><th>R²</th></tr>
                                </thead>
                                <tbody>
                                    {METRICS.filter(key => selected.info.metrics?.[key]).map(key => {
                                        const metric = selected.info.metrics[key]
                                        return <tr key={key}><td>{key}</td><td>{formatNumber(metric.rms_stat, 3)}</td><td>{formatNumber(metric.rms_dyn, 3)}</td><td>{formatNumber(metric.r2 * 100, 1)}%</td></tr>
                                    })}
                                </tbody>
                            </table>

                            <div className='Label' style={{marginTop: '.8rem'}}>Ruído parado (desvio padrão)</div>
                            <div className='Noise mono'>
                                {SENSORS.filter(key => selected.info.metrics?.[key]).map(key => <span key={key}>{key} {formatNumber(selected.info.metrics[key].std_stat, 4)}</span>)}
                            </div>
                        </div>

                        <div className='Actions'>
                            {selected.info.files?.certificate && <AsyncButton small text='Certificado' variant='light' onClick={() => call('open_path', {path: `${selected.path}/certificate.pdf`})}/>}
                            {selected.info.files?.certificate && <AsyncButton small text='Exportar PDF…' variant='light' onClick={() => exportPdf(selected)}/>}
                            <AsyncButton small text='Pasta' variant='ghost' onClick={() => call('open_path', {path: selected.path})}/>
                        </div>

                        <AsyncButton text='Enviar ao MRU em Produção' onClick={() => { setSelection(current => ({...current, calibration: selected.path})); navigate('/Production') }}/>
                    </div>
                )}
            </div>
        </Page>
    )
}
