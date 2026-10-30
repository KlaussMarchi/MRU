import { useState } from 'react'
import { open } from '@tauri-apps/plugin-dialog'
import Page from '../../components/Page'
import AsyncButton from '../../components/AsyncButton'
import Overlay from '../../components/Overlay'
import { useConfirm } from '../../components/Dialog'
import { useDevice } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, APP_VERSION } from '../../utils'
import './styles.css'

const FOLDERS = [
    {key: 'sessions', label: 'Sessões gravadas', hint: 'cada gravação vira uma pasta com target.csv, data.csv e info.json'},
    {key: 'calibrations', label: 'Calibrações', hint: 'cada calibração vira um pacote com certificado, figuras, config.h e calibration.json'}
]

const SCENARIOS = [
    {value: 'table', label: 'Sobre a plataforma', detail: 'O ciclo do Table.ino em repetição: 100 s de pitch, 100 s de roll e 100 s de repouso a 15° e 0,3 Hz, com o Kernel 0,3 m acima dos eixos. Ao gravar para calibração, a plataforma vai a zero, fica 20 s parada e recomeça o ciclo no mesmo instante do MRU; ao parar, volta a ciclar.'},
    {value: 'ship', label: 'Navio em ondas', detail: 'Roll de 6°, pitch de 2,5° e heave de 0,8 m em mar irregular, com o MRU a 12 m do centro de giro. Nunca fica parado: serve para Monitor e HMS.'},
    {value: 'still', label: 'Parado', detail: 'O MRU na bancada, só com ruído, viés e deriva térmica do Kernel.'}
]


export default function SettingsPage(){
    const {settings, setSettings, defaults, python, jobs, installPython, cancelJob, clearJob} = useGlobalContext()
    const {simulation, setSimulation} = useDevice()
    const [error, setError] = useState('')
    const [cleared, setCleared] = useState('')
    const [confirmation, ask] = useConfirm()
    const job      = jobs.environment
    const tone     = !python ? '' : python.error || python.missing?.length ? 'bad' : 'ok'
    const managed  = settings.python == defaults?.managed
    const scenario = SCENARIOS.find(item => item.value == simulation.scenario) ?? SCENARIOS[0]

    async function choose(key){
        const folder = await open({directory: true, defaultPath: settings[key]})

        if(folder)
            setSettings({[key]: folder})
    }

    async function install(){
        setError('')
        await installPython().catch(reason => setError(String(reason)))
    }

    async function resetSimulator(){
        if(await ask('Restaurar o MRU simulado', 'Configurações, calibração gravada e align do MRU simulado voltam ao padrão de fábrica.', 'Restaurar'))
            await call('simulation_reset')
    }

    async function clearAll(){
        const text = <>Todas as sessões gravadas em <code>{settings.sessions}</code> e todas as calibrações em <code>{settings.calibrations}</code> serão apagadas, com certificados e config.h. <b>Não dá para desfazer.</b></>

        if(!await ask('Apagar sessões e calibrações', text, 'Apagar tudo'))
            return

        setCleared('')

        try {
            const counts = await Promise.all(FOLDERS.map(folder => call('clear_folder', {path: settings[folder.key]})))
            setCleared(`${counts[0]} itens de sessões e ${counts[1]} de calibrações apagados.`)
        }
        catch(failure) {
            setCleared(`Não apagou tudo: ${failure}`)
        }
    }

    return (
        <Page title='Ajustes' subtitle='Simulação, Python do pipeline e pastas de sessões e calibrações' className='SettingsPage'>
            {job?.status == 'running' && (
                <Overlay title='Instalando o ambiente Python' stage={job.stage} message={job.message} progress={job.steps ? job.step / job.steps : null} started={job.started} log={job.log}>
                    <AsyncButton text='Cancelar' variant='light' onClick={() => cancelJob('environment')}/>
                </Overlay>
            )}

            <div className='Column'>
                <div className='Card'>
                    <div className='CardTitle'>Simulação <span className={`Pill ${simulation.enabled ? 'ok' : ''}`}>{simulation.enabled ? 'ligada' : 'desligada'}</span></div>

                    <label className='Switch'>
                        <input type='checkbox' checked={simulation.enabled} onChange={event => setSimulation({enabled: event.target.checked})}/>
                        Simular MRU
                    </label>

                    <div className='Muted' style={{margin: '.5rem 0 .8rem 0'}}>
                        Um MRU e uma plataforma fictícios nas portas <b>SIM0</b> e <b>SIM1</b>, nas listas e na busca automática. O MRU já sai transmitindo a <b>100 Hz em LIST a 115200 bps</b>, emula o firmware v1.0.8 e entrega o Kernel com o ruído, o viés e a deriva do ensaio real; baud errado vira lixo. A plataforma transmite a 100 Hz, como o Table.ino.
                    </div>

                    <div className='Label'>Movimento</div>
                    <div className='Segmented'>
                        {SCENARIOS.map(item => <span key={item.value} className={simulation.scenario == item.value ? 'on' : ''} onClick={() => setSimulation({scenario: item.value})}>{item.label}</span>)}
                    </div>

                    <div className='Muted' style={{marginTop: '.5rem'}}>{scenario.detail}</div>

                    <div className='Actions'>
                        <AsyncButton small variant='light' text='Restaurar o MRU simulado' onClick={resetSimulator} disabled={!simulation.enabled}/>
                    </div>
                </div>

                <div className='Card'>
                    <div className='CardTitle'>Pastas</div>

                    <div className='Column'>
                        {FOLDERS.map(folder => (
                            <div key={folder.key} className='Field'>
                                <span className='Label'>{folder.label}</span>

                                <div className='Row'>
                                    <input className='Input mono Grow' value={settings[folder.key] ?? ''} onChange={event => setSettings({[folder.key]: event.target.value})}/>
                                    <AsyncButton text='Escolher…' variant='light' onClick={() => choose(folder.key)}/>
                                    <AsyncButton text='Abrir' variant='ghost' onClick={() => call('open_path', {path: settings[folder.key]})}/>
                                </div>

                                <span className='Muted FolderHint'>{folder.hint}</span>
                            </div>
                        ))}
                    </div>

                    {cleared && <div className={`Notice ${cleared.startsWith('Não') ? 'bad' : 'ok'}`} style={{marginTop: '.6rem'}}>{cleared}</div>}

                    <div className='Actions'>
                        <AsyncButton small text='Apagar sessões e calibrações' variant='red' onClick={clearAll}/>
                        <div className='Spacer'/>
                        <AsyncButton small text='Voltar ao padrão' variant='ghost' onClick={() => setSettings({sessions: defaults.sessions, calibrations: defaults.calibrations, python: defaults.pythons[0]})}/>
                    </div>
                </div>
            </div>

            <div className='Column'>
                {(error || (job && job.status != 'running')) && (
                    <div className={`Notice ${job?.status == 'done' && !error ? 'ok' : 'bad'}`}>
                        {error ? `Não deu para iniciar a instalação: ${error}` : job.status == 'done' ? `Ambiente instalado: ${job.result?.python}` : job.status == 'cancelled' ? 'Instalação cancelada.' : `A instalação parou: ${job.error}`}
                        <button className='LinkButton' style={{marginLeft: '.6rem'}} onClick={() => { setError(''); clearJob('environment') }}>ok</button>
                    </div>
                )}

                <div className='Card'>
                    <div className='CardTitle'>Python do pipeline <span className={`Pill ${tone}`}>{!python ? 'verificando' : tone == 'ok' ? `Python ${python.version}` : 'incompleto'}</span></div>

                    <label className='Field'>
                        <span className='Label'>Executável</span>
                        <input className='Input mono' list='pythons' value={settings.python ?? ''} onChange={event => setSettings({python: event.target.value})}/>
                        <datalist id='pythons'>{defaults?.pythons.map(item => <option key={item} value={item}/>)}</datalist>
                    </label>

                    <div className='Muted' style={{marginTop: '.5rem'}}>
                        {python?.error && <>Não roda: {python.error}</>}
                        {python?.missing?.length > 0 && <>Faltam os módulos {python.missing.join(', ')}: use "Instalar ambiente" ou rode <code>{settings.python} -m pip install -r {defaults?.base}/Pipeline/requirements.txt</code></>}
                        {tone == 'ok' && <>{python.executable}: numpy, pandas, scipy, scikit-learn, matplotlib, reportlab, tqdm, multiprocess e numba presentes.</>}
                    </div>

                    <div className='Row' style={{marginTop: '.8rem', flexWrap: 'nowrap', alignItems: 'center'}}>
                        <span className='Muted Grow'>O app baixa o uv, um Python 3.12 próprio e os módulos do pipeline para <code>{defaults?.environment}</code>, sem mexer no Python da máquina. Precisa de internet.</span>
                        <AsyncButton small text={managed ? 'Reinstalar ambiente' : 'Instalar ambiente'} variant='light' onClick={install}/>
                    </div>
                </div>

                <div className='Card'>
                    <div className='CardTitle'>Sobre</div>

                    <div className='Facts wide'>
                        <span>MRU Monitor</span><b>{APP_VERSION}</b>
                        <span>Firmware compatível</span><b className='small'>v1.0.8 ou mais novo para $status!, CS: e calibração pela serial; o resto funciona com versões anteriores</b>
                        <span>Pipeline</span><b className='small'>Pipeline/: os algoritmos dos notebooks de Calibration/, conferidos contra eles</b>
                        <span>Scripts e dados</span><b className='small mono'>{defaults?.base}</b>
                    </div>
                </div>
            </div>

            {confirmation}
        </Page>
    )
}
