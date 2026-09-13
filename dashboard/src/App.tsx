import { Routes, Route, Link } from 'react-router-dom'
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
    <div style={{ minHeight: '100vh', background: '#0a0a0f' }}>
      <nav style={{ background: '#111118', borderBottom: '1px solid #2a2a35', padding: '12px 24px', display: 'flex', gap: '24px', alignItems: 'center' }}>
        <Link to="/" style={{ color: '#00ff88', textDecoration: 'none', fontWeight: 'bold', fontSize: '18px' }}>
          AI SURVIVAL
        </Link>
        <div style={{ display: 'flex', gap: '16px' }}>
          <Link to="/" style={{ color: '#aaa', textDecoration: 'none' }}>Dashboard</Link>
          <Link to="/revenue" style={{ color: '#00ff88', textDecoration: 'none', fontWeight: 'bold' }}>Revenue</Link>
          <Link to="/agents" style={{ color: '#aaa', textDecoration: 'none' }}>Agents</Link>
          <Link to="/self-improve" style={{ color: '#aaa', textDecoration: 'none' }}>Self-Improve</Link>
          <Link to="/hierarchy" style={{ color: '#aaa', textDecoration: 'none' }}>Hierarchy</Link>
          <Link to="/transactions" style={{ color: '#aaa', textDecoration: 'none' }}>Transactions</Link>
          <Link to="/decisions" style={{ color: '#aaa', textDecoration: 'none' }}>Decisions</Link>
          <Link to="/experiments" style={{ color: '#aaa', textDecoration: 'none' }}>Experiments</Link>
          <Link to="/affiliate" style={{ color: '#aaa', textDecoration: 'none' }}>Affiliate</Link>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard apiBase={API_BASE} />} />
        <Route path="/revenue" element={<Revenue apiBase={API_BASE} />} />
        <Route path="/agents" element={<Agents apiBase={API_BASE} />} />
        <Route path="/self-improve" element={<SelfImproving apiBase={API_BASE} />} />
        <Route path="/hierarchy" element={<Hierarchy apiBase={API_BASE} />} />
        <Route path="/transactions" element={<Transactions apiBase={API_BASE} />} />
        <Route path="/decisions" element={<Decisions apiBase={API_BASE} />} />
        <Route path="/experiments" element={<Experiments apiBase={API_BASE} />} />
        <Route path="/affiliate" element={<Affiliate apiBase={API_BASE} />} />
      </Routes>
    </div>
  )
}

export default App
