import { GlobalProvider } from './contexts/GlobalContext';
import WifiMonitorPage from './pages/WifiMontor';
import WireMonitorPage from './pages/WireMonitor';
import { BrowserRouter, Routes, Route } from 'react-router-dom';


export function AppRoutes(){
    return (
        <BrowserRouter>
            <Routes>
                <Route path='/'               element={<WireMonitorPage/>}/>
                <Route path='/Wire'           element={<WireMonitorPage/>}/>
                <Route path='/Wifi'           element={<WifiMonitorPage/>}/>
            </Routes>
        </BrowserRouter>
    )
}


export default function App() {
  return (
    <GlobalProvider>
      <div className='App'>
        <AppRoutes/>
      </div>
    </GlobalProvider>
  )
}

