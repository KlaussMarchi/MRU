import { useState } from 'react'
import AsyncButton from '../AsyncButton'
import './styles.css'


// JANELA SOBRE A TELA: TÍTULO, CONTEÚDO E AÇÕES; CLICAR FORA OU NO X FECHA
export default function Dialog({title, tone = '', onClose, actions, children}){
    return (
        <div className='Dialog' onMouseDown={event => event.target == event.currentTarget && onClose()}>
            <div className={`DialogCard ${tone}`}>
                <div className='DialogTitle'>
                    {title}
                    <button className='DialogClose' onClick={onClose} title='Fechar'>×</button>
                </div>

                <div className='DialogBody'>{children}</div>
                {actions && <div className='DialogActions'>{actions}</div>}
            </div>
        </div>
    )
}


// PERGUNTA SIM OU NÃO NUMA Dialog: ask() DEVOLVE A RESPOSTA E dialog VAI NO JSX DA TELA
export function useConfirm(){
    const [question, setQuestion] = useState(null)

    function ask(title, text, confirm = 'Confirmar'){
        return new Promise(resolve => setQuestion({title, text, confirm, resolve}))
    }

    function answer(value){
        question.resolve(value)
        setQuestion(null)
    }

    const actions = <><AsyncButton small variant='light' text='Cancelar' onClick={() => answer(false)}/><AsyncButton small variant='red' text={question?.confirm} onClick={() => answer(true)}/></>
    const dialog  = question && <Dialog title={question.title} tone='bad' onClose={() => answer(false)} actions={actions}>{question.text}</Dialog>
    return [dialog, ask]
}
