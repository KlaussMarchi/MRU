import { useEffect, useRef, useState } from 'react'
import Page from '../../components/Page'
import ConnectionBar from '../../components/ConnectionBar'
import AsyncButton from '../../components/AsyncButton'
import Dropdown from '../../components/Dropdown'
import { useConfirm } from '../../components/Dialog'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, getBaud, getCRC, getLoad, formatFloat, formatNumber, BAUDS, FREQUENCIES, OUTPUTS, PROTOCOLS, LAYOUTS, MODELS } from '../../utils'
import './styles.css'

const COMMAND = 200    // CARACTERES POR CL:, ABAIXO DO CMD_MAX_SIZE = 256 DO FIRMWARE
const NONE    = 'none'


// OS VALORES DE UMA CHAVE EM COMANDOS CL:CHAVE@posicao$v1,v2,...! QUE CABEM NO BUFFER DO FIRMWARE
function getCommands(key, values){
    const commands = []
    let [offset, tokens] = [0, []]

    values.forEach((value, index) => {
        const token = formatFloat(value)
        const size  = `CL:${key}@${offset}$${[...tokens, token].join(',')}!`.length

        if(size > COMMAND && tokens.length){
            commands.push({offset, text: `CL:${key}@${offset}$${tokens.join(',')}!`})
            ;[offset, tokens] = [index, []]
        }

        tokens.push(token)
    })

    commands.push({offset, text: `CL:${key}@${offset}$${tokens.join(',')}!`})
    return commands
}

// CHAVE A CHAVE, O CRC DO QUE O MRU GUARDOU CONTRA O DOS VALORES DO PACOTE
function getMismatch(check, firmware, keys){
    return keys.filter(key => parseInt(check.keys[key]?.[1], 16) != parseInt(getCRC(firmware[key]), 16))
}


export default function ProductionPage(){
    const {links, query, configure, reboot} = useDevice()
    const {stats} = useLive()
    const {settings, selection} = useGlobalContext()
    const [library, setLibrary]     = useState([])
    const [confirmation, ask]       = useConfirm()
    const [chosen, setChosen]       = useState(selection.calibration ?? NONE)
    const [protocol, setProtocol]   = useState(2)
    const [frequency, setFrequency] = useState(10)
    const [output, setOutput]       = useState(3)
    const [baud, setBaud]           = useState(115200)
    const [steps, setSteps]         = useState([])
    const [result, setResult]       = useState(null)
    const list   = useRef()
    const link   = links.mru
    const synced = link.state == 'synced'
    const bundle = library.find(item => item.path == chosen)
    const status = link.status
    const flash  = status?.calibration == 'flash'
    const load   = getLoad(protocol, frequency, baud)
    const usb    = output == 1

    useEffect(() => {
        call('list_calibrations', {folder: settings.calibrations}).then(items => setLibrary(items.filter(item => item.info?.firmware)))
    }, [settings.calibrations])

    useEffect(() => {
        setBaud(Math.max(getBaud(protocol, frequency), 9600))
    }, [protocol, frequency])

    useEffect(() => {
        if(list.current)
            list.current.scrollTop = list.current.scrollHeight
    }, [steps])

    function step(text, state = 'run'){
        setSteps(current => {
            const last = current[current.length - 1]
            const done = last?.state == 'run' ? [...current.slice(0, -1), {...last, state: 'ok'}] : current
            return [...done, {text, state}]
        })
    }

    function fail(text){
        setSteps(current => [...current.slice(0, -1), {...current[current.length - 1], state: 'bad'}, {text, state: 'bad'}])
    }

    function finish(text){
        setSteps(current => [...current.slice(0, -1), {...current[current.length - 1], state: 'ok'}, {text, state: 'ok'}])
    }

    // CL: DE TODAS AS CHAVES, CRC NA PENDENTE, $calibration_save!, REINÍCIO E CRC DE NOVO NA QUE FICOU NA FLASH
    async function upload(){
        const firmware = bundle.info.firmware
        step('lendo as chaves e tamanhos que este firmware aceita ($calibration_check!)')
        const check = JSON.parse(await query('$calibration_check!', ['"keys"'], 3000).catch(() => { throw new Error('o MRU não respondeu $calibration_check!: atualize o firmware para v1.0.8') }))
        const model = firmware.ATTITUDE_MODEL[0]
        const keys  = []

        for(const [key, [size]] of Object.entries(check.keys)){
            const values = firmware[key]

            if(!values)    // CHAVE DE OUTRA ESTRATÉGIA: FICA A QUE O MRU JÁ TEM
                continue

            if(values.length == size){
                keys.push(key)
                continue
            }

            if(key.startsWith('MACHINE_') && model != 2)    // MODELO DE ML COM OUTRA JANELA: SÓ IMPORTA SE FOR O ESCOLHIDO
                continue

            throw new Error(`${key}: o pacote tem ${values.length} valores e o firmware compilado ${size}; recompile o firmware com os config.h deste pacote`)
        }

        const commands = keys.flatMap(key => getCommands(key, firmware[key]).map(command => ({key, ...command})))

        for(const [index, command] of commands.entries()){
            step(`enviando ${command.key} (${index + 1}/${commands.length})`)
            const response = await query(command.text, [`$OK:${command.key}@${command.offset}+`, `$ERROR:${command.key}`], 2500).catch(() => query(command.text, [`$OK:${command.key}@${command.offset}+`, `$ERROR:${command.key}`], 2500))

            if(response.includes('ERROR'))
                throw new Error(`o MRU recusou ${command.text.slice(0, 60)}…`)
        }

        step('conferindo o CRC de cada chave antes de gravar')
        const pending = JSON.parse(await query('$calibration_check!', ['"keys"'], 3000))
        const wrong   = getMismatch(pending, firmware, keys)

        if(wrong.length)
            throw new Error(`CRC diferente em ${wrong.join(', ')}: nada foi gravado`)

        step('gravando na flash e reiniciando')
        await query('$calibration_save!', ['$CALIBRATION SAVED!'], 3000)
        await reboot(link.settings)

        step('conferindo a calibração gravada')
        const saved = JSON.parse(await query('$calibration_check!', ['"keys"'], 3000))
        const after = getMismatch(saved, firmware, keys)

        if(saved.source != 'flash' || after.length)
            throw new Error(`a flash não confere: ${after.join(', ') || saved.source}`)

        finish(`calibração gravada: ${keys.length} chaves, modelo ${MODELS[model]}`)
    }

    async function handleUpload(){
        setSteps([])
        setResult(null)

        try {
            await upload()
        }
        catch(error) {
            fail(String(error.message ?? error))
        }
    }

    async function handleErase(){
        if(!await ask('Apagar a calibração da flash', 'O MRU volta aos config.h compilados no firmware.', 'Apagar'))
            return

        setSteps([])
        step('apagando a calibração da flash')

        try {
            await query('$calibration_erase!', ['$CALIBRATION ERASED!'], 3000)
            await reboot(link.settings)
            finish('o MRU usa de novo a calibração compilada')
        }
        catch(error) {
            fail(String(error.message ?? error))
        }
    }

    // CALIBRAÇÃO (SE ESCOLHIDA), CONFIGURAÇÃO DE SAÍDA NUM REINÍCIO SÓ E A CONFERÊNCIA PELO $status!
    async function handlePrepare(){
        setSteps([])
        setResult(null)

        try {
            if(bundle)
                await upload()

            const calibrated = Boolean(bundle) || flash
            const changes = {device_mode: 0, kernel_mode: 0, streamer_mode: calibrated ? 0 : 2, protocol, frequency, output, baudrate: baud, autostream: 1}
            step(`configurando: ${calibrated ? 'CALIBRATED' : 'SCALE'}, ${PROTOCOLS.find(item => item.value == protocol).label}, ${frequency} Hz, ${OUTPUTS.find(item => item.value == output).label} a ${baud} bps`)
            await configure(changes, text => step(text))

            const final = JSON.parse(await query('$status!', ['"firmware"'], 2500))
            const expected = {device_mode: 0, kernel_mode: 0, streamer_mode: changes.streamer_mode, protocol, autostream: true}
            const wrong = Object.entries(expected).filter(([key, value]) => final[key] != value).map(([key]) => key)

            if(wrong.length)
                throw new Error(`o MRU não ficou como pedido em: ${wrong.join(', ')}`)

            setResult({...final, output, baud})
            finish('pronto para produção')
        }
        catch(error) {
            fail(String(error.message ?? error))
        }
    }

    const running = steps.some(item => item.state == 'run')
    const current = stats.mru
    const layout  = LAYOUTS[current?.layout]

    return (
        <Page title='Produção' subtitle='Grava a calibração no MRU pela serial e o deixa transmitindo sozinho ao ligar' actions={<ConnectionBar role='mru'/>} className='ProductionPage'>
            <div className='Column ProductionSteps'>
                <div className='Card'>
                    <div className='Numbered'><span>1</span>Calibração<span className='hint'>{status ? `no MRU agora: ${flash ? 'gravada na flash' : 'compilada no firmware'} · ${MODELS[status.model] ?? '—'}` : 'sincronize para ver a do MRU'}</span></div>

                    <Dropdown value={chosen} onChange={setChosen} options={[{value: NONE, label: flash ? 'Manter a calibração que está no MRU' : 'Nenhuma: o MRU sai na escala do Kernel (SCALE)'}, ...library.map(item => ({value: item.path, label: `${item.info.id ?? 'MRU'} · ${item.info.strategy}${item.info.reference == 'debug' ? ' · debug' : ''} · ${item.info.created?.replace('T', ' ')}`}))]}/>

                    {bundle && (
                        <div className='BundleFacts'>
                            <div><span>Modelo de atitude</span><b>{MODELS[bundle.info.firmware.ATTITUDE_MODEL[0]]}</b></div>
                            <div><span>Roll / pitch no balanço</span><b>{formatNumber(bundle.info.metrics?.roll?.rms_dyn, 3)}° / {formatNumber(bundle.info.metrics?.pitch?.rms_dyn, 3)}°</b></div>
                            <div><span>Heave</span><b>{formatNumber(bundle.info.metrics?.heave?.rmse, 3)} m</b></div>
                            <div><span>Montagem do ensaio</span><b>{bundle.info.align ? `[${bundle.info.align.join(', ')}]` : 'não registrada'}</b></div>
                            <div><span>Braço até o ponto</span><b>[{bundle.info.firmware.LEVER_POINT.map(value => formatNumber(value, 2)).join(', ')}] m</b></div>
                        </div>
                    )}

                    {bundle?.info.reference == 'debug' && <div className='Notice warn ProductionNotice'>Este pacote saiu de uma sessão com referência em debug: serve para testar o envio, não para operar.</div>}
                    {bundle && <div className='Notice info ProductionNotice'>Confira o braço (LEVER_POINT) e o período do heave antes de ir a bordo: os do pacote são os do ensaio na plataforma.</div>}

                    <div className='Actions end'>
                        {flash && <AsyncButton text='Apagar a da flash' variant='ghost' onClick={handleErase} disabled={!synced || running}/>}
                        <AsyncButton text='Só enviar a calibração' variant='light' onClick={handleUpload} disabled={!synced || !bundle || running}/>
                    </div>
                </div>

                <div className='Card'>
                    <div className='Numbered'><span>2</span>Saída em operação<span className='hint'>{bundle || flash ? 'CALIBRATED' : 'SCALE'} · Kernel em HR · autostream ligado</span></div>

                    <div className='OutputFields'>
                        <Dropdown label='Protocolo' value={protocol} onChange={setProtocol} options={PROTOCOLS}/>
                        <Dropdown label='Frequência' value={frequency} onChange={setFrequency} options={FREQUENCIES.filter(value => value <= 100).map(value => ({value, label: `${value} Hz`}))}/>
                        <Dropdown label='Porta ao ligar' value={output} onChange={setOutput} options={OUTPUTS}/>
                        <Dropdown label='Baud RS232/RS422' value={baud} onChange={setBaud} options={BAUDS.map(value => ({value, label: `${value}`}))}/>
                    </div>

                    <div className='Load'>
                        <div className='LoadText'>
                            <span>{usb ? 'Pelo USB o baud não limita' : `Ocupação do link: ${(load * 100).toFixed(0)}% de ${baud} bps`}</span>
                            <span className='Muted'>um comando por outra porta muda o destino até o próximo reinício</span>
                        </div>
                        {!usb && <div className={`Progress ${load > 0.8 ? 'bad' : load > 0.5 ? 'warn' : ''}`}><div style={{width: `${Math.min(100, load * 100)}%`}}/></div>}
                    </div>

                    <div className='Actions end'>
                        <AsyncButton text={bundle ? 'Enviar calibração e preparar' : 'Preparar para produção'} large onClick={handlePrepare} disabled={!synced || running || load > 1}/>
                    </div>
                </div>
            </div>

            <div className='Column ProductionProgress'>
                <div className='Card fill'>
                    <div className='CardTitle'>Andamento {running && <span className='Pill warn'><span className='Dot pulse'/>em andamento</span>}</div>

                    {steps.length == 0 && (
                        <div className='Plan'>
                            <div className='Muted'>{synced ? 'Ao preparar, o app:' : 'Os botões ficam ativos com o MRU sincronizado (ACK respondido). Ao preparar, o app:'}</div>
                            <ol>
                                <li>envia cada chave da calibração em comandos CL: e confere o CRC de todas antes de gravar;</li>
                                <li>grava na flash, reinicia e confere o CRC de novo;</li>
                                <li>configura protocolo, frequência, porta e baud num reinício só;</li>
                                <li>verifica pelo $status! que o MRU ficou como pedido.</li>
                            </ol>
                        </div>
                    )}

                    <div className='Checklist Scroll' ref={list}>
                        {steps.map((item, index) => (
                            <div key={index} className={`Check ${item.state}`}>
                                <span className='CheckMark'>{item.state == 'ok' ? '✓' : item.state == 'bad' ? '✕' : <span className='Spinner'/>}</span>
                                <span>{item.text}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {result && (
                    <div className='Card Ready'>
                        <div className='CardTitle'>Pronto para produção <span className='Pill ok'>verificado</span></div>

                        <div className='Facts wide'>
                            <span>MRU</span><b>{result.id} · {result.firmware}</b>
                            <span>Cadeia</span><b className='small'>{result.processing}</b>
                            <span>Calibração</span><b>{result.calibration == 'flash' ? 'gravada na flash' : 'compilada'}</b>
                            <span>Saída</span><b>{OUTPUTS.find(item => item.value == result.output)?.label} · {result.baud} bps</b>
                            <span>Stream agora</span><b>{layout ? `${layout.label}${layout.label != current.format?.toUpperCase() ? ` · ${current.format?.toUpperCase()}` : ''} · ${Math.round(current.rate)} Hz` : 'aguardando'}</b>
                        </div>

                        <div className='Muted' style={{marginTop: '.7rem'}}>Desligue e ligue o MRU antes de instalar: o Kernel só aplica a própria flash ao ligar.</div>
                    </div>
                )}
            </div>

            {confirmation}
        </Page>
    )
}
