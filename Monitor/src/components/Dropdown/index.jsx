export default function Dropdown({label, value, onChange, options, disabled = false, width}){
    return (
        <label className='Field' style={{width}}>
            {label && <span className='Label'>{label}</span>}

            <select className='Select' value={value ?? ''} disabled={disabled} onChange={event => onChange(options.find(option => String(option.value) == event.target.value)?.value ?? event.target.value)}>
                {options.map(option => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}
            </select>
        </label>
    )
}
