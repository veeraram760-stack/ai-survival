import { useState, useEffect } from 'react'

interface Transaction {
  id: string
  timestamp: string
  agent_id?: string
  category: string
  action: string
  amount: number
  balance_before: number
  balance_after: number
  status: string
  risk_level: string
}

export default function Transactions({ apiBase }: { apiBase: string }) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/transactions?limit=100`)
      .then(r => r.json())
      .then(setTransactions)
      .finally(() => setLoading(false))
  }, [apiBase])

  if (loading) return <div style={{ padding: 24 }}>Loading transactions...</div>

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ color: '#00ff88', marginBottom: 16 }}>Transactions</h1>
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #2a2a35', textAlign: 'left', background: '#0d0d14' }}>
              <th style={{ padding: 12 }}>ID</th>
              <th style={{ padding: 12 }}>Time</th>
              <th style={{ padding: 12 }}>Agent</th>
              <th style={{ padding: 12 }}>Category</th>
              <th style={{ padding: 12 }}>Action</th>
              <th style={{ padding: 12 }}>Amount</th>
              <th style={{ padding: 12 }}>Balance After</th>
              <th style={{ padding: 12 }}>Status</th>
              <th style={{ padding: 12 }}>Risk</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map(t => (
              <tr key={t.id} style={{ borderBottom: '1px solid #1a1a22' }}>
                <td style={{ padding: 12, color: '#00ff88' }}>{t.id.slice(0, 8)}</td>
                <td style={{ padding: 12 }}>{new Date(t.timestamp).toLocaleString()}</td>
                <td style={{ padding: 12 }}>{t.agent_id?.slice(0, 12) || 'SYSTEM'}</td>
                <td style={{ padding: 12 }}>{t.category}</td>
                <td style={{ padding: 12 }}>{t.action}</td>
                <td style={{ padding: 12, color: t.amount >= 0 ? '#00ff88' : '#ff4444' }}>${t.amount.toFixed(2)}</td>
                <td style={{ padding: 12 }}>${t.balance_after.toFixed(2)}</td>
                <td style={{ padding: 12 }}>{t.status}</td>
                <td style={{ padding: 12 }}>{t.risk_level}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
