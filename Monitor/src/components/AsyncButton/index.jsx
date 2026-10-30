import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import './styles.css'


export default function AsyncButton({text, icon, onClick = () => null, variant = 'dark', disabled = false, loading = false, small = false, large = false, title}){
    const [running, setRunning] = useState(false)
    const busy = running || loading

    async function handleClick(){
        if(busy || disabled)
            return

        setRunning(true)

        try {
            await onClick()
        }
        finally {
            setRunning(false)
        }
    }

    return (
        <button className={`AsyncButton ${variant} ${small ? 'small' : ''} ${large ? 'large' : ''}`} disabled={disabled || busy} onClick={handleClick} title={title}>
            {busy ? <span className='loadingCircle'/> : <>{icon && <FontAwesomeIcon icon={icon}/>}{text}</>}
        </button>
    )
}
