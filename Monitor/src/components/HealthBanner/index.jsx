import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AsyncButton from '../AsyncButton'
import Dialog from '../Dialog'
import { useDevice, useIssues } from '../../contexts/DeviceContext'
import './styles.css'

const ACTIONS = {search: 'Procurar de novo', sync: 'Tentar de novo', restart: 'Reiniciar MRU', stream: 'Iniciar stream', firmware: 'Atualizar firmware'}


// O PROBLEMA MAIS GRAVE NUMA LINHA, EM TODAS AS TELAS, COM O QUE DÁ PARA FAZER; O RESTO FICA NOS DETALHES
export default function HealthBanner(){
    const issues   = useIssues()
    const navigate = useNavigate()
    const {connect, disconnect, sync, send, reboot, links, health} = useDevice()
    const [open, setOpen] = useState(false)
    const top = issues[0]

    if(!top)
        return null

    async function act(action){
        const link = links.mru

        if(action == 'firmware'){
            setOpen(false)
            return navigate('/Device?tab=firmware')
        }

        if(action == 'search'){
            await disconnect('mru')
            return connect('mru')
        }

        if(action == 'sync')
            return sync()

        if(action == 'stream'){
            await send('$stream_start!')
            return sync()
        }

        await send('MICRS')
        return reboot(link.settings ?? {})
    }

    return (
        <>
            <div className={`HealthBanner ${top.level}`}>
                <span className='HealthMark'>{top.level == 'info' ? 'i' : '!'}</span>
                <b title={top.title}>{top.title}</b>
                <span className='HealthDetail' title={top.detail}>{top.detail}</span>
                {top.action && <AsyncButton small variant='light' text={ACTIONS[top.action]} onClick={() => act(top.action)}/>}
                <button className='LinkButton' onClick={() => setOpen(true)}>{issues.length > 1 ? `mais ${issues.length - 1}` : 'detalhes'}</button>
            </div>

            {open && (
                <Dialog title='Diagnóstico do MRU' onClose={() => setOpen(false)} actions={<AsyncButton small text='Fechar' onClick={() => setOpen(false)}/>}>
                    <div className='HealthList'>
                        {issues.map(issue => (
                            <div key={issue.key} className={`HealthItem ${issue.level}`}>
                                <b>{issue.title}</b>
                                <div>{issue.detail}</div>
                                {issue.action && <div className='HealthAction'><AsyncButton small variant='light' text={ACTIONS[issue.action]} onClick={() => act(issue.action)}/></div>}
                            </div>
                        ))}
                    </div>

                    {health.log.length > 0 && (
                        <>
                            <div className='Label' style={{marginTop: '.8rem'}}>Últimos eventos do MRU</div>
                            <div className='HealthLog mono Scroll'>{[...health.log].reverse().map((entry, index) => <div key={index} className={entry.l}><span>{entry.t.toFixed(1)} s</span>{entry.m}</div>)}</div>
                        </>
                    )}
                </Dialog>
            )}
        </>
    )
}
