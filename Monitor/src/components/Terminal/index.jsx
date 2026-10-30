import { useEffect, useRef, useState } from 'react'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import './styles.css'

const KINDS = [
    {value: 'rx', label: 'Respostas'},
    {value: 'tx', label: 'Enviados'},
    {value: 'stream', label: 'Stream'},
    {value: 'info', label: 'Sistema'}
]

const QUICK   = ['$ackoneledge!', '$status!', '$settings!', '$check_sensor!', '$firmware!', '$calibrate!', '$stream_start!', '$stream_stop!', '$calibration_check!']
const ENDINGS = [{value: '\r\n', label: 'CR+LF'}, {value: '\n', label: 'LF'}, {value: '', label: 'nenhum'}]
const VISIBLE = 400    // LINHAS NO DOM: O RESTO FICA NO BUFFER
const MARKS   = {tx: '→', rx: '←', stream: '≈'}


function format(host){
    const date = new Date(host * 1000)
    return `${date.toLocaleTimeString('pt-BR')}.${String(date.getMilliseconds()).padStart(3, '0')}`
}


function getLine(line){
    const row = document.createElement('div')
    row.className = `TerminalLine ${line.kind}`

    for(const [name, text] of [['TerminalTime', format(line.host)], ['TerminalKind', MARKS[line.kind] ?? '•'], ['TerminalText', line.text]]){
        const span = document.createElement('span')
        span.className   = name
        span.textContent = text
        row.append(span)
    }

    return row
}


// O TERMINAL DO APARELHO NO ESPAÇO DO PAI: A CAIXA DE LINHAS ENCOLHE COM A JANELA, ENTRADA E ATALHOS FICAM SEMPRE À MOSTRA
export default function Terminal({role = 'mru', hint}){
    const {getTexts, clearTexts, send} = useDevice()
    const {stats} = useLive()
    const {settings, setSettings} = useGlobalContext()
    const [message, setMessage] = useState('')
    const [kinds, setKinds]     = useState(['rx', 'tx', 'stream', 'info', 'error'])
    const [history, setHistory] = useState([])
    const [cursor, setCursor]   = useState(-1)
    const [error, setError]     = useState('')
    const box    = useRef()
    const bottom = useRef(true)
    const connected = Boolean(stats[role])
    const drawn     = useRef(0)

    // AS LINHAS NOVAS ENTRAM NO DOM A CADA QUADRO, SEM PASSAR PELO REACT: O STREAM A 200 Hz ROLA LISO
    useEffect(() => {
        const element = box.current
        let frame
        element.replaceChildren()
        drawn.current = 0

        function draw(){
            frame = requestAnimationFrame(draw)
            const all    = getTexts(role)
            const newest = all.length ? all[all.length - 1].seq : 0

            if(newest == drawn.current)
                return

            if(newest < drawn.current){
                element.replaceChildren()
                drawn.current = 0
            }

            const fresh    = all.filter(line => line.seq > drawn.current && kinds.includes(line.kind)).slice(-VISIBLE)
            const fragment = document.createDocumentFragment()
            fresh.forEach(line => fragment.append(getLine(line)))
            element.append(fragment)

            while(element.childElementCount > VISIBLE)
                element.firstElementChild.remove()

            drawn.current = newest

            if(bottom.current)
                element.scrollTop = element.scrollHeight
        }

        frame = requestAnimationFrame(draw)
        return () => cancelAnimationFrame(frame)
    }, [role, kinds])

    function toggle(kind){
        const group = kind == 'info' ? ['info', 'error'] : [kind]
        setKinds(current => current.includes(kind) ? current.filter(item => !group.includes(item)) : [...current, ...group])
    }

    async function handleSend(text = message){
        if(!text.trim())
            return

        setError('')

        try {
            await send(text.trim(), role, settings.ending ?? '\r\n')
            setHistory(current => [text.trim(), ...current.filter(item => item != text.trim())].slice(0, 50))
            setMessage('')
            setCursor(-1)
            bottom.current = true
        }
        catch(failure) {
            setError(String(failure))
        }
    }

    function handleKey(event){
        if(event.key == 'Enter')
            return handleSend()

        if(event.key != 'ArrowUp' && event.key != 'ArrowDown')
            return

        event.preventDefault()
        const next = Math.max(-1, Math.min(history.length - 1, cursor + (event.key == 'ArrowUp' ? 1 : -1)))
        setCursor(next)
        setMessage(next < 0 ? '' : history[next])
    }

    return (
        <div className='Terminal'>
            <div className='TerminalBar'>
                {hint && <span className='TerminalHint'>{hint}</span>}
                <div className='Chips'>
                    {KINDS.map(kind => <span key={kind.value} className={`Chip ${kinds.includes(kind.value) ? 'active' : ''}`} onClick={() => toggle(kind.value)}>{kind.label}</span>)}
                </div>

                <div className='Spacer'/>

                <button className='TerminalLink' onClick={() => clearTexts(role)}>limpar</button>
            </div>

            <div className='TerminalBox mono Scroll' ref={box} data-empty={connected ? 'nenhuma linha ainda' : 'conecte um aparelho para usar o terminal'} onScroll={event => { const target = event.currentTarget; bottom.current = target.scrollHeight - target.scrollTop - target.clientHeight < 30 }}/>

            <div className='TerminalInput'>
                <input className='Input mono' placeholder='comando, ex.: $status!   (↑ ↓ histórico)' value={message} disabled={!connected} onChange={event => setMessage(event.target.value)} onKeyDown={handleKey}/>

                <select className='Select' value={settings.ending ?? '\r\n'} onChange={event => setSettings({ending: event.target.value})} title='Fim de linha'>
                    {ENDINGS.map(ending => <option key={ending.label} value={ending.value}>{ending.label}</option>)}
                </select>

                <button className='AsyncButton dark' disabled={!connected || !message.trim()} onClick={() => handleSend()}>Enviar</button>
            </div>

            <div className='TerminalQuick'>
                {QUICK.map(command => <span key={command} className={`Chip mono ${connected ? '' : 'disabled'}`} onClick={() => connected && handleSend(command)}>{command}</span>)}
            </div>

            {error && <div className='Notice bad' style={{marginTop: '.5rem'}}>{error}</div>}
        </div>
    )
}
