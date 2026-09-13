import { useState, useEffect } from 'react'

interface SelfImprovingAgent {
  id: string
  agent_type: string
  level: string
  strategy: string
  status: string
  improvement_cycle: number
  improvements_applied: number
  improvements_failed: number
  auto_improve_enabled: boolean
  known_weaknesses: string[]
  known_strengths: string[]
  roi: number
  success_rate: number
  lifetime_profit: number
}

interface ImprovementCycle {
  id: string
  agent_id: string
  cycle: number
  status: string
  started_at: string
  completed_at: string | null
  weaknesses_found: any[]
  improvements_applied: number
  improvements_failed: number
}

export default function SelfImproving({ apiBase }: { apiBase: string }) {
  const [agents, setAgents] = useState<SelfImprovingAgent[]>([])
  const [history, setHistory] = useState<ImprovementCycle[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/self-improve/agents`)
      .then(r => r.json())
      .then(data => setAgents(data.agents || []))
      .finally(() => setLoading(false))
  }, [apiBase])

  const loadHistory = (agentId: string) => {
    fetch(`${apiBase}/self-improve/history?agent_id=${agentId}`)
      .then(r => r.json())
      .then(data => setHistory(data))
  }

  const triggerCycle = () => {
    fetch(`${apiBase}/self-improve/cycle`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (data.self_improvement) {
          const si = data.self_improvement
          if (si.agent_id) loadHistory(si.agent_id)
        }
      })
  }

  if (loading) return <div style={{ padding: 24 }}>Loading self-improving agents...</div>

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: '#00ff88', marginBottom: 16 }}>Self-Improving Agents</h1>
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <button
          onClick={triggerCycle}
          style={{
            padding: '8px 16px',
            background: '#00ff88',
            color: '#000',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          Trigger Improvement Cycle
        </button>
      </div>

      {agents.length === 0 && <p style={{ color: '#888' }}>No self-improving agents found</p>}

      {agents.map(agent => (
        <div key={agent.id} style={{
          background: '#111118',
          border: '1px solid #2a2a35',
          borderRadius: 8,
          padding: 20,
          marginBottom: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ color: '#00ff88', margin: 0, fontSize: 16 }}>
              {agent.id}
              <span style={{ color: '#888', fontSize: 13, marginLeft: 8 }}>
                [{agent.level}] {agent.agent_type}
              </span>
            </h2>
            <span style={{
              padding: '4px 8px',
              background: agent.auto_improve_enabled ? '#00ff8833' : '#ff444433',
              color: agent.auto_improve_enabled ? '#00ff88' : '#ff4444',
              borderRadius: 4,
              fontSize: 12,
            }}>
              {agent.auto_improve_enabled ? 'AUTO-IMPROVE ON' : 'AUTO-IMPROVE OFF'}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 12 }}>
            <div style={{ background: '#0d0d14', padding: 12, borderRadius: 4 }}>
              <div style={{ color: '#888', fontSize: 12 }}>Cycle</div>
              <div style={{ color: '#fff', fontSize: 18 }}>{agent.improvement_cycle}</div>
            </div>
            <div style={{ background: '#0d0d14', padding: 12, borderRadius: 4 }}>
              <div style={{ color: '#888', fontSize: 12 }}>Applied</div>
              <div style={{ color: '#00ff88', fontSize: 18 }}>{agent.improvements_applied}</div>
            </div>
            <div style={{ background: '#0d0d14', padding: 12, borderRadius: 4 }}>
              <div style={{ color: '#888', fontSize: 12 }}>Failed</div>
              <div style={{ color: '#ff4444', fontSize: 18 }}>{agent.improvements_failed}</div>
            </div>
            <div style={{ background: '#0d0d14', padding: 12, borderRadius: 4 }}>
              <div style={{ color: '#888', fontSize: 12 }}>ROI</div>
              <div style={{ color: agent.roi >= 0 ? '#00ff88' : '#ff4444', fontSize: 18 }}>{agent.roi.toFixed(2)}</div>
            </div>
          </div>

          {agent.known_weaknesses.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ color: '#ff4444', fontSize: 12, marginBottom: 4 }}>Weaknesses:</div>
              {agent.known_weaknesses.map((w, i) => (
                <span key={i} style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  margin: '2px',
                  background: '#ff444422',
                  borderRadius: 4,
                  fontSize: 12,
                  color: '#ff4444',
                }}>
                  {w}
                </span>
              ))}
            </div>
          )}

          {agent.known_strengths.length > 0 && (
            <div>
              <div style={{ color: '#00ff88', fontSize: 12, marginBottom: 4 }}>Strengths:</div>
              {agent.known_strengths.map((s, i) => (
                <span key={i} style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  margin: '2px',
                  background: '#00ff8822',
                  borderRadius: 4,
                  fontSize: 12,
                  color: '#00ff88',
                }}>
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}

      {history.length > 0 && (
        <div style={{
          background: '#111118',
          border: '1px solid #2a2a35',
          borderRadius: 8,
          padding: 20,
          marginTop: 16,
        }}>
          <h3 style={{ color: '#00ff88', marginBottom: 12 }}>Improvement History</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2a2a35', textAlign: 'left', background: '#0d0d14' }}>
                <th style={{ padding: 12 }}>Cycle</th>
                <th style={{ padding: 12 }}>Status</th>
                <th style={{ padding: 12 }}>Applied</th>
                <th style={{ padding: 12 }}>Failed</th>
                <th style={{ padding: 12 }}>Started</th>
                <th style={{ padding: 12 }}>Completed</th>
              </tr>
            </thead>
            <tbody>
              {history.map(h => (
                <tr key={h.id} style={{ borderBottom: '1px solid #1a1a22' }}>
                  <td style={{ padding: 12, color: '#00ff88' }}>{h.cycle}</td>
                  <td style={{ padding: 12 }}>{h.status}</td>
                  <td style={{ padding: 12, color: '#00ff88' }}>{h.improvements_applied}</td>
                  <td style={{ padding: 12, color: '#ff4444' }}>{h.improvements_failed}</td>
                  <td style={{ padding: 12 }}>{h.started_at ? new Date(h.started_at).toLocaleString() : '-'}</td>
                  <td style={{ padding: 12 }}>{h.completed_at ? new Date(h.completed_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
