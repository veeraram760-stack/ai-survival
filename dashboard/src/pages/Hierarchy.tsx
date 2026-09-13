import { useEffect, useState } from 'react'

interface Agent {
  id: string
  agent_type: string
  level: string
  department?: string
  status: string
  strategy: string
  supervisor_id?: string
  specialist_count?: number
  specialists?: Agent[]
}

interface HierarchyData {
  supervisors: Agent[]
  specialists: Agent[]
}

export default function Hierarchy({ apiBase }: { apiBase: string }) {
  const [data, setData] = useState<HierarchyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${apiBase}/hierarchy`)
      .then(r => r.json())
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [apiBase])

  if (loading) return <div style={{ padding: 24, color: '#aaa' }}>Loading hierarchy...</div>
  if (error) return <div style={{ padding: 24, color: '#ff4444' }}>Error: {error}</div>

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: '#fff', marginBottom: 24 }}>Agent Hierarchy</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
        {data?.supervisors.map(sup => (
          <div key={sup.id} style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h2 style={{ color: '#00ff88', margin: 0, fontSize: 16 }}>{sup.department || sup.agent_type}</h2>
              <span style={{ background: sup.status === 'TESTING' ? '#ffaa00' : '#00ff88', color: '#000', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>
                {sup.level}
              </span>
            </div>
            <div style={{ color: '#aaa', fontSize: 13, marginBottom: 4 }}>ID: {sup.id}</div>
            <div style={{ color: '#aaa', fontSize: 13, marginBottom: 4 }}>Strategy: {sup.strategy}</div>
            <div style={{ color: '#aaa', fontSize: 13, marginBottom: 12 }}>Specialists: {sup.specialist_count || sup.specialists?.length || 0}</div>
            {sup.specialists && sup.specialists.length > 0 && (
              <div style={{ borderTop: '1px solid #2a2a35', paddingTop: 12 }}>
                {sup.specialists.map(spec => (
                  <div key={spec.id} style={{ background: '#0a0a0f', border: '1px solid #1a1a25', borderRadius: 4, padding: '8px 12px', marginBottom: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#fff', fontSize: 14 }}>{spec.agent_type}</span>
                      <span style={{ background: spec.status === 'TESTING' ? '#ffaa00' : '#00ff88', color: '#000', padding: '2px 6px', borderRadius: 3, fontSize: 11 }}>
                        {spec.status}
                      </span>
                    </div>
                    <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>{spec.strategy}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {data?.specialists && data.specialists.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h2 style={{ color: '#fff', marginBottom: 12 }}>Unassigned Specialists</h2>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {data.specialists.map(spec => (
              <div key={spec.id} style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 4, padding: '8px 12px' }}>
                <span style={{ color: '#fff' }}>{spec.agent_type}</span>
                <span style={{ color: '#666', marginLeft: 8 }}>{spec.id.slice(0, 12)}...</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
