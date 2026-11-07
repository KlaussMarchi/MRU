import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import { useDevice } from '../../contexts/DeviceContext'
import { getRawFactor, formatNumber } from '../../utils'
import './styles.css'

const DELAY  = 0.12    // s ATRÁS DO RELÓGIO: O QUE O POLL AINDA NÃO TROUXE NÃO VIRA BURACO NA PONTA
const CADENCE = [{seconds: 60, every: 0}, {seconds: 300, every: 100}, {seconds: Infinity, every: 400}]    // ms ENTRE QUADROS POR JANELA: ATÉ 1 min, TODO QUADRO DA TELA
const AXIS  = {stroke: '#667085', grid: {stroke: '#eef0f3', width: 1}, ticks: {show: false}, font: '11px Inter, sans-serif', labelFont: '600 11px Inter, sans-serif'}


// MÉDIA EXPONENCIAL COM CONSTANTE DE TEMPO tau EM SEGUNDOS, PELO ESPAÇAMENTO REAL DOS PONTOS
function smooth(x, columns, tau){
    for(const column of columns){
        let state = null

        for(let n = 0; n < x.length; n++){
            const value = column[n]

            if(value == null){
                state = null
                continue
            }

            const alpha = state == null ? 1 : 1 - Math.exp(-(x[n] - x[n - 1]) / tau)
            state = state == null ? value : state + alpha * (value - state)
            column[n] = state
        }
    }
}


// O GRÁFICO DO STREAM NO ESPAÇO DO PAI: UMA GRANDEZA (UM EIXO), LINHAS DE UM OU DOS DOIS APARELHOS NO TEMPO DO PRIMEIRO, O VALOR ATUAL NA LEGENDA E O DO CURSOR AO PASSAR O MOUSE
export default function LiveChart({lines, unit = '', digits = 2, seconds = 30, paused = false, tau = 0, bands = [], empty = 'aguardando dados do MRU', action = null}){
    const box    = useRef()
    const holder = useRef()
    const plot   = useRef()
    const values = useRef([])
    const clock  = useRef()
    const {getSeries} = useDevice()
    const keys = lines.map(line => `${line.role ?? 'mru'}:${line.key}:${line.color}`).join() + bands.map(band => band.value).join()

    function showValues(index){
        const data = plot.current?.data

        if(!data?.[0]?.length)
            return

        const point = index ?? data[0].length - 1
        lines.forEach((line, k) => {
            if(values.current[k])
                values.current[k].textContent = formatNumber(data[k + 1][point], digits)
        })

        if(clock.current)
            clock.current.textContent = index == null ? 'agora' : `${formatNumber(data[0][point], 1)} s`
    }

    useEffect(() => {
        const options = {
            width: holder.current.clientWidth,
            height: holder.current.clientHeight,
            legend: {show: false},
            cursor: {points: {show: false}, drag: {x: false, y: false}, x: true, y: false},
            pxAlign: 0,    // LINHA FORA DA GRADE DE PIXELS: A ROLAGEM CONTÍNUA NÃO TREME
            scales: {x: {time: false, range: () => [-seconds, 0]}},
            axes: [
                {...AXIS, values: (u, ticks, axis, space, step) => ticks.map(tick => `${tick.toFixed(step < 1 ? 1 : 0)} s`)},
                {...AXIS, size: 52, values: (u, ticks, axis, space, step) => ticks.map(tick => tick.toFixed(Math.min(4, Math.max(0, -Math.floor(Math.log10(step))))))}
            ],
            series: [{}, ...lines.map(line => ({label: line.label, stroke: line.color, width: 1.75, dash: line.dash, points: {show: false}})), ...bands.map(band => ({stroke: band.color, width: 1, dash: [6, 5], points: {show: false}}))],
            hooks: {setCursor: [u => showValues(u.cursor.idx)]}
        }

        plot.current = new uPlot(options, [[], ...lines.map(() => []), ...bands.map(() => [])], holder.current)
        const observer = new ResizeObserver(() => holder.current && plot.current.setSize({width: holder.current.clientWidth, height: holder.current.clientHeight}))    // O REACT SOLTA O ref ANTES DE DESLIGAR O OBSERVADOR
        observer.observe(holder.current)

        return () => {
            observer.disconnect()
            plot.current.destroy()
        }
    }, [keys, unit, digits, seconds])

    useEffect(() => {
        if(paused)
            return

        const every = CADENCE.find(option => seconds <= option.seconds).every
        let frame, drawn = 0

        // O EIXO ANDA COM O RELÓGIO A CADA QUADRO DA TELA, NÃO A CADA LOTE DO POLL: O GRÁFICO ROLA LISO EM QUALQUER TAXA
        function draw(moment){
            frame = requestAnimationFrame(draw)

            if(document.hidden || moment - drawn < every || !box.current)
                return

            drawn = moment
            const base   = lines[0]?.role ?? 'mru'
            const series = getSeries(base)
            const own    = lines.filter(line => (line.role ?? 'mru') == base)
            const raw    = series.last?.layout == 'raw'
            const factor = key => raw ? getRawFactor(key, series.last.values) : 1
            const end    = Date.now() / 1000 - DELAY
            const data   = series.getWindow(seconds, own.map(line => line.key), {factor, until: end})
            box.current.classList.toggle('waiting', !data)

            if(!data)
                return

            const times   = data[0].map(x => x + end)
            const columns = lines.map(line => (line.role ?? 'mru') == base ? data[1 + own.indexOf(line)] : getSeries(line.role).sample(times, line.key))

            if(tau > 0)
                smooth(data[0], columns, tau)

            plot.current.setData([data[0], ...columns, ...bands.map(band => data[0].map(() => band.value))])

            if(plot.current.cursor.idx == null)
                showValues(null)
        }

        frame = requestAnimationFrame(draw)
        return () => cancelAnimationFrame(frame)
    }, [keys, seconds, paused, tau])

    return (
        <div className='LiveChart waiting' ref={box}>
            <div className='LiveChartLegend'>
                {lines.map((line, k) => (
                    <span key={`${line.role}:${line.key}`} className='LiveChartItem'>
                        <span className={`LiveChartSwatch ${line.dash ? 'dashed' : ''}`} style={{'--color': line.color}}/>
                        {line.label}
                        <span className='LiveChartValue' ref={element => values.current[k] = element}>—</span>
                        <span className='LiveChartUnit'>{unit.split(' ')[0]}</span>
                    </span>
                ))}

                <span className='LiveChartClock' ref={clock}>agora</span>
            </div>

            <div ref={holder} className='LiveChartPlot'/>
            <div className='LiveChartEmpty'><span>{empty}</span>{action}</div>
        </div>
    )
}
