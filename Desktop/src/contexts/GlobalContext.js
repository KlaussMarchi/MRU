import React, { createContext, useState, useContext } from 'react';

const GlobalContext = createContext(undefined);

export function useGlobalContext() {
    const context = useContext(GlobalContext);

    if (!context)
        throw new Error("useGlobal deve ser usado dentro de um GlobalProvider")
    
    return context;
}

export function GlobalProvider({ children }) {
    const [globalOptions, setGlobalOptions] = useState({
        activePage: 'home',
        portName: 'None',
        serialConnected: false,
    })

    const [devices, setDevices] = useState([])
    const [rows, setRows] = useState([])

    return (
        <GlobalContext.Provider value={{ globalOptions, setGlobalOptions, devices, setDevices, rows, setRows }}>
            {children}
        </GlobalContext.Provider>
    );
}
