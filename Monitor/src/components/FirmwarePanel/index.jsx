import { useEffect, useState } from 'react'
import { open } from '@tauri-apps/plugin-dialog'
import AsyncButton from '../AsyncButton'
import Dialog, { useConfirm } from '../Dialog'
import Overlay from '../Overlay'
import { useDevice, useLive } from '../../contexts/DeviceContext'
import { useGlobalContext } from '../../contexts/GlobalContext'
import { call, formatBytes, formatDuration } from '../../utils'
import { compareVersions } from '../../utils/diagnostics'
import './styles.css'

const STAGES = ['Sincronizar', 'Preparar', 'Enviar', 'Verificar', 'Reiniciar', 'Confirmar']
const CANCEL = ['Sincronizar', 'Preparar', 'Enviar']    // DEPOIS DISSO A IMAGEM JÁ ESTÁ NA FLASH: CANCELAR NÃO DESFAZ
const USB    = 22000    // bytes/s MEDIDOS DO ENVIO COM PAUSAS, O TETO EM QUALQUER PORTA
const SLOW   = 300      // s: ACIMA DISSO VALE AVISAR QUE A LINHA É LENTA
const FILTERS = [{name: 'Firmware (.bin)', extensions: ['bin']}]


function getEta(image, link){
    const line = link.kind == 'usb' || !link.baud ? USB : Math.min(USB, link.baud / 10 * 0.75)    // O BASE64 OCUPA 4/3 DOS BYTES
    return image.size / line
}


// O FIRMWARE NOVO PELO CABO: ESCOLHE O ARQUIVO, MOSTRA O QUE ELE É, E O MRU SÓ TROCA DE FIRMWARE DEPOIS DE CONFERIR TUDO
export default function FirmwarePanel(){
    const {links, update, setUpdate, updateFirmware, cancelUpdate} = useDevice()
    const {recording} = useLive()
    const {defaults, settings, setSettings} = useGlobalContext()
    const [image, setImage]     = useState(null)
    const [problem, setProblem] = useState('')
    const [confirmation, ask]   = useConfirm()
    const link    = links.mru
    const path    = settings.firmware ?? defaults?.firmware ?? ''
    const synced  = link.state == 'synced'
    const order   = compareVersions(image?.version, link.firmware)
    const eta     = image ? getEta(image, link) : 0
    const running = update?.status == 'running'

    async function inspect(){
        setProblem('')

        try {
            const found = await call('firmware_inspect', {path})
            setImage(found)
            return found
        }
        catch(failure) {
            setImage(null)
            setProblem(String(failure))
            return null
        }
    }

    useEffect(() => {
        if(path)
            inspect()
    }, [path])

    async function choose(){
        const chosen = await open({defaultPath: path || undefined, filters: FILTERS, title: 'Firmware do MRU (Main.ino.bin)'})

        if(chosen)
            setSettings({firmware: chosen})
    }

    async function handleSend(){
        const found = await inspect()    // O ARQUIVO PODE TER SIDO RECOMPILADO DESDE QUE A TELA ABRIU

        if(!found)
            return

        const older = compareVersions(found.version, link.firmware) < 0

        if(older && !await ask('Voltar para uma versão mais antiga', `O MRU está no ${link.firmware} e este arquivo é o ${found.version}. Quer mesmo voltar?`, 'Enviar assim mesmo'))
            return

        await updateFirmware(found)
    }

    const tiles = [
        ['No arquivo', image ? image.version ?? '?' : '—'],
        ['No MRU', link.firmware ?? '—'],
        ['Tamanho', image ? formatBytes(image.size) : '—'],
        ['Compilado', image ? new Date(image.modified * 1000).toLocaleString('pt-BR', {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'}) : '—'],
        ['Tempo', image ? `~${formatDuration(eta)}` : '—']
    ]

    const notices = [
        problem && ['bad', problem],
        !path && ['warn', 'Escolha o arquivo Main.ino.bin.'],
        recording && ['bad', 'Existe uma gravação em andamento: pare antes de atualizar.'],
        image?.outdated && ['warn', 'O código do firmware é mais novo que este arquivo: compile de novo, ou o MRU recebe a versão anterior ao que foi mexido.'],
        image && order < 0 && ['warn', `Este arquivo é mais antigo que o firmware do MRU (${link.firmware}).`],
        image && order == 0 && ['info', `O MRU já está no ${link.firmware}: enviar só regrava a mesma versão.`],
        image && order > 0 && ['ok', `Atualiza do ${link.firmware} para o ${image.version}.`],
        image && eta > SLOW && ['warn', `A ${link.baud} bps leva ~${formatDuration(eta)}. Pelo USB ou num baud maior é bem mais rápido.`],
        image && !synced && !order && ['info', 'O botão conecta ao MRU antes de enviar.']
    ].filter(Boolean).slice(0, 2)

    return (
        <div className='FirmwarePanel'>
            <div className='Field'>
                <span className='Label'>Arquivo do firmware</span>

                <div className='Row'>
                    <input className='Input mono Grow' value={path} title={path} placeholder='caminho do Main.ino.bin' onChange={event => setSettings({firmware: event.target.value})}/>
                    <AsyncButton text='Escolher…' variant='light' onClick={choose}/>
                    {settings.firmware && settings.firmware != defaults?.firmware && <AsyncButton text='Padrão' variant='ghost' onClick={() => setSettings({firmware: defaults?.firmware})}/>}
                </div>
            </div>

            <div className='FirmwareTiles'>
                {tiles.map(([label, value]) => <div key={label} className='MruTile'><span>{label}</span><b title={value}>{value}</b></div>)}
            </div>

            <div className='FirmwareSend'>
                <div className='FirmwareNotices'>
                    {notices.length == 0 && <div className='Notice'>O MRU confere cada bloco e a imagem inteira antes de trocar de firmware. Se algo falhar, o atual continua.</div>}
                    {notices.map(([tone, text]) => <div key={text} className={`Notice ${tone}`}>{text}</div>)}
                </div>

                <AsyncButton text={synced ? 'Enviar ao MRU' : 'Conectar e enviar'} large disabled={!image || recording || running} onClick={handleSend}/>
            </div>

            {confirmation}

            {running && (
                <Overlay title={`Atualizando o firmware${update.image?.version ? ` para o ${update.image.version}` : ''}`} stage={update.stage} stages={STAGES} message={update.message} progress={update.steps ? update.step / update.steps : null} started={update.started} log={update.log}>
                    <div className='Muted FirmwareWarning'>Não desligue o MRU nem tire o cabo. Se a transferência falhar, o firmware atual continua rodando.</div>
                    {CANCEL.includes(update.stage) && <AsyncButton text='Cancelar' variant='light' onClick={cancelUpdate}/>}
                </Overlay>
            )}

            {update && !running && (
                <Dialog title={update.status == 'done' ? 'Firmware atualizado' : update.status == 'cancelled' ? 'Atualização cancelada' : 'A atualização falhou'} tone={update.status == 'error' ? 'bad' : ''} onClose={() => setUpdate(null)} actions={<>{update.status != 'done' && <AsyncButton small variant='light' text='Tentar de novo' onClick={handleSend}/>}<AsyncButton small text='Fechar' onClick={() => setUpdate(null)}/></>}>
                    {update.error && <div className='Notice bad' style={{marginBottom: '.7rem'}}>{update.error}</div>}

                    <div className='Facts wide'>
                        <span>Antes</span><b>{update.before ?? '?'}</b>
                        <span>Agora</span><b>{update.after ?? '?'}</b>
                        {update.result && <><span>Envio</span><b>{formatBytes(update.result.bytes)} em {formatDuration(update.result.seconds)}</b></>}
                        {update.result && <><span>Blocos repetidos</span><b>{update.result.retries}</b></>}
                        {update.result?.protocol == 1 && <><span>Protocolo</span><b>antigo, sem CRC por bloco</b></>}
                    </div>

                    {update.status == 'done' && <div className='Muted' style={{marginTop: '.7rem'}}>O MRU rodou o firmware novo sem cair e o confirmou. Configurações e calibração da flash continuam as mesmas.</div>}
                    {update.status == 'error' && update.after && <div className='Muted' style={{marginTop: '.7rem'}}>O MRU continua funcionando no {update.after}.</div>}
                    {update.status == 'error' && !update.after && <div className='Muted' style={{marginTop: '.7rem'}}>O MRU não voltou a responder. Desligue e ligue; se não voltar, grave o firmware pelo USB com a IDE ou o arduino-cli.</div>}
                </Dialog>
            )}
        </div>
    )
}
