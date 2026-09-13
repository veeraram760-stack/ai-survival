import { useState, useEffect } from 'react'

interface Decision {
  id: string
  agent_id?: string
  decision_type: string
  approval_status: string
  risk_assessment?: string
  executed_at?: string
  created_at: string
}

export default function Decisions({ apiBase }: { apiBase: string }) {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/decisions?limit=100`)
      .then(r => r.json())
      .then(setDecisions)
      .finally(() => setLoading(false))
  }, [apiBase])

  if (loading) return <div style={{ padding: 24 }}>Loading decisions...</div>

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: '#00ff88', marginBottom: 16 }}>Decision Log</h1>
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2a35', textAlign: 'left', background: '#0d0d14' }}>
              <th style={{ padding: 12 }}>ID</th>
              <th style={{ padding: 12 }}>Agent</th>
              <th style={{ padding: 12 }}>Type</th>
              <th style={{ padding: 12 }}>Status</th>
              <th style={{ padding: 12 }}>Risk Assessment</th>
              <th style={{ padding: 12 }}>Executed</th>
              <th style={{ padding: 12 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {decisions.map(d => (
              <tr key={d.id} style={{ borderBottom: '1px solid #1a1a22' }}>
                <td style={{ padding: 12, color: '#00ff88' }}>{d.id.slice(0, 8)}</td>
                <td style={{ padding: 12 }}>{d.agent_id?.slice(0, 12) || 'SYSTEM'}</td>
                <td style={{ padding: 12 }}>{d.decision_type}</td>
                <td style={{ padding: 12, color: d.approval_status === 'APPROVED' ? '#00ff88' : d.approval_status === 'DENIED' ? '#ff4444' : '#ffaa00' }}>{d.approval_status}</td>
                <td style={{ padding: 12 }}>{d.risk_assessment || '-'}</td>
                <td style={{ padding: 12 }}>{d.executed_at ? new Date(d.executed_at).toLocaleString() : '-'}</td>
                <td style={{ padding: 12 }}>{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
