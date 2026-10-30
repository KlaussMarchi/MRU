import { formatDuration } from '../../utils'
import './styles.css'


// TAREFA LONGA NA FRENTE DA TELA: AS ETAPAS (QUANDO HÁ), A BARRA COM O TEMPO RESTANTE, A MENSAGEM E O FIM DO LOG
export default function Overlay({title, stage, message, progress = null, started = null, log = [], stages = [], children}){
    const elapsed = started ? Date.now() / 1000 - started : null
    const percent = progress == null ? null : Math.max(0, Math.min(1, progress))
    const left    = percent > 0.03 && elapsed > 3 ? elapsed * (1 - percent) / percent : null
    const current = stages.indexOf(stage)

    return (
        <div className='Overlay'>
            <div className='OverlayCard'>
                <div className='OverlayTitle'>{title}</div>

                <div className='OverlayBar'>
                    <div className={`OverlayFill ${percent == null ? 'indeterminate' : ''}`} style={{width: percent == null ? '35%' : `${percent * 100}%`}}/>
                </div>

                <div className='OverlayTimes'>
                    <b>{percent == null ? '' : `${(percent * 100).toFixed(0)}%`}</b>
                    <span>{elapsed != null && `decorrido ${formatDuration(elapsed)}`}{left != null && ` · restante ~${formatDuration(left)}`}</span>
                </div>

                {stages.length > 0 && (
                    <div className='OverlayStages'>
                        {stages.map((name, index) => (
                            <div key={name} className={`OverlayStage ${index < current ? 'done' : index == current ? 'now' : ''}`}>
                                <span className='OverlayMark'>{index < current ? '✓' : index == current ? <span className='Spinner'/> : ''}</span>
                                <span>{name}</span>
                                {index == current && <span className='OverlayMessage'>{message}</span>}
                            </div>
                        ))}
                    </div>
                )}

                {!stages.length && <div className='OverlayMessage'>{stage ? `${stage} · ` : ''}{message}</div>}

                {log.length > 0 && (
                    <details className='OverlayDetails'>
                        <summary>log</summary>
                        <div className='OverlayLog mono Scroll'>{log.slice(-10).map((line, index) => <div key={index}>{line}</div>)}</div>
                    </details>
                )}

                <div className='OverlayActions'>{children}</div>
            </div>
        </div>
    )
}
