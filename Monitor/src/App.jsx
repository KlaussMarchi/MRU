import { HashRouter, Routes, Route } from 'react-router-dom'
import { GlobalProvider } from './contexts/GlobalContext'
import { DeviceProvider } from './contexts/DeviceContext'
import SideBar from './components/SideBar'
import HomePage from './pages/Home'
import MonitorPage from './pages/Monitor'
import AcquisitionPage from './pages/Acquisition'
import CalibrationPage from './pages/Calibration'
import ProductionPage from './pages/Production'
import DevicePage from './pages/Device'
import SettingsPage from './pages/Settings'
import HMSPage from './pages/HMS'


export default function App(){
    return (
        <GlobalProvider>
            <DeviceProvider>
                <HashRouter>
                    <div className='MainContainer'>
                        <SideBar/>

                        <Routes>
                            <Route path='/'            element={<HomePage/>}/>
                            <Route path='/Monitor'     element={<MonitorPage/>}/>
                            <Route path='/Acquisition' element={<AcquisitionPage/>}/>
                            <Route path='/Calibration' element={<CalibrationPage/>}/>
                            <Route path='/Production'  element={<ProductionPage/>}/>
                            <Route path='/Device'      element={<DevicePage/>}/>
                            <Route path='/Settings'    element={<SettingsPage/>}/>
                            <Route path='/HMS'         element={<HMSPage/>}/>
                        </Routes>
                    </div>
                </HashRouter>
            </DeviceProvider>
        </GlobalProvider>
    )
}
