import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'

interface CapitalSnapshot {
  total_capital: number
  survival_reserve: number
  operating_capital: number
  growth_capital: number
  total_revenue: number
  total_expenses: number
  net_profit: number
  roi: number
  real_revenue: number
  real_expenses: number
  simulated_revenue: number
  simulated_expenses: number
}

interface AgentSummary {
  id: string
  agent_type: string
  strategy?: string
  status: string
  revenue: number
  expenses: number
  profit: number
  roi: number
  success_rate: number
  days_alive: number
  experiments_count: number
}

interface SystemState {
  current_mode: string
  total_agents: number
  active_agents: number
}

interface WithdrawalStatus {
  threshold: number
  real_revenue: number
  remaining_to_threshold: number
  eligible: boolean
  pending_withdrawals: number
}

export default function Dashboard({ apiBase }: { apiBase: string }) {
  const [capital, setCapital] = useState<CapitalSnapshot | null>(null)
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [system, setSystem] = useState<SystemState | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [withdrawal, setWithdrawal] = useState<WithdrawalStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTask, setActiveTask] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [capitalRes, agentsRes, systemRes, withdrawalRes] = await Promise.all([
          fetch(`${apiBase}/capital`),
          fetch(`${apiBase}/agents`),
          fetch(`${apiBase}/system/state`),
          fetch(`${apiBase}/withdrawal/status`),
        ])
        const capitalData = await capitalRes.json()
        const agentsData = await agentsRes.json()
        const systemData = await systemRes.json()
        const withdrawalData = await withdrawalRes.json()
        setCapital(capitalData)
        setAgents(agentsData)
        setSystem(systemData)
        setWithdrawal(withdrawalData)

        setHistory(prev => [
          ...prev.slice(-29),
          { time: new Date().toLocaleTimeString(), capital: capitalData.total_capital || 0, real: capitalData.real_revenue || 0 },
        ])
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [apiBase])

  const triggerTask = async (agentId: string, taskType: string) => {
    setActiveTask(`${agentId}-${taskType}`)
    try {
      await fetch(`${apiBase}/agents/${agentId}/tasks?task_type=${taskType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: 'https://httpbin.org/post' }),
      })
    } catch (e) {
      console.error(e)
    } finally {
      setTimeout(() => setActiveTask(null), 2000)
    }
  }

  if (loading) return <div style={{ padding: 24, color: '#00ff88' }}>Loading...</div>

  const alive = agents.filter(a => a.status === 'ALIVE').length
  const testing = agents.filter(a => a.status === 'TESTING').length
  const growing = agents.filter(a => a.status === 'GROWING').length
  const dead = agents.filter(a => ['TERMINATED', 'FAILED'].includes(a.status)).length

  const agentChartData = agents.map(a => ({
    id: a.id,
    revenue: Number(a.revenue.toFixed(2)),
    expenses: Number(a.expenses.toFixed(2)),
    profit: Number(a.profit.toFixed(2)),
  }))

  const statusColor = (status: string) => {
    if (status === 'ALIVE' || status === 'GROWING') return '#00ff88'
    if (status === 'TESTING') return '#ffaa00'
    if (status === 'PAUSED') return '#888'
    return '#ff4444'
  }

  return (
    <div style={{ padding: 24, maxWidth: 1600, margin: '0 auto', background: '#0a0a0f', minHeight: '100vh', color: '#e0e0e0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ color: '#00ff88', marginBottom: 4, fontSize: 32 }}>AI SURVIVAL</h1>
          <p style={{ color: '#888', margin: 0 }}>Autonomous Multi-Agent AI Business System</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 12 }}>SYSTEM MODE</div>
            <div style={{ color: system?.current_mode === 'GROWTH' ? '#00ff88' : '#ffaa00', fontSize: 20, fontWeight: 'bold' }}>{system?.current_mode || 'UNKNOWN'}</div>
          </div>
          <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 12 }}>WITHDRAWAL</div>
            <div style={{ color: withdrawal && withdrawal.eligible ? '#00ff88' : '#ffaa00', fontSize: 20, fontWeight: 'bold' }}>
              {withdrawal && withdrawal.eligible ? 'ELIGIBLE' : `$${withdrawal ? withdrawal.real_revenue.toFixed(2) : '0.00'} / $500`}
            </div>
          </div>
        </div>
      </div>

      <div style={{ background: '#1a1a00', border: '1px solid #ffaa00', borderRadius: 12, padding: 16, marginBottom: 24 }}>
        <div style={{ color: '#ffaa00', fontWeight: 'bold', marginBottom: 8 }}>⚠️ REAL MONEY STATUS</div>
        <div style={{ color: '#e0e0e0', fontSize: 14, lineHeight: 1.6 }}>
          "Real Revenue" currently reflects <strong>simulated/estimated</strong> values from tool execution because live payment integrations (affiliate commissions, sales transactions, ad payouts) are not yet connected. 
          To count as real money, a tool must verify an actual financial event — e.g., a confirmed affiliate conversion, a completed sale, or a verified payout from an ad network. 
          Until then, revenue figures are projections, not deposited funds.
        </div>
      </div>

      <div style={{ background: '#111118', border: '2px solid #00ff88', borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <h2 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16, fontSize: 22 }}>AGENT ACTIVITY</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 20 }}>
          <MetricCard label="TOTAL AGENTS" value={(system?.total_agents || 0).toString()} color="#00ff88" />
          <MetricCard label="ACTIVE AGENTS" value={`${system?.active_agents || 0}`} color="#00aaff" />
          <MetricCard label="ALIVE" value={alive.toString()} color="#00ff88" />
          <MetricCard label="TESTING" value={testing.toString()} color="#ffaa00" />
          <MetricCard label="GROWING" value={growing.toString()} color="#00aaff" />
          <MetricCard label="DEAD" value={dead.toString()} color="#ff4444" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
          {agents.map(a => (
            <div key={a.id} style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <div style={{ color: '#00ff88', fontWeight: 'bold', fontSize: 16 }}>{a.id}</div>
                  <div style={{ color: '#888', fontSize: 12 }}>{a.agent_type} • {a.strategy || 'default'} • Day {a.days_alive}</div>
                </div>
                <div style={{ background: statusColor(a.status), color: '#000', padding: '4px 10px', borderRadius: 4, fontSize: 12, fontWeight: 'bold' }}>
                  {a.status}
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
                <div>
                  <div style={{ color: '#888', fontSize: 11 }}>REVENUE</div>
                  <div style={{ color: '#00ff88', fontSize: 16 }}>${a.revenue.toFixed(2)}</div>
                </div>
                <div>
                  <div style={{ color: '#888', fontSize: 11 }}>EXPENSES</div>
                  <div style={{ color: '#ff4444', fontSize: 16 }}>${a.expenses.toFixed(2)}</div>
                </div>
                <div>
                  <div style={{ color: '#888', fontSize: 11 }}>PROFIT</div>
                  <div style={{ color: a.profit >= 0 ? '#00ff88' : '#ff4444', fontSize: 16 }}>${a.profit.toFixed(2)}</div>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12, fontSize: 12 }}>
                <div>
                  <span style={{ color: '#888' }}>ROI:</span> <span style={{ color: '#e0e0e0' }}>{a.roi.toFixed(2)}</span>
                </div>
                <div>
                  <span style={{ color: '#888' }}>Success:</span> <span style={{ color: '#e0e0e0' }}>{(a.success_rate * 100).toFixed(0)}%</span>
                </div>
                <div>
                  <span style={{ color: '#888' }}>Tasks:</span> <span style={{ color: '#e0e0e0' }}>{a.experiments_count}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  onClick={() => triggerTask(a.id, 'content_generation')}
                  disabled={activeTask === `${a.id}-content_generation`}
                  style={{
                    background: activeTask === `${a.id}-content_generation` ? '#2a2a35' : '#00ff88',
                    color: '#000',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 'bold',
                  }}
                >
                  {activeTask === `${a.id}-content_generation` ? 'RUNNING...' : 'EARN'}
                </button>
                <button
                  onClick={() => triggerTask(a.id, 'affiliate_marketing')}
                  disabled={activeTask === `${a.id}-affiliate_marketing`}
                  style={{
                    background: activeTask === `${a.id}-affiliate_marketing` ? '#2a2a35' : '#00aaff',
                    color: '#000',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 'bold',
                  }}
                >
                  {activeTask === `${a.id}-affiliate_marketing` ? 'RUNNING...' : 'AFFILIATE'}
                </button>
                <button
                  onClick={() => triggerTask(a.id, 'sales_outreach')}
                  disabled={activeTask === `${a.id}-sales_outreach`}
                  style={{
                    background: activeTask === `${a.id}-sales_outreach` ? '#2a2a35' : '#ffaa00',
                    color: '#000',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: 'bold',
                  }}
                >
                  {activeTask === `${a.id}-sales_outreach` ? 'RUNNING...' : 'SALES'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 24 }}>
        <MetricCard label="TOTAL CAPITAL" value={`$${capital?.total_capital.toFixed(2) || '0.00'}`} />
        <MetricCard label="REAL REVENUE" value={`$${capital?.real_revenue.toFixed(2) || '0.00'}`} color="#00ff88" />
        <MetricCard label="GROWTH CAPITAL" value={`$${capital?.growth_capital.toFixed(2) || '0.00'}`} color="#00aaff" />
        <MetricCard label="NET PROFIT" value={`$${capital?.net_profit.toFixed(2) || '0.00'}`} color={capital && capital.net_profit >= 0 ? '#00ff88' : '#ff4444'} />
        <MetricCard label="TOTAL EXPENSES" value={`$${capital?.total_expenses.toFixed(2) || '0.00'}`} color="#ff4444" />
        <MetricCard label="ROI" value={`${capital?.roi.toFixed(1) || '0.0'}%`} />
        <MetricCard label="REMAINING" value={`$${withdrawal ? Math.max(0, withdrawal.threshold - withdrawal.real_revenue).toFixed(2) : '500.00'}`} color="#ffaa00" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: 20 }}>
          <h3 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16 }}>Capital Equity Curve</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" />
              <XAxis dataKey="time" stroke="#666" fontSize={12} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip contentStyle={{ background: '#111118', border: '1px solid #2a2a35', color: '#e0e0e0' }} />
              <Area type="monotone" dataKey="capital" stroke="#00ff88" fill="rgba(0,255,136,0.1)" name="Total Capital" />
              <Area type="monotone" dataKey="real" stroke="#00aaff" fill="rgba(0,170,255,0.1)" name="Real Revenue" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: 20 }}>
          <h3 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16 }}>Agent Revenue vs Expenses</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={agentChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" />
              <XAxis dataKey="id" stroke="#666" fontSize={10} angle={-20} textAnchor="end" height={80} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip contentStyle={{ background: '#111118', border: '1px solid #2a2a35', color: '#e0e0e0' }} />
              <Legend />
              <Bar dataKey="revenue" fill="#00ff88" name="Revenue" />
              <Bar dataKey="expenses" fill="#ff4444" name="Expenses" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: 20 }}>
        <h3 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16 }}>Capital Breakdown</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <div style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
            <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>SURVIVAL RESERVE</div>
            <div style={{ color: '#ff4444', fontSize: 20, fontWeight: 'bold' }}>${capital?.survival_reserve.toFixed(2) || '0.00'}</div>
            <div style={{ background: '#2a2a35', height: 6, borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
              <div style={{ background: '#ff4444', height: '100%', width: `${capital ? (capital.survival_reserve / capital.total_capital) * 100 : 0}%`, borderRadius: 3 }} />
            </div>
          </div>
          <div style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
            <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>OPERATING CAPITAL</div>
            <div style={{ color: '#ffaa00', fontSize: 20, fontWeight: 'bold' }}>${capital?.operating_capital.toFixed(2) || '0.00'}</div>
            <div style={{ background: '#2a2a35', height: 6, borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
              <div style={{ background: '#ffaa00', height: '100%', width: `${capital ? (capital.operating_capital / capital.total_capital) * 100 : 0}%`, borderRadius: 3 }} />
            </div>
          </div>
          <div style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
            <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>GROWTH CAPITAL</div>
            <div style={{ color: '#00ff88', fontSize: 20, fontWeight: 'bold' }}>${capital?.growth_capital.toFixed(2) || '0.00'}</div>
            <div style={{ background: '#2a2a35', height: 6, borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
              <div style={{ background: '#00ff88', height: '100%', width: `${capital ? (capital.growth_capital / capital.total_capital) * 100 : 0}%`, borderRadius: 3 }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
      <div style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>{label}</div>
      <div style={{ color: color || '#e0e0e0', fontSize: 20, fontWeight: 'bold' }}>{value}</div>
    </div>
  )
}
