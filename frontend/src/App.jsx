import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Overview from './pages/Overview'
import CrimeMap from './pages/CrimeMap'
import Hotspots from './pages/Hotspots'
import Predictions from './pages/Predictions'
import Forecast from './pages/Forecast'
import ModelInsights from './pages/ModelInsights'
import DataExplorer from './pages/DataExplorer'
import SystemPage from './pages/SystemPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route element={<Layout />}>
          <Route path="/overview" element={<Overview />} />
          <Route path="/map" element={<CrimeMap />} />
          <Route path="/hotspots" element={<Hotspots />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/forecast" element={<Forecast />} />
          <Route path="/insights" element={<ModelInsights />} />
          <Route path="/explorer" element={<DataExplorer />} />
          <Route path="/system" element={<SystemPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
