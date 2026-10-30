// A MARCA DO APP: UM INDICADOR DE ATITUDE COM O HORIZONTE INCLINADO SOBRE O MAR, O QUE O MRU MEDE
export default function Logo({size = 40}){
    return (
        <svg width={size} height={size} viewBox='0 0 512 512' role='img' aria-label='MRU Monitor'>
            <defs>
                <linearGradient id='logoBack' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stopColor='#0f2a3a'/><stop offset='1' stopColor='#0b4f5c'/></linearGradient>
                <linearGradient id='logoSky' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stopColor='#a5f3fc'/><stop offset='1' stopColor='#5eead4'/></linearGradient>
                <linearGradient id='logoSea' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stopColor='#0e7490'/><stop offset='1' stopColor='#0c3b52'/></linearGradient>
                <clipPath id='logoDial'><circle cx='256' cy='256' r='164'/></clipPath>
            </defs>

            <rect width='512' height='512' rx='116' fill='url(#logoBack)'/>

            <g clipPath='url(#logoDial)'>
                <g transform='rotate(-13 256 256)'>
                    <rect x='60' y='60' width='392' height='212' fill='url(#logoSky)'/>
                    <path d='M60 272 C 110 248 160 248 210 272 S 310 296 360 272 S 430 252 452 262 V 452 H 60 Z' fill='url(#logoSea)'/>
                    <path d='M60 272 C 110 248 160 248 210 272 S 310 296 360 272 S 430 252 452 262' fill='none' stroke='#ecfeff' strokeWidth='10' strokeLinecap='round'/>
                </g>
            </g>

            <circle cx='256' cy='256' r='164' fill='none' stroke='#e2e8f0' strokeWidth='16'/>
            <g stroke='#e2e8f0' strokeWidth='12' strokeLinecap='round'>
                <line x1='256' y1='70' x2='256' y2='40'/>
                <line x1='163' y1='95' x2='148' y2='69'/>
                <line x1='349' y1='95' x2='364' y2='69'/>
            </g>

            <path d='M150 262 H 214 L 256 222 L 298 262 H 362' fill='none' stroke='#fbbf24' strokeWidth='18' strokeLinecap='round' strokeLinejoin='round'/>
            <circle cx='256' cy='262' r='13' fill='#fbbf24'/>
        </svg>
    )
}
