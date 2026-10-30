import { QUANTITIES, VARIABLES, getQuantity, getColor } from '../../utils'


// A GRANDEZA DO GRÁFICO E AS VARIÁVEIS DELA QUE APARECEM: UM EIXO SÓ, CADA VARIÁVEL COM A COR FIXA DA POSIÇÃO DELA
export default function QuantityPicker({value, onChange, quantities = QUANTITIES.map(item => item.key)}){
    const quantity = getQuantity(value.quantity)

    function choose(key){
        const next = getQuantity(key)
        onChange({quantity: key, keys: next.shown ?? next.keys})
    }

    function toggle(key){
        const keys = value.keys.includes(key) ? value.keys.filter(item => item != key) : quantity.keys.filter(item => item == key || value.keys.includes(item))
        onChange({...value, keys: keys.length ? keys : [key]})
    }

    return (
        <div className='QuantityPicker'>
            <select className='Select' value={quantity.key} onChange={event => choose(event.target.value)} title='Grandeza no gráfico'>
                {QUANTITIES.filter(item => quantities.includes(item.key)).map(item => <option key={item.key} value={item.key}>{item.label}{item.unit ? ` (${item.unit.split(' ')[0]})` : ''}</option>)}
            </select>

            {quantity.keys.length > 1 && (
                <div className='Chips'>
                    {quantity.keys.map(key => (
                        <span key={key} className={`Chip Variable ${value.keys.includes(key) ? 'active' : ''}`} onClick={() => toggle(key)}>
                            <span className='Swatch' style={{background: getColor(key)}}/>{VARIABLES[key].label}
                        </span>
                    ))}
                </div>
            )}
        </div>
    )
}
