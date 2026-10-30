import { useEffect, useMemo, useRef, useState } from 'react'
import Page from '../../components/Page'
import ConnectionBar from '../../components/ConnectionBar'
import LiveChart from '../../components/LiveChart'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { getMotion, getInclination, WINDOW } from '../../utils/motion'
import { formatNumber, formatDuration, getStored, setStored, getColor } from '../../utils'
import { getLimits, getTone, getHeaveStatus, CATEGORIES, DECKS, PERIODS, FALL, STALE } from './limits'
import './styles.css'

const TRAIL  = 60     // s DE RASTRO NO INDICADOR DO CONVÉS
const SCALE  = 1.6    // O CÍRCULO DO LIMITE FICA A 1/1,6 DO RAIO DO INDICADOR
const RADIUS = 100
const CHARTS = [{value: 'attitude', label: 'Pitch e roll · 5 min'}, {value: 'heave', label: 'Heave · 5 min'}]


// PITCH (VERTICAL, PROA PARA CIMA) CONTRA ROLL (HORIZONTAL, BORESTE À DIREITA), COM O CÍRCULO DA INCLINAÇÃO LIMITE
function Deck({series, limit, version}){
    const points = useMemo(() => {
        const data = series.getWindow(TRAIL, ['pitch', 'roll'], {points: 240})
        return data ? data[0].map((_, n) => [data[2][n], data[1][n]]).filter(([roll, pitch]) => roll != null && pitch != null) : []
    }, [version])

    const range = (limit ?? 5) * SCALE
    const map   = ([roll, pitch]) => [RADIUS + Math.max(-1, Math.min(1, roll / range)) * RADIUS, RADIUS - Math.max(-1, Math.min(1, pitch / range)) * RADIUS]
    const now   = points[points.length - 1]
    const tone  = now ? getTone(getInclination(now[1], now[0]), limit) : ''

    return (
        <svg className='Deck' viewBox={`-14 -14 ${2 * RADIUS + 28} ${2 * RADIUS + 28}`}>
            <circle cx={RADIUS} cy={RADIUS} r={RADIUS} className='DeckOuter'/>
            <circle cx={RADIUS} cy={RADIUS} r={RADIUS / SCALE} className='DeckLimit'/>
            <circle cx={RADIUS} cy={RADIUS} r={RADIUS / SCALE / 2} className='DeckHalf'/>
            <line x1={0} y1={RADIUS} x2={2 * RADIUS} y2={RADIUS} className='DeckAxis'/>
            <line x1={RADIUS} y1={0} x2={RADIUS} y2={2 * RADIUS} className='DeckAxis'/>
            <text x={RADIUS} y={-4} className='DeckLabel'>PROA</text>
            <text x={2 * RADIUS + 4} y={RADIUS + 3} className='DeckLabel' textAnchor='start'>BE</text>
            <text x={-4} y={RADIUS + 3} className='DeckLabel' textAnchor='end'>BB</text>
            <polyline points={points.map(point => map(point).join(',')).join(' ')} className='DeckTrail'/>
            {now && <circle cx={map(now)[0]} cy={map(now)[1]} r={6} className={`DeckDot ${tone}`}/>}
        </svg>
    )
}


function Tile({title, value, unit, digits = 1, rows = [], limit, tone}){
    return (
        <div className={`Tile ${tone}`}>
            <div className='TileTop'>
                <span>{title}</span>
                <span className='TileLimit'>{limit != null ? `limite ${formatNumber(limit, 1)}${unit}` : 'informativo'}</span>
            </div>

            <div className='TileValue'>{formatNumber(value, digits)}<small>{unit}</small></div>

            <div className='TileRows'>
                {rows.map(([label, number]) => <div key={label}><span>{label}</span><b>{formatNumber(number, digits)}{unit}</b></div>)}
            </div>
        </div>
    )
}


// UM PAINEL DE HMS SOBRE O QUE O MRU MANDA (O $GPPASHR DE PRODUÇÃO OU QUALQUER OUTRO FORMATO): STATUS DE POUSO, MÁXIMOS DE 20 MIN E SHR
export default function HMSPage(){
    const {getSeries} = useDevice()
    const {stats, version} = useLive()
    const [options, setOptionsState] = useState(getStored('hms', {category: 'A', deck: 1, period: 'day', chart: 'attitude'}))
    const history = useRef([])
    const status  = useRef('ok')
    const series  = getSeries('mru')
    const last    = series.last?.values
    const limits  = getLimits(options)
    const age     = stats.mru?.last ? Date.now() / 1000 - stats.mru.last : null
    const stale   = age == null || age > STALE
    const motion  = useMemo(() => getMotion(series, WINDOW), [Math.floor(version / 4)])

    useEffect(() => {
        if(motion?.shr == null || stale)
            return

        const time = Date.now() / 1000
        history.current = [...history.current.filter(item => item.time > time - FALL - 60), {time, shr: motion.shr}]
        status.current  = getHeaveStatus(history.current, limits?.rate, status.current)
    }, [motion])

    function setOptions(changes){
        const next = {...options, ...changes}
        setOptionsState(next)
        setStored('hms', next)
    }

    const pitchMax = motion ? Math.max(Math.abs(motion.up ?? 0), Math.abs(motion.down ?? 0)) : null
    const rollMax  = motion ? Math.max(Math.abs(motion.port ?? 0), Math.abs(motion.starboard ?? 0)) : null
    const checks   = limits ? [getTone(pitchMax, limits.angle), getTone(rollMax, limits.angle), getTone(motion?.inclination, limits.inclination), getTone(motion?.velocity, limits.rate), status.current] : []
    const closed   = !limits || checks.includes('bad')
    const state    = stale ? 'idle' : closed ? 'bad' : checks.includes('warn') ? 'warn' : 'ok'
    const derived  = last && last.heave_rate == null

    const banner = {
        idle: {title: 'SEM DADOS', text: age != null ? `nenhum pacote há ${formatNumber(age, 0)} s` : stats.mru ? 'o MRU está conectado, mas não transmite: inicie o stream' : 'conecte o MRU (NMEA, LIST ou JSON)'},
        bad: {title: 'HELIDEQUE FECHADO', text: !limits ? 'operação noturna não permitida em helideque classe 3' : 'um parâmetro dos últimos 20 min passou do limite da NORMAM-223'},
        warn: {title: 'LIBERADO · ATENÇÃO', text: 'um parâmetro está acima de 90% do limite'},
        ok: {title: 'LIBERADO PARA POUSO', text: 'todos os parâmetros dos últimos 20 min dentro dos limites'}
    }[state]

    return (
        <Page title='HMS' subtitle='Helideck Monitoring System simulado sobre o stream do MRU, com os limites da NORMAM-223 (Tabela 1)' actions={<ConnectionBar role='mru'/>} className='HMSPage'>

            <div className={`Banner ${state}`}>
                <div className='BannerLight'/>

                <div className='BannerText'>
                    <div className='BannerTitle'>{banner.title}</div>
                    <div className='BannerDetail'>{banner.text} · status simulado, não homologado</div>
                </div>

                <div className='BannerOptions'>
                    {[[CATEGORIES, 'category'], [DECKS, 'deck'], [PERIODS, 'period']].map(([items, key]) => (
                        <div key={key} className='Segmented'>
                            {items.map(item => <span key={item.value} className={options[key] == item.value ? 'on' : ''} onClick={() => setOptions({[key]: item.value})}>{item.label}</span>)}
                        </div>
                    ))}
                </div>
            </div>

            <div className='HMSGrid'>
                <div className='Tiles'>
                    <Tile title='Pitch (caturro)' value={last?.pitch} unit='°' limit={limits?.angle} tone={getTone(pitchMax, limits?.angle)} rows={[['máx. proa ↑', motion?.up], ['máx. proa ↓', motion?.down]]}/>
                    <Tile title='Roll (balanço)' value={last?.roll} unit='°' limit={limits?.angle} tone={getTone(rollMax, limits?.angle)} rows={[['máx. BB', motion?.port], ['máx. BE', motion?.starboard]]}/>
                    <Tile title='Inclinação' value={last ? getInclination(last.pitch, last.roll) : null} unit='°' limit={limits?.inclination} tone={getTone(motion?.inclination, limits?.inclination)} rows={[['máx. 20 min', motion?.inclination]]}/>
                    <Tile title='SHR (SVArf)' value={motion?.shr} unit=' m/s' limit={limits?.rate} tone={status.current == 'bad' ? 'bad' : getTone(motion?.shr, limits?.rate)} rows={[['2 × RMS da vel. do heave', motion?.shr]]}/>
                    <Tile title='Vel. arfagem (VArf)' value={motion?.velocity} unit=' m/s' digits={2} limit={limits?.rate} tone={getTone(motion?.velocity, limits?.rate)} rows={[['na maior oscilação', motion?.velocity]]}/>
                    <Tile title='Arfagem (Arf)' value={motion?.heave} unit=' m' digits={2} tone='' rows={[['heave agora', last?.heave], ['limite só sem VArf/SHR', limits?.heave]]}/>
                </div>

                <div className='Card DeckCard'>
                    <div className='CardTitle'>Convés <span className='hint'>proa {formatNumber(last?.yaw, 1)}°</span></div>
                    <Deck series={series} limit={limits?.inclination} version={version}/>
                    <div className='Muted DeckNote'>círculo vermelho: inclinação limite · rastro: último minuto</div>
                </div>
            </div>

            <div className='Card HMSChart'>
                <div className='Toolbar'>
                    <div className='Segmented'>
                        {CHARTS.map(item => <span key={item.value} className={options.chart == item.value ? 'on' : ''} onClick={() => setOptions({chart: item.value})}>{item.label}</span>)}
                    </div>

                    <span className='Muted Grow'>Janela de {formatDuration(Math.min(motion?.span ?? 0, WINDOW))} de {formatDuration(WINDOW)}. {derived ? 'O NMEA não traz a velocidade do heave: VArf e SHR saem da derivada. ' : ''}Valores no LEVER_POINT gravado no MRU.</span>
                </div>

                {options.chart == 'heave'
                    ? <LiveChart unit='m · + para baixo' digits={3} seconds={300} lines={[{key: 'heave', label: 'heave', color: getColor('heave')}]}/>
                    : <LiveChart unit='°' seconds={300} lines={[{key: 'pitch', label: 'pitch', color: getColor('pitch')}, {key: 'roll', label: 'roll', color: getColor('roll')}]} bands={limits ? [{value: limits.angle, color: '#c62828'}, {value: -limits.angle, color: '#c62828'}] : []}/>}
            </div>
        </Page>
    )
}
