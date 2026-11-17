import Select from '../Select'


// UM CAMPO COM RÓTULO E O DROPDOWN (components/Select): options = [{value, label, hint}]; O onChange DEVOLVE O value COM O TIPO DA OPÇÃO
export default function Dropdown({label, value, onChange, options, disabled = false, width, placeholder, search, compact}){
    return (
        <label className='Field' style={{width}}>
            {label && <span className='Label'>{label}</span>}
            <Select value={value} options={options} onChange={onChange} disabled={disabled} placeholder={placeholder} search={search} compact={compact}/>
        </label>
    )
}
