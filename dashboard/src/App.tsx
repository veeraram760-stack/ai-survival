import { Routes, Route } from 'react-router-dom'
import CommandCenterV2 from './components/v2/CommandCenterV2'
import Commands from './components/panels/CommandCenter'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Transactions from './pages/Transactions'
import Decisions from './pages/Decisions'
import Experiments from './pages/Experiments'
import Affiliate from './pages/Affiliate'
import Hierarchy from './pages/Hierarchy'
import SelfImproving from './pages/SelfImproving'
import Revenue from './pages/Revenue'

const API_BASE = (import.meta as any).env.PROD ? '/api/v1' : 'http://localhost:8000/api/v1'

function App() {
  return (
    <Routes>
      <Route path="/" element={<CommandCenterV2 />} />
      <Route path="/legacy" element={<Commands />} />
      <Route path="/revenue" element={<Revenue apiBase={API_BASE} />} />
      <Route path="/agents" element={<Agents apiBase={API_BASE} />} />
      <Route path="/self-improve" element={<SelfImproving apiBase={API_BASE} />} />
      <Route path="/hierarchy" element={<Hierarchy apiBase={API_BASE} />} />
      <Route path="/transactions" element={<Transactions apiBase={API_BASE} />} />
      <Route path="/decisions" element={<Decisions apiBase={API_BASE} />} />
      <Route path="/experiments" element={<Experiments apiBase={API_BASE} />} />
      <Route path="/affiliate" element={<Affiliate apiBase={API_BASE} />} />
      <Route path="/dashboard" element={<Dashboard apiBase={API_BASE} />} />
    </Routes>
  )
}

export default App
