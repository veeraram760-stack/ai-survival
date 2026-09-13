import { useState, useEffect } from 'react'

interface AgentSummary {
  id: string
  agent_type: string
  parent_id?: string
  generation: number
  status: string
  strategy: string
  budget: number
  revenue: number
  expenses: number
  profit: number
  roi: number
  success_rate: number
  days_alive: number
}

export default function Agents({ apiBase }: { apiBase: string }) {
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/agents`)
      .then(r => r.json())
      .then(setAgents)
      .finally(() => setLoading(false))
  }, [apiBase])

  if (loading) return <div style={{ padding: 24 }}>Loading agents...</div>

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: '#00ff88', marginBottom: 16 }}>Agents</h1>
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2a35', textAlign: 'left', background: '#0d0d14' }}>
              <th style={{ padding: 12 }}>ID</th>
              <th style={{ padding: 12 }}>Type</th>
              <th style={{ padding: 12 }}>Generation</th>
              <th style={{ padding: 12 }}>Strategy</th>
              <th style={{ padding: 12 }}>Status</th>
              <th style={{ padding: 12 }}>Profit</th>
              <th style={{ padding: 12 }}>ROI</th>
              <th style={{ padding: 12 }}>Success</th>
              <th style={{ padding: 12 }}>Days</th>
            </tr>
          </thead>
          <tbody>
            {agents.map(a => (
              <tr key={a.id} style={{ borderBottom: '1px solid #1a1a22' }}>
                <td style={{ padding: 12, color: '#00ff88' }}>{a.id}</td>
                <td style={{ padding: 12 }}>{a.agent_type}</td>
                <td style={{ padding: 12 }}>{a.generation}</td>
                <td style={{ padding: 12 }}>{a.strategy}</td>
                <td style={{ padding: 12 }}>{a.status}</td>
                <td style={{ padding: 12, color: a.profit >= 0 ? '#00ff88' : '#ff4444' }}>${a.profit.toFixed(2)}</td>
                <td style={{ padding: 12 }}>{a.roi.toFixed(2)}</td>
                <td style={{ padding: 12 }}>{(a.success_rate * 100).toFixed(0)}%</td>
                <td style={{ padding: 12 }}>{a.days_alive}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
