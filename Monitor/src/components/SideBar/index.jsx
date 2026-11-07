import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHouse, faChartLine, faCircleDot, faFlask, faIndustry, faMicrochip, faGear, faExpand, faCompress, faHelicopter } from '@fortawesome/free-solid-svg-icons'
import { useDevice, useIssues, useLive } from '../../contexts/DeviceContext'
import Logo from '../Logo'
import { APP_VERSION } from '../../utils'
import './styles.css'

const GROUPS = [
    {label: 'Fluxo', items: [
        {path: '/', icon: faHouse, label: 'Início'},
        {path: '/Monitor', icon: faChartLine, label: 'Monitor'},
        {path: '/Acquisition', icon: faCircleDot, label: 'Aquisição'},
        {path: '/Calibration', icon: faFlask, label: 'Calibração'},
        {path: '/Production', icon: faIndustry, label: 'Produção'}
    ]},
    {label: 'Ferramentas', items: [
        {path: '/Device', icon: faMicrochip, label: 'Dispositivo'},
        {path: '/HMS', icon: faHelicopter, label: 'HMS'},
        {path: '/Settings', icon: faGear, label: 'Ajustes'}
    ]}
]

const STATES = {
    off: {tone: '', label: 'desconectado'},
    searching: {tone: 'warn', label: 'procurando'},
    open: {tone: 'warn', label: 'porta aberta'},
    syncing: {tone: 'warn', label: 'sincronizando'},
    rebooting: {tone: 'warn', label: 'reiniciando'},
    synced: {tone: 'ok', label: 'sincronizado'},
    error: {tone: 'bad', label: 'sem resposta'}
}


export default function SideBar(){
    const {links, simulation} = useDevice()
    const {stats, recording} = useLive()
    const issues = useIssues()
    const [full, setFull] = useState(false)

    async function toggleFullscreen(){
        const window = getCurrentWindow()
        const next   = !(await window.isFullscreen())
        await window.setFullscreen(next)
        setFull(next)
    }

    useEffect(() => {
        const handleKey = event => event.key == 'F11' && (event.preventDefault(), toggleFullscreen())
        document.addEventListener('keydown', handleKey)
        return () => document.removeEventListener('keydown', handleKey)
    }, [])

    const devices = [['MRU', links.mru, stats.mru], ['Plataforma', links.table, stats.table]]

    return (
        <aside className='SideBarContainer'>
            <div className='Brand'>
                <Logo size={34}/>
                <div className='Name'>MRU Monitor<span>{simulation.enabled ? 'simulação ligada' : 'Kernel-120'}</span></div>
            </div>

            <nav className='Items'>
                {GROUPS.map(group => (
                    <div key={group.label} className='Group'>
                        <div className='GroupLabel'>{group.label}</div>

                        {group.items.map(item => (
                            <NavLink key={item.path} to={item.path} end title={item.label} className={({isActive}) => `Item ${isActive ? 'active' : ''}`}>
                                <FontAwesomeIcon icon={item.icon} className='Icon'/>
                                <span>{item.label}</span>
                            </NavLink>
                        ))}
                    </div>
                ))}
            </nav>

            <div className='Bottom'>
                {recording && (
                    <NavLink to='/Acquisition' className='Recording' title='Gravando'>
                        <span className='Dot pulse'/><span>gravando</span>
                    </NavLink>
                )}

                <div className='Links'>
                    {devices.map(([name, link, stat]) => {
                        const state = name == 'Plataforma' && link.state == 'open' ? {tone: stat?.rate ? 'ok' : 'warn', label: stat?.rate ? 'transmitindo' : 'sem dados'} : STATES[link.state] ?? STATES.off
                        const issue = name == 'MRU' && issues[0]?.level != 'info' ? issues[0] : null
                        return (
                            <div key={name} className={`Link ${issue ? (issue.level == 'error' ? 'bad' : 'warn') : state.tone}`} title={issue?.title ?? (link.message || state.label)}>
                                <span className={`Dot ${['searching', 'syncing', 'rebooting'].includes(link.state) ? 'pulse' : ''}`}/>
                                <div className='LinkText'>
                                    <b>{name}</b>
                                    <span>{link.port ? `${link.simulated ? 'simulado' : link.port.split(/[\\/]/).pop()} · ${Math.round(stat?.rate ?? 0)} Hz` : state.label}</span>
                                </div>
                            </div>
                        )
                    })}
                </div>

                <button className='Item Fullscreen' onClick={toggleFullscreen} title='Tela cheia (F11)'>
                    <FontAwesomeIcon icon={full ? faCompress : faExpand} className='Icon'/>
                    <span>{full ? 'Sair da tela cheia' : 'Tela cheia'}</span>
                </button>

                <div className='Version'>{APP_VERSION}</div>
            </div>
        </aside>
    )
}
