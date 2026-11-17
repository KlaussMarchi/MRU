import { useState } from 'react'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { BAUDS } from '../../utils'
import AsyncButton from '../AsyncButton'
import Select from '../Select'
import './styles.css'

const TONES   = {synced: 'ok', streaming: 'ok', open: 'warn', silent: 'warn', searching: 'warn', syncing: 'warn', rebooting: 'warn', error: 'bad', off: ''}
const NAMES   = {synced: 'sincronizado', streaming: 'transmitindo', open: 'porta aberta', silent: 'sem dados', searching: 'procurando', syncing: 'sincronizando', rebooting: 'reiniciando', error: 'falhou', off: 'desconectado'}
const WORKING = ['searching', 'syncing', 'rebooting']
const TABLE   = 115200    // Table.ino: Serial.begin(115200)


// PORTA, BAUD E ESTADO DE UM PAPEL (MRU OU PLATAFORMA) NUMA LINHA: DESCONECTADO MOSTRA AS ESCOLHAS, CONECTADO SÓ O QUE ESTÁ ABERTO
export default function ConnectionBar({role = 'mru'}){
    const {links, ports, discovery, refreshPorts, connect, disconnect, sync} = useDevice()
    const {stats} = useLive()
    const [port, setPort] = useState('auto')
    const [baud, setBaud] = useState('auto')
    const link    = links[role]
    const active  = link.state != 'off' && link.state != 'error'
    const working = WORKING.includes(link.state)
    const usb     = ports.find(item => item.name == port)?.kind == 'usb'
    const rate    = stats[role]?.rate ?? 0
    const state   = role == 'table' && link.state == 'open' ? (rate > 0 ? 'streaming' : 'silent') : link.state
    const detail  = working ? discovery || link.message : link.state == 'error' ? link.message : active ? `${link.simulated ? `${link.label ?? 'simulado'}` : link.label ?? link.port}${link.kind == 'converter' ? ` · ${link.baud} bps` : ''} · ${Math.round(rate)} Hz` : ''

    async function handleConnect(){
        const chosen = port == 'auto' ? null : port
        const speed  = role == 'table' ? (chosen ? TABLE : null) : baud == 'auto' || usb ? null : Number(baud)
        await connect(role, {port: chosen, baud: speed})
    }

    return (
        <div className={`ConnectionBar ${active ? 'active' : ''}`}>
            <span className={`Pill ${TONES[state]}`} title={link.message}><span className={`Dot ${working ? 'pulse' : ''}`}/>{NAMES[state]}</span>
            {detail && <span className='ConnectionDetail' title={detail}>{detail}</span>}

            {!active && (
                <>
                    <Select className='BarSelect' compact value={port} onChange={setPort} onOpen={refreshPorts} title='Porta' options={[{value: 'auto', label: 'Porta automática'}, ...ports.map(item => ({value: item.name, label: item.label}))]}/>

                    {role == 'mru' && (
                        <Select className='BarSelect narrow' compact search={false} value={baud} disabled={usb} onChange={setBaud} title='Baud rate' options={[{value: 'auto', label: usb ? 'USB nativo' : 'Baud auto'}, ...BAUDS.map(value => ({value: String(value), label: String(value)}))]}/>
                    )}

                    <AsyncButton small text='Conectar' onClick={handleConnect} loading={working}/>
                </>
            )}

            {active && role == 'mru' && link.state != 'synced' && <AsyncButton small text='Sincronizar' variant='light' onClick={() => sync(role)} loading={working}/>}
            {active && <AsyncButton small text='Desconectar' variant='ghost' onClick={() => disconnect(role)} disabled={working}/>}
        </div>
    )
}
