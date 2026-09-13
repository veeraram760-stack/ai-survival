import { useState, useEffect } from 'react'

interface Experiment {
  id: string
  agent_id: string
  hypothesis: string
  budget: number
  status: string
  actual_result?: number
  conclusion?: string
  created_at: string
}

export default function Experiments({ apiBase }: { apiBase: string }) {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/experiments?limit=100`)
      .then(r => r.json())
      .then(setExperiments)
      .finally(() => setLoading(false))
  }, [apiBase])

  if (loading) return <div style={{ padding: 24 }}>Loading experiments...</div>

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: '#00ff88', marginBottom: 16 }}>Experiments</h1>
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2a35', textAlign: 'left', background: '#0d0d14' }}>
              <th style={{ padding: 12 }}>ID</th>
              <th style={{ padding: 12 }}>Agent</th>
              <th style={{ padding: 12 }}>Hypothesis</th>
              <th style={{ padding: 12 }}>Budget</th>
              <th style={{ padding: 12 }}>Result</th>
              <th style={{ padding: 12 }}>Status</th>
              <th style={{ padding: 12 }}>Conclusion</th>
              <th style={{ padding: 12 }}>Created</th>
            </tr>
          </thead>
          <tbody>
            {experiments.map(e => (
              <tr key={e.id} style={{ borderBottom: '1px solid #1a1a22' }}>
                <td style={{ padding: 12, color: '#00ff88' }}>{e.id.slice(0, 8)}</td>
                <td style={{ padding: 12 }}>{e.agent_id.slice(0, 12)}</td>
                <td style={{ padding: 12, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.hypothesis}</td>
                <td style={{ padding: 12 }}>${e.budget.toFixed(2)}</td>
                <td style={{ padding: 12, color: e.actual_result && e.actual_result > e.budget ? '#00ff88' : e.actual_result ? '#ff4444' : '-'}}>
                  {e.actual_result ? `$${e.actual_result.toFixed(2)}` : '-'}
                </td>
                <td style={{ padding: 12 }}>{e.status}</td>
                <td style={{ padding: 12 }}>{e.conclusion || '-'}</td>
                <td style={{ padding: 12 }}>{new Date(e.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
