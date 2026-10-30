import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCircleDot, faFlask, faIndustry, faChartLine, faMicrochip, faHelicopter, faArrowRight, faChevronRight } from '@fortawesome/free-solid-svg-icons'
import Page from '../../components/Page'
import Horizon from '../../components/Horizon'
import AsyncButton from '../../components/AsyncButton'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, formatDuration, formatNumber, getRawFactor, LAYOUTS, MODELS } from '../../utils'
import './styles.css'

const FLOW = [
    {path: '/Acquisition', icon: faCircleDot, title: 'Aquisição', text: 'Grava o MRU contra a plataforma de referência no modo de calibração.'},
    {path: '/Calibration', icon: faFlask, title: 'Calibração', text: 'Filtros, correção, atitude, heave e braço, com certificado em PDF.'},
    {path: '/Production', icon: faIndustry, title: 'Produção', text: 'Grava a calibração pela serial e deixa o MRU transmitindo ao ligar.'}
]

const TOOLS = [
    {path: '/Monitor', icon: faChartLine, title: 'Monitor', text: 'Gráficos e leituras ao vivo em qualquer modo'},
    {path: '/Device', icon: faMicrochip, title: 'Dispositivo', text: 'Configuração, align do Kernel e terminal'},
    {path: '/HMS', icon: faHelicopter, title: 'HMS', text: 'Painel de helideque com os limites da NORMAM-223'}
]

const GUIDES = [
    {title: 'Calibrar um MRU', steps: [
        'Monte o MRU na plataforma na posição em que vai operar e grave o align em Dispositivo; desligue e ligue o MRU.',
        'Em Aquisição, escolha "Para calibração", aplique e espere sincronizar. Conecte a plataforma (Table.ino, 115200 bps).',
        'Inicie a gravação: a plataforma fica parada 20 s e depois alterna pitch, roll e repouso. Grave pelo menos 320 s.',
        'Pare, salve a sessão e clique em "Calibrar esta sessão". Escolha a estratégia e rode o pipeline.',
        'Confira as métricas e o certificado e envie a calibração ao MRU em Produção.'
    ]},
    {title: 'Preparar para produção', steps: [
        'Sincronize o MRU: o ACK libera os botões.',
        'Escolha a calibração, ou nenhuma para sair na escala do Kernel.',
        'Escolha protocolo (NMEA por padrão), frequência, porta ao ligar e baud; a tela mostra quanto do link o stream ocupa.',
        'Clique em preparar: o app envia a calibração, confere o CRC, configura num reinício só e verifica pelo $status!.',
        'Desligue e ligue o MRU: ao ligar ele já transmite pela porta escolhida.'
    ]},
    {title: 'Sem MRU por perto', steps: [
        'Em Ajustes, ligue "Simular MRU" e escolha o movimento: sobre a plataforma, navio em ondas ou parado.',
        'As portas SIM0 (MRU) e SIM1 (plataforma) entram nas listas e na busca automática; o MRU simulado responde como o firmware v1.0.8.',
        'Em Aquisição, aplique "Para calibração", conecte a plataforma simulada e grave 320 s.',
        'Salve, calibre e envie o pacote ao MRU simulado em Produção: o fluxo é o mesmo do aparelho de verdade.'
    ]},
    {title: 'Eixos e unidades', steps: [
        'SCALE mantém os eixos do Kernel: X boreste, Y proa, Z para cima.',
        'CALIBRADO entrega os eixos do navio: x proa, y boreste, z para baixo.',
        'Heave e velocidade do heave são positivos para baixo, no ponto do braço de alavanca (LEVER_POINT).',
        'RAW são os inteiros do Kernel; o Monitor os converte só para mostrar.'
    ]},
    {title: 'Quando algo não responde', steps: [
        'Nenhuma porta: confira o cabo e a permissão (grupo dialout no Linux).',
        'Porta abre mas sem ACK: o baud do RS232/RS422 pode ser outro; deixe o baud automático.',
        'Linhas ruins subindo: baud errado ou ruído no cabo; o contador fica no painel Stream do Monitor.',
        'Pitch e roll trocados: confira a marca de boreste e o align do Kernel.'
    ]}
]


export default function HomePage(){
    const navigate = useNavigate()
    const {links, simulation, getSeries, connect, send, sync} = useDevice()
    const {stats} = useLive()
    const {settings, python} = useGlobalContext()
    const [library, setLibrary] = useState({sessions: [], calibrations: []})
    const [guide, setGuide]     = useState(0)
    const link    = links.mru
    const current = stats.mru
    const last    = getSeries('mru').last
    const synced  = link.state == 'synced'
    const working = ['searching', 'syncing', 'rebooting'].includes(link.state)

    useEffect(() => {
        if(!settings.sessions)
            return

        Promise.all([call('list_sessions', {folder: settings.sessions}), call('list_calibrations', {folder: settings.calibrations})]).then(([sessions, calibrations]) => setLibrary({sessions: sessions.filter(item => item.info?.calibration), calibrations: calibrations.filter(item => item.info)}))
    }, [settings.sessions, settings.calibrations])

    function getValue(key){
        const value = last?.values[key]
        return value == null ? null : last.layout == 'raw' ? value * getRawFactor(key, last.values) : value
    }

    const pythonOk = python && !python.error && !python.missing?.length
    const session  = library.sessions[0]
    const bundle   = library.calibrations[0]
    const layout   = LAYOUTS[current?.layout]
    const flowing  = (current?.rate ?? 0) > 0

    const facts = [
        {label: 'Simulação', value: simulation.enabled ? 'ligada · SIM0 e SIM1' : 'desligada', tone: simulation.enabled ? 'info' : ''},
        {label: 'Python do pipeline', value: !python ? 'verificando' : pythonOk ? `Python ${python.version} completo` : 'incompleto: veja Ajustes', tone: !python ? '' : pythonOk ? 'ok' : 'bad'},
        {label: 'Sessões de calibração', value: `${library.sessions.length} gravada${library.sessions.length == 1 ? '' : 's'}`, tone: ''},
        {label: 'Calibrações', value: `${library.calibrations.length} pacote${library.calibrations.length == 1 ? '' : 's'}`, tone: ''},
        {label: 'Firmware', value: link.firmware ? `${link.firmware}${link.status ? '' : ' (anterior a v1.0.8)'}` : '—', tone: link.firmware && !link.status ? 'warn' : ''}
    ]

    const context = [
        session ? `última: ${session.name} · ${formatDuration(session.info.duration)}` : 'nenhuma sessão gravada',
        bundle ? `última: ${bundle.info.id ?? 'MRU'} · ${bundle.info.strategy}` : 'nenhuma calibração',
        link.status ? `no MRU: ${link.status.calibration == 'flash' ? 'gravada na flash' : 'compilada'} · ${MODELS[link.status.model] ?? '—'}` : 'sincronize o MRU para ver'
    ]

    return (
        <Page title='MRU Monitor' subtitle='Monitoramento, aquisição, calibração e produção do MRU com Kernel-120' className='HomePage'>
            <div className='Card HomeLive'>
                <Horizon pitch={getValue('pitch')} roll={getValue('roll')} size={170}/>

                <div className='HomeLiveBody'>
                    <div className='HomeLiveState'>
                        <span className={`Pill ${synced ? 'ok' : working ? 'warn' : link.state == 'error' ? 'bad' : ''}`}><span className={`Dot ${working ? 'pulse' : ''}`}/>{synced ? 'MRU sincronizado' : working ? 'procurando o MRU' : link.state == 'error' ? 'nenhum MRU respondeu' : link.state == 'open' ? 'porta aberta, sem ACK' : 'MRU desconectado'}</span>
                        {link.port && <span className='Muted'>{link.label ?? link.port} · {link.status?.id ?? ''} {flowing ? `· ${layout?.label ?? ''} ${current.format?.toUpperCase()} a ${Math.round(current.rate)} Hz` : '· sem stream'}</span>}
                    </div>

                    <div className='HomeValues'>
                        {[['Pitch', 'pitch', '°', 2], ['Roll', 'roll', '°', 2], ['Heave', 'heave', 'm', 3], ['Yaw', 'yaw', '°', 1]].map(([label, key, unit, digits]) => (
                            <div key={key} className={getValue(key) == null ? 'empty' : ''}>
                                <span>{label}</span>
                                <b>{formatNumber(getValue(key), digits)}<small>{unit}</small></b>
                            </div>
                        ))}
                    </div>

                    <div className='Row'>
                        {link.state == 'off' || link.state == 'error'
                            ? <AsyncButton text='Conectar automaticamente' onClick={() => connect('mru')} loading={working}/>
                            : <AsyncButton text='Abrir o Monitor' icon={faArrowRight} onClick={() => navigate('/Monitor')}/>}
                        {synced && !flowing && <AsyncButton text='Iniciar stream' variant='light' onClick={async () => { await send('$stream_start!'); await sync() }}/>}
                        {!synced && !simulation.enabled && <AsyncButton text='Simular um MRU' variant='light' onClick={() => navigate('/Settings')}/>}
                    </div>
                </div>
            </div>

            <div className='Card HomeFacts'>
                <div className='CardTitle'>Ambiente</div>

                <div className='HomeFactList'>
                    {facts.map(fact => (
                        <div key={fact.label}>
                            <span>{fact.label}</span>
                            <b className={fact.tone}>{fact.value}</b>
                        </div>
                    ))}
                </div>
            </div>

            <div className='HomeFlow'>
                {FLOW.map((step, index) => (
                    <div key={step.path} className='HomeStep' onClick={() => navigate(step.path)}>
                        <div className='HomeStepTop'>
                            <span className='HomeStepIcon'><FontAwesomeIcon icon={step.icon}/></span>
                            <span className='HomeStepNumber'>passo {index + 1}</span>
                            <FontAwesomeIcon icon={faChevronRight} className='HomeStepArrow'/>
                        </div>
                        <div className='HomeStepTitle'>{step.title}</div>
                        <div className='HomeStepText'>{step.text}</div>
                        <div className='HomeStepContext'>{context[index]}</div>
                    </div>
                ))}
            </div>

            <div className='Card HomeGuides'>
                <div className='GuideTabs'>
                    <div className='Label'>Guias</div>
                    {GUIDES.map((item, index) => <span key={item.title} className={guide == index ? 'on' : ''} onClick={() => setGuide(index)}>{item.title}</span>)}
                </div>

                <ol className='GuideSteps CardBody'>
                    {GUIDES[guide].steps.map((step, index) => <li key={step}><span>{index + 1}</span>{step}</li>)}
                </ol>
            </div>

            <div className='Card HomeTools'>
                <div className='CardTitle'>Ferramentas</div>

                {TOOLS.map(tool => (
                    <div key={tool.path} className='HomeTool' onClick={() => navigate(tool.path)}>
                        <span className='HomeStepIcon'><FontAwesomeIcon icon={tool.icon}/></span>
                        <div className='Grow'>
                            <div className='HomeToolTitle'>{tool.title}</div>
                            <div className='HomeToolText'>{tool.text}</div>
                        </div>
                        <FontAwesomeIcon icon={faChevronRight} className='HomeStepArrow'/>
                    </div>
                ))}
            </div>
        </Page>
    )
}
