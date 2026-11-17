import { useState } from 'react'
import Autocomplete from '@mui/material/Autocomplete'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faCheck, faChevronDown, faMagnifyingGlass } from '@fortawesome/free-solid-svg-icons'
import './styles.css'

const SEARCH = 7    // A PARTIR DE QUANTAS OPÇÕES O CAMPO VIRA BUSCA
const PAPER  = {
    marginTop: '6px',
    borderRadius: '11px',
    border: '1px solid var(--line)',
    boxShadow: '0 14px 36px rgba(16, 24, 40, .14)',
    fontFamily: 'inherit',
    fontSize: '.84rem',
    color: 'var(--ink)',
    '& .MuiAutocomplete-listbox': {padding: '5px', maxHeight: '19rem'},
    '& .MuiAutocomplete-option': {minHeight: 'auto', padding: '.5rem .6rem', borderRadius: '8px', gap: '.6rem'},
    '& .MuiAutocomplete-option.Mui-focused': {background: 'var(--soft)'},
    '& .MuiAutocomplete-option[aria-selected="true"], & .MuiAutocomplete-option[aria-selected="true"].Mui-focused': {background: 'var(--accent-soft)', color: 'var(--accent-strong)', fontWeight: 600},
    '& .MuiAutocomplete-noOptions, & .MuiAutocomplete-loading': {fontSize: '.8rem', color: 'var(--muted)', padding: '.7rem .9rem'}
}


function fold(text){
    return String(text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}


// TODAS AS PALAVRAS DIGITADAS, SEM ACENTO, NO NOME, NO VALOR OU NO DETALHE DA OPÇÃO
function filter(options, {inputValue}){
    const words = fold(inputValue).split(/\s+/).filter(Boolean)
    return options.filter(option => words.every(word => fold(`${option.label} ${option.value} ${option.hint ?? ''}`).includes(word)))
}


// O DROPDOWN (O MESMO DO SIGHIR DESKTOP, Etilometro/desktop/src/components/Select): options = [{value, label, hint}]; COM MUITAS OPÇÕES ABRE COM A BUSCA; value null NUM SELETOR DE AÇÃO (O placeholder FICA);
// loading: A LISTA AINDA VEM DO SERVIDOR (SPINNER E loadingText, NUNCA "NADA ENCONTRADO"); O VALOR FORA DA LISTA (O SENSOR LIDO DO APARELHO) APARECE MESMO ASSIM;
// onOpen: ATUALIZAR A LISTA AO ABRIR (AS PORTAS); className NA RAIZ, PARA A LARGURA; title É A DICA DO CAMPO
export default function Select({value, options, onChange, placeholder = 'escolha', disabled = false, loading = false, loadingText = 'carregando do servidor...', compact = false, search, onOpen, className, title}){
    const [open, setOpen] = useState(false)
    const [text, setText] = useState('')
    const listed     = options.find(option => option.value == value)
    const selected   = listed ?? (value ? {value, label: String(value), hint: 'fora da lista'} : null)
    const choices    = listed || !selected ? options : [selected, ...options]
    const searchable = search ?? options.length >= SEARCH

    return (
        <Autocomplete
            className={className}
            options={choices}
            value={selected}
            inputValue={open && searchable ? text : selected?.label ?? ''}
            onInputChange={(event, next, reason) => reason == 'input' && setText(next)}
            onChange={(event, option) => option && onChange(option.value)}
            onOpen={() => { setText(''); setOpen(true); onOpen?.() }}
            onClose={() => setOpen(false)}
            getOptionLabel={option => option.label}
            isOptionEqualToValue={(option, current) => option.value == current.value}
            filterOptions={filter}
            disabled={disabled}
            loading={loading}
            loadingText={<span className='SelectLoading'><span className='Spinner'/>{loadingText}</span>}
            noOptionsText='nada encontrado'
            disableClearable
            openOnFocus
            autoHighlight
            blurOnSelect
            selectOnFocus={false}
            slotProps={{paper: {sx: PAPER}, popper: {placement: 'bottom-start', sx: {minWidth: '16rem'}}}}
            renderOption={({key, ...props}, option, {selected: chosen}) => (
                <li key={key} {...props}>
                    <span className='SelectCheck'>{chosen && <FontAwesomeIcon icon={faCheck}/>}</span>
                    <span className='SelectLabel'>{option.label}</span>
                    {option.hint && <span className='SelectHint'>{option.hint}</span>}
                </li>
            )}
            renderInput={params => (
                <div ref={params.InputProps.ref} className={`Picker ${compact ? 'compact' : ''} ${open ? 'open' : ''} ${disabled ? 'disabled' : ''}`} title={title}>
                    {open && searchable && <FontAwesomeIcon icon={faMagnifyingGlass} className='PickerIcon'/>}
                    <input {...params.inputProps} readOnly={!searchable} placeholder={open && searchable ? `buscar${selected ? ` (${selected.label})` : ''}` : loading ? loadingText : placeholder}/>
                    {selected?.hint && !open && <span className='SelectHint'>{selected.hint}</span>}
                    {loading ? <span className='Spinner' title={loadingText}/> : <FontAwesomeIcon icon={faChevronDown} className='PickerChevron'/>}
                </div>
            )}
        />
    )
}
