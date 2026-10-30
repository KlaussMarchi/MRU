import { useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faPause, faPlay, faChevronUp, faChevronDown } from '@fortawesome/free-solid-svg-icons'
import Page from '../../components/Page'
import ConnectionBar from '../../components/ConnectionBar'
import LiveChart from '../../components/LiveChart'
import QuantityPicker from '../../components/QuantityPicker'
import Terminal from '../../components/Terminal'
import AsyncButton from '../../components/AsyncButton'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { getMotion, getInclination } from '../../utils/motion'
import { LAYOUTS, VARIABLES, formatNumber, formatBytes, formatDuration, getRawFactor, getStored, setStored, getQuantity, getColor } from '../../utils'
import './styles.css'

const READOUTS  = ['pitch', 'roll', 'yaw', 'heave', 'heave_rate', 'tmp']
const WINDOWS   = [{value: 10, label: '10 s'}, {value: 30, label: '30 s'}, {value: 60, label: '1 min'}, {value: 300, label: '5 min'}, {value: 1200, label: '20 min'}]
const SMOOTHING = [{value: 0, label: 'sem suavizar'}, {value: 0.2, label: 'suavizar 0,2 s'}, {value: 1, label: 'suavizar 1 s'}]


export default function MonitorPage(){
    const {links, getSeries, send, sync} = useDevice()
    const {stats, version} = useLive()
    const [view, setViewState] = useState(getStored('monitor-view', {chart: {quantity: 'attitude', keys: ['pitch', 'roll']}, seconds: 30, tau: 0}))
    const [paused, setPaused] = useState(false)
    const [collapsed, setCollapsed] = useState(false)    // O TERMINAL ABRE SEMPRE À MOSTRA; RECOLHER VALE ATÉ SAIR DA TELA
    const series   = getSeries('mru')
    const last     = series.last
    const current  = stats.mru
    const link     = links.mru
    const layout   = LAYOUTS[current?.layout]
    const quantity = getQuantity(view.chart.quantity)
    const motion   = useMemo(() => getMotion(series), [Math.floor(version / 4)])    // A JANELA DE 20 MIN UMA VEZ POR SEGUNDO
    const silent   = link.state == 'synced' && !current?.rate

    function setView(changes){
        const next = {...view, ...changes}
        setViewState(next)
        setStored('monitor-view', next)
    }

    function getValue(key){
        const value = last?.values[key]

        if(value == null)
            return null

        return last.layout == 'raw' ? value * getRawFactor(key, last.values) : value
    }

    const available = key => last && last.values[key] != null
    const lines     = view.chart.keys.map(key => ({key, label: VARIABLES[key].label, color: getColor(key)}))
    const pitch = getValue('pitch'), roll = getValue('roll')
    const start = <AsyncButton text='Iniciar stream' variant='accent' onClick={async () => { await send('$stream_start!'); await sync() }}/>

    return (
        <Page title='Monitor' subtitle={layout ? `${layout.label} · ${layout.detail}` : 'O MRU em tempo real, em qualquer modo e protocolo'} actions={<ConnectionBar role='mru'/>} className={`MonitorPage ${collapsed ? '' : 'docked'}`}>
            <div className='Card MonitorChart'>
                <div className='Toolbar'>
                    <QuantityPicker value={view.chart} onChange={chart => setView({chart})}/>
                    <div className='Spacer'/>

                    <div className='Segmented'>
                        {WINDOWS.map(option => <span key={option.value} className={view.seconds == option.value ? 'on' : ''} onClick={() => setView({seconds: option.value})}>{option.label}</span>)}
                    </div>

                    <select className='Select Compact' value={view.tau} onChange={event => setView({tau: Number(event.target.value)})} title='Suavização só na tela'>
                        {SMOOTHING.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>

                    <button className={`IconButton ${paused ? 'on' : ''}`} onClick={() => setPaused(!paused)} title={paused ? 'Continuar' : 'Pausar'}>
                        <FontAwesomeIcon icon={paused ? faPlay : faPause}/>
                    </button>
                </div>

                <LiveChart lines={lines} unit={quantity.unit} digits={quantity.digits} seconds={view.seconds} tau={view.tau} paused={paused} empty={silent ? 'o MRU está sincronizado, mas não está transmitindo' : link.state == 'synced' || link.state == 'open' ? 'aguardando dados do MRU' : 'conecte o MRU no alto da tela'} action={silent ? start : null}/>
            </div>

            <div className='MonitorSide'>
                <div className='Card'>
                    <div className='CardTitle'>Leituras {layout && <span className={`Pill ${layout.tone}`}>{layout.label}</span>}<span className='hint'>faixa em {WINDOWS.find(option => option.value == view.seconds)?.label}</span></div>

                    <div className='Readouts'>
                        {READOUTS.map(key => {
                            const range = available(key) ? series.getStats(key, view.seconds) : null
                            const raw   = last?.layout == 'raw' ? getRawFactor(key, last.values) : 1
                            return (
                                <div key={key} className={`Readout ${available(key) ? '' : 'empty'}`}>
                                    <div className='ReadoutLabel'>{VARIABLES[key].label}</div>
                                    <div className='ReadoutValue'>{formatNumber(getValue(key), key.startsWith('heave') ? 3 : 2)}<span>{VARIABLES[key].unit}</span></div>
                                    <div className='ReadoutRange'>{range ? `${formatNumber(range.min * raw, 2)} a ${formatNumber(range.max * raw, 2)}` : last ? 'sem este dado' : '—'}</div>
                                </div>
                            )
                        })}

                        <div className={`Readout Wide ${pitch == null || roll == null ? 'empty' : ''}`}>
                            <div className='ReadoutLabel'>Inclinação · arccos(cos θ · cos φ)</div>
                            <div className='ReadoutValue'>{pitch == null || roll == null ? '—' : formatNumber(getInclination(pitch, roll), 2)}<span>°</span></div>
                        </div>
                    </div>
                </div>

                <div className='Card'>
                    <div className='CardTitle'>Stream <span className='hint'>{link.firmware ? `firmware ${link.firmware}` : ''}</span></div>

                    <div className='Stats'>
                        <div><span>Formato</span><b>{current?.format?.toUpperCase() ?? '—'}</b></div>
                        <div><span>Taxa</span><b>{current ? `${Math.round(current.rate)} Hz` : '—'}</b></div>
                        <div><span>Recebido</span><b>{current ? formatBytes(current.bytes) : '—'}</b></div>
                        <div><span>Pacotes</span><b>{current?.count?.toLocaleString('pt-BR') ?? '—'}</b></div>
                        <div><span>Perdidos</span><b className={current?.lost ? 'warn' : ''}>{current?.lost?.toLocaleString('pt-BR') ?? '—'}</b></div>
                        <div><span>Ruins</span><b className={current?.bad ? 'warn' : ''}>{current?.bad?.toLocaleString('pt-BR') ?? '—'}</b></div>
                    </div>

                    <div className='Muted Chain' title={link.status?.processing}>{link.status?.processing ?? (link.firmware ? 'cadeia: pergunte com $calibrate!' : 'sem MRU sincronizado')}</div>
                </div>

                <div className='Card'>
                    <div className='CardTitle'>Movimento <span className='hint'>{motion ? `últimos ${formatDuration(Math.min(motion.span, 1200))}` : 'janela de 20 min'}</span></div>

                    <div className='Facts'>
                        <span>Pitch máx. ↑ / ↓</span><b>{formatNumber(motion?.up, 1)}° / {formatNumber(motion?.down, 1)}°</b>
                        <span>Roll máx. BB / BE</span><b>{formatNumber(motion?.port, 1)}° / {formatNumber(motion?.starboard, 1)}°</b>
                        <span>Inclinação máx.</span><b>{formatNumber(motion?.inclination, 1)}°</b>
                        <span>Arfagem (Arf)</span><b>{formatNumber(motion?.heave, 2)} m</b>
                        <span>Vel. arfagem (VArf)</span><b>{formatNumber(motion?.velocity, 2)} m/s</b>
                        <span>SHR (SVArf)</span><b>{formatNumber(motion?.shr, 2)} m/s</b>
                    </div>
                </div>
            </div>

            <div className='Card MonitorTerminal'>
                <button className='DockToggle' onClick={() => setCollapsed(!collapsed)}>
                    Terminal serial <span className='hint'>{collapsed ? 'comandos, respostas e o stream' : 'recolher'}</span>
                    <FontAwesomeIcon icon={collapsed ? faChevronUp : faChevronDown} className='DockIcon'/>
                </button>

                {!collapsed && <Terminal role='mru'/>}
            </div>
        </Page>
    )
}
