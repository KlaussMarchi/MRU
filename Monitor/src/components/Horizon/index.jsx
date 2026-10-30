import './styles.css'

const RADIUS = 100
const SPAN   = 30    // ° DE PITCH DO CENTRO À BORDA DO MOSTRADOR
const TICKS  = [-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60]


// INDICADOR DE ATITUDE: O MAR GIRA COM O ROLL E SOBE OU DESCE COM O PITCH, O SÍMBOLO DO MRU FICA PARADO NO CENTRO
export default function Horizon({pitch, roll, size = 180}){
    const idle   = pitch == null || roll == null
    const shift  = idle ? 0 : Math.max(-1.2, Math.min(1.2, pitch / SPAN)) * RADIUS
    const rotate = idle ? 0 : -roll

    return (
        <svg className={`Horizon ${idle ? 'idle' : ''}`} width={size} height={size} viewBox='-110 -110 220 220' role='img' aria-label='Atitude'>
            <defs>
                <clipPath id='horizonDial'><circle r={RADIUS}/></clipPath>
            </defs>

            <g clipPath='url(#horizonDial)'>
                <g transform={`rotate(${rotate}) translate(0 ${shift})`}>
                    <rect x={-300} y={-300} width={600} height={300} className='HorizonSky'/>
                    <rect x={-300} y={0} width={600} height={300} className='HorizonSea'/>
                    <line x1={-300} y1={0} x2={300} y2={0} className='HorizonLine'/>
                    {[-20, -10, 10, 20].map(value => <line key={value} x1={-18} x2={18} y1={-value / SPAN * RADIUS} y2={-value / SPAN * RADIUS} className='HorizonPitch'/>)}
                </g>
            </g>

            <circle r={RADIUS} className='HorizonRing'/>
            {TICKS.map(value => <line key={value} x1={0} y1={-RADIUS} x2={0} y2={-RADIUS + (value % 30 ? 6 : 11)} transform={`rotate(${value})`} className='HorizonTick'/>)}
            <path d={`M 0 ${-RADIUS + 2} l -6 10 h 12 z`} transform={`rotate(${rotate})`} className='HorizonPointer'/>
            <path d='M -52 0 H -18 L -9 9 L 0 0 L 9 9 L 18 0 H 52' className='HorizonSymbol'/>
            <circle r={3.5} className='HorizonCenter'/>
        </svg>
    )
}
