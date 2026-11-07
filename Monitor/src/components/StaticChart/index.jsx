import { useEffect, useRef } from 'react'
import uPlot from 'uplot'
import '../LiveChart/styles.css'

const AXIS = {stroke: '#667085', grid: {stroke: '#eef0f3', width: 1}, ticks: {show: false}, font: '11px Inter, sans-serif', labelFont: '600 11px Inter, sans-serif'}


// SÉRIES PRONTAS (UMA SESSÃO SALVA) NO ESPAÇO DO PAI: x EM SEGUNDOS E UMA COLUNA POR LINHA, COM ARRASTE PARA APROXIMAR
export default function StaticChart({lines, data, unit = ''}){
    const holder = useRef()

    useEffect(() => {
        if(!data)
            return

        const options = {
            width: holder.current.clientWidth,
            height: holder.current.clientHeight,
            legend: {show: false},
            cursor: {points: {show: false}, drag: {x: true, y: false}},
            scales: {x: {time: false}},
            axes: [{...AXIS, values: (u, ticks, axis, space, step) => ticks.map(tick => `${tick.toFixed(step < 1 ? 1 : 0)} s`)}, {...AXIS, size: 52, values: (u, ticks, axis, space, step) => ticks.map(tick => tick.toFixed(Math.min(4, Math.max(0, -Math.floor(Math.log10(step))))))}],
            series: [{}, ...lines.map(line => ({label: line.label, stroke: line.color, width: line.width ?? 1.5, dash: line.dash, points: {show: false}}))]
        }

        const plot = new uPlot(options, data, holder.current)
        const observer = new ResizeObserver(() => holder.current && plot.setSize({width: holder.current.clientWidth, height: holder.current.clientHeight}))
        observer.observe(holder.current)

        return () => {
            observer.disconnect()
            plot.destroy()
        }
    }, [data, unit])

    return (
        <div className={`LiveChart ${data ? '' : 'waiting'}`}>
            <div className='LiveChartLegend'>
                {lines.map(line => <span key={line.label} className='LiveChartItem'><span className={`LiveChartSwatch ${line.dash ? 'dashed' : ''}`} style={{'--color': line.color}}/>{line.label}</span>)}
                <span className='LiveChartClock'>arraste para aproximar · duplo clique volta</span>
            </div>

            <div ref={holder} className='LiveChartPlot'/>
            <div className='LiveChartEmpty'>sem prévia</div>
        </div>
    )
}
