import { useDevice, useIssues, useLive } from '../../contexts/DeviceContext'
import { getChecks } from '../../utils/diagnostics'
import './styles.css'


// TUDO QUE O MRU E A PORTA DIZEM: O QUE ESTÁ BEM TAMBÉM APARECE, E OS EVENTOS DO PRÓPRIO FIRMWARE, OS DE ANTES DE UMA QUEDA INCLUSIVE
export default function DiagnosticsCard(){
    const {links, health} = useDevice()
    const {stats} = useLive()
    const issues  = useIssues()
    const link    = links.mru
    const checks  = getChecks({link, stat: stats.mru, health})
    const bad     = issues.filter(issue => issue.level == 'error').length
    const warn    = issues.filter(issue => issue.level == 'warn').length
    const summary = link.state == 'off' ? null : bad ? ['bad', `${bad} problema(s)`] : warn ? ['warn', `${warn} aviso(s)`] : ['ok', 'tudo certo']

    return (
        <div className='Card DiagnosticsCard'>
            <div className='CardTitle'>Diagnóstico {summary && <span className={`Pill ${summary[0]}`}>{summary[1]}</span>}</div>

            <div className='DiagnosticsBody Scroll'>
                {issues.map(issue => (
                    <div key={issue.key} className={`DiagnosticsIssue ${issue.level}`} title={issue.detail}>
                        <b>{issue.title}</b>
                        <span>{issue.detail}</span>
                    </div>
                ))}

                <div className='DiagnosticsChecks'>
                    {checks.map(check => (
                        <div key={check.label} className={`DiagnosticsCheck ${check.state}`}>
                            <span className='Dot'/>
                            <span>{check.label}</span>
                            <b title={check.text}>{check.text}</b>
                        </div>
                    ))}
                </div>

                {health.log.length > 0 && (
                    <>
                        <div className='Label DiagnosticsLabel'>Eventos do MRU · o mais novo em cima</div>
                        <div className='DiagnosticsLog mono'>{[...health.log].reverse().map((entry, index) => <div key={index} className={entry.l}><span>{entry.t.toFixed(1)} s</span>{entry.m}</div>)}</div>
                    </>
                )}
            </div>
        </div>
    )
}
