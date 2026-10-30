import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { call, getStored, setStored, useInterval } from '../utils'

const GlobalContext = createContext(undefined)


export function useGlobalContext(){
    const context = useContext(GlobalContext)

    if(!context)
        throw new Error('useGlobalContext precisa estar dentro de um GlobalProvider')

    return context
}

// PREFERÊNCIAS DO APP: PASTAS DE SESSÕES E CALIBRAÇÕES, PYTHON DO PIPELINE E O QUE A ÚLTIMA SESSÃO DEIXOU PARA A PRÓXIMA TELA
export function GlobalProvider({children}){
    const [settings, setSettingsState] = useState(getStored('settings', {}))
    const [defaults, setDefaults]      = useState(null)
    const [python, setPython]          = useState(null)
    const [selection, setSelection]    = useState({session: null, calibration: null})
    const [jobs, setJobs]              = useState({})
    const running                      = useRef({})

    useInterval(async () => {
        for(const [kind, id] of Object.entries(running.current)){
            const state = await call('job_status', {id}).catch(() => null)

            if(!state)
                continue

            setJobs(current => ({...current, [kind]: state}))

            if(state.status != 'running')
                delete running.current[kind]

            if(kind == 'environment' && state.status == 'done')
                setSettings({python: state.result.python})
        }
    }, 500)

    useEffect(() => {
        call('app_defaults').then(values => {
            setDefaults(values)
            setSettingsState(current => ({sessions: values.sessions, calibrations: values.calibrations, python: values.pythons[0] ?? 'python3', ending: '\r\n', ...current}))
        })
    }, [])

    useEffect(() => {
        if(!settings.python || jobs.environment?.status == 'running')
            return

        setPython(null)
        call('python_check', {python: settings.python}).then(setPython)
    }, [settings.python, jobs.environment?.status])

    function setSettings(changes){
        setSettingsState(current => {
            const next = {...current, ...changes}
            setStored('settings', next)
            return next
        })
    }

    function track(kind, id){
        running.current[kind] = id
        setJobs(current => ({...current, [kind]: {id, kind, status: 'running', stage: '', message: 'iniciando...', step: 0, steps: 0, log: [], started: Date.now() / 1000}}))
        return id
    }

    // UM SCRIPT DO APP (Pipeline OU Pipeline/Session) NO PYTHON ESCOLHIDO, RODANDO NA PASTA DELE
    async function startJob(kind, script, args){
        const folder = `${defaults.base}/${script.split('/').slice(0, -1).join('/')}`
        const id     = await call('job_start', {kind, python: settings.python, script: `${defaults.base}/${script}`, args, cwd: folder})
        return track(kind, id)
    }

    // O uv BAIXA UM PYTHON PRÓPRIO E OS MÓDULOS DO PIPELINE PARA A PASTA DO APP; NO FIM O APP PASSA A USAR ESSE PYTHON
    async function installPython(){
        return track('environment', await call('python_install'))
    }

    function cancelJob(kind){
        const id = jobs[kind]?.id

        if(id)
            call('job_cancel', {id})
    }

    function clearJob(kind){
        setJobs(current => ({...current, [kind]: null}))
    }

    const ready = Boolean(defaults)
    const value = {settings, setSettings, defaults, python, ready, selection, setSelection, jobs, startJob, installPython, cancelJob, clearJob}
    return (
        <GlobalContext.Provider value={value}>
            {children}
        </GlobalContext.Provider>
    )
}
