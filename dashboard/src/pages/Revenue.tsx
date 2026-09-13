import { useState, useEffect } from 'react'

interface RevenueStrategy {
  name: string
  description: string
  required_tools: string[]
  required_env: string[]
}

interface RevenueAgent {
  agent_id: string
  strategy: string
  cycles: number
  revenue: number
  expenses: number
  profit: number
  roi: number
  status: string
  consecutive_failures: number
  last_execution: string | null
}

interface RevenuePerformance {
  total_revenue: number
  total_expenses: number
  total_profit: number
  roi: number
  agent_count: number
  by_strategy: Record<string, RevenueAgent>
}

export default function Revenue({ apiBase }: { apiBase: string }) {
  const [strategies, setStrategies] = useState<Record<string, RevenueStrategy>>({})
  const [agents, setAgents] = useState<RevenueAgent[]>([])
  const [performance, setPerformance] = useState<RevenuePerformance | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeAction, setActiveAction] = useState<string | null>(null)
  const [riskTolerance, setRiskTolerance] = useState('MEDIUM')
  const [recommendation, setRecommendation] = useState<{ recommended_strategy: string; capital: number; risk_tolerance: string; available_strategies: string[] } | null>(null)
  const [recommendError, setRecommendError] = useState<string | null>(null)

  const getRecommendation = async () => {
    setActiveAction('recommend')
    setRecommendError(null)
    const capital = performance?.total_revenue ?? 50
    try {
      const res = await fetch(`${apiBase}/revenue/recommend-strategy?capital=${capital}&risk_tolerance=${riskTolerance}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setRecommendation(await res.json())
    } catch (e) {
      console.error(e)
      setRecommendError('Failed to get recommendation — is the backend running?')
    } finally {
      setTimeout(() => setActiveAction(null), 2000)
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [strategiesRes, agentsRes, performanceRes] = await Promise.all([
          fetch(`${apiBase}/revenue/strategies`),
          fetch(`${apiBase}/revenue/agents`),
          fetch(`${apiBase}/revenue/performance`),
        ])
        setStrategies(await strategiesRes.json())
        setAgents(await agentsRes.json())
        setPerformance(await performanceRes.json())
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [apiBase])

  const triggerCycle = async (agentId: string) => {
    setActiveAction(`cycle-${agentId}`)
    try {
      await fetch(`${apiBase}/revenue/agents/${agentId}/cycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
    } catch (e) {
      console.error(e)
    } finally {
      setTimeout(() => setActiveAction(null), 2000)
    }
  }

  const switchStrategy = async (agentId: string, strategy: string) => {
    setActiveAction(`switch-${agentId}`)
    try {
      await fetch(`${apiBase}/revenue/agents/${agentId}/switch-strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy_name: strategy }),
      })
    } catch (e) {
      console.error(e)
    } finally {
      setTimeout(() => setActiveAction(null), 2000)
    }
  }

  const createAgent = async (strategy: string) => {
    setActiveAction(`create-${strategy}`)
    try {
      await fetch(`${apiBase}/revenue/agents/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy_name: strategy }),
      })
    } catch (e) {
      console.error(e)
    } finally {
      setTimeout(() => setActiveAction(null), 2000)
    }
  }

  if (loading) return <div style={{ padding: 24, color: '#00ff88' }}>Loading...</div>

  const profitColor = performance && performance.total_profit >= 0 ? '#00ff88' : '#ff4444'

  return (
    <div style={{ padding: 24, maxWidth: 1600, margin: '0 auto', background: '#0a0a0f', minHeight: '100vh', color: '#e0e0e0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ color: '#00ff88', marginBottom: 4, fontSize: 32 }}>REVENUE ENGINE</h1>
          <p style={{ color: '#888', margin: 0 }}>Multi-channel revenue generation & strategy management</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 12 }}>TOTAL REVENUE</div>
            <div style={{ color: '#00ff88', fontSize: 24, fontWeight: 'bold' }}>${performance?.total_revenue.toFixed(2) || '0.00'}</div>
          </div>
          <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 12 }}>TOTAL PROFIT</div>
            <div style={{ color: profitColor, fontSize: 24, fontWeight: 'bold' }}>${performance?.total_profit.toFixed(2) || '0.00'}</div>
          </div>
          <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 8, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 12 }}>ROI</div>
            <div style={{ color: '#00aaff', fontSize: 24, fontWeight: 'bold' }}>{performance?.roi.toFixed(1) || '0.0'}%</div>
          </div>
        </div>
      </div>

      {/* Strategies Overview */}
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <h2 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16, fontSize: 22 }}>AVAILABLE STRATEGIES</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 16 }}>
          {Object.entries(strategies).map(([key, strat]) => (
            <div key={key} style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div style={{ color: '#00ff88', fontWeight: 'bold', fontSize: 16 }}>{strat.name.replace(/_/g, ' ').toUpperCase()}</div>
                  <div style={{ color: '#888', fontSize: 11, marginTop: 4 }}>{key}</div>
                </div>
                <button
                  onClick={() => createAgent(key)}
                  disabled={activeAction === `create-${key}`}
                  style={{
                    background: activeAction === `create-${key}` ? '#2a2a35' : '#00ff88',
                    color: '#000',
                    border: 'none',
                    padding: '8px 14px',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 12,
                    fontWeight: 'bold',
                  }}
                >
                  {activeAction === `create-${key}` ? 'CREATING...' : 'CREATE AGENT'}
                </button>
              </div>
              <div style={{ color: '#aaa', fontSize: 13, marginBottom: 12, lineHeight: 1.5 }}>{strat.description}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                <span style={{ color: '#888', fontSize: 11 }}>Tools:</span>
                {strat.required_tools.map((t: string) => (
                  <span key={t} style={{ background: '#1a1a2e', color: '#00aaff', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>{t}</span>
                ))}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                <span style={{ color: '#888', fontSize: 11 }}>Env:</span>
                {strat.required_env.map((e: string) => (
                  <span key={e} style={{ background: '#1a1a2e', color: '#ffaa00', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>{e}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Revenue Agents */}
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <h2 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16, fontSize: 22 }}>REVENUE AGENTS</h2>
        
        {agents.length === 0 ? (
          <div style={{ color: '#888', textAlign: 'center', padding: 40 }}>
            No revenue agents yet. Create one using the strategy cards above.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 16 }}>
            {agents.map(a => {
              const statusColor = a.status === 'ALIVE' || a.status === 'GROWING' ? '#00ff88' : 
                                  a.status === 'TESTING' ? '#ffaa00' : 
                                  a.status === 'PAUSED' ? '#888' : '#ff4444'
              
              return (
                <div key={a.agent_id} style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <div>
                      <div style={{ color: '#00ff88', fontWeight: 'bold', fontSize: 16 }}>{a.agent_id}</div>
                      <div style={{ color: '#888', fontSize: 12, marginTop: 4 }}>{a.strategy.replace(/_/g, ' ').toUpperCase()}</div>
                    </div>
                    <div style={{ background: statusColor, color: '#000', padding: '4px 10px', borderRadius: 4, fontSize: 12, fontWeight: 'bold' }}>
                      {a.status}
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
                    <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 12 }}>
                      <div style={{ color: '#888', fontSize: 11 }}>REVENUE</div>
                      <div style={{ color: '#00ff88', fontSize: 18, fontWeight: 'bold' }}>${a.revenue.toFixed(2)}</div>
                    </div>
                    <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 12 }}>
                      <div style={{ color: '#888', fontSize: 11 }}>EXPENSES</div>
                      <div style={{ color: '#ff4444', fontSize: 18, fontWeight: 'bold' }}>${a.expenses.toFixed(2)}</div>
                    </div>
                    <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 12 }}>
                      <div style={{ color: '#888', fontSize: 11 }}>PROFIT</div>
                      <div style={{ color: a.profit >= 0 ? '#00ff88' : '#ff4444', fontSize: 18, fontWeight: 'bold' }}>${a.profit.toFixed(2)}</div>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#888' }}>ROI:</span> <span style={{ color: '#e0e0e0' }}>{a.roi.toFixed(2)}</span>
                    </div>
                    <div>
                      <span style={{ color: '#888' }}>Cycles:</span> <span style={{ color: '#e0e0e0' }}>{a.cycles}</span>
                    </div>
                    <div>
                      <span style={{ color: '#888' }}>Failures:</span> <span style={{ color: a.consecutive_failures > 0 ? '#ffaa00' : '#00ff88' }}>{a.consecutive_failures}</span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      onClick={() => triggerCycle(a.agent_id)}
                      disabled={activeAction === `cycle-${a.agent_id}`}
                      style={{
                        background: activeAction === `cycle-${a.agent_id}` ? '#2a2a35' : '#00ff88',
                        color: '#000',
                        border: 'none',
                        padding: '8px 14px',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 'bold',
                        flex: 1,
                        minWidth: 100,
                      }}
                    >
                      {activeAction === `cycle-${a.agent_id}` ? 'RUNNING...' : 'RUN CYCLE'}
                    </button>
                    <select
                      value={a.strategy}
                      onChange={(e) => switchStrategy(a.agent_id, e.target.value)}
                      disabled={activeAction === `switch-${a.agent_id}`}
                      style={{
                        background: '#1a1a2e',
                        color: '#e0e0e0',
                        border: '1px solid #2a2a35',
                        padding: '8px 12px',
                        borderRadius: 6,
                        fontSize: 12,
                        flex: 1,
                        minWidth: 140,
                      }}
                    >
                      {Object.keys(strategies).map(key => (
                        <option key={key} value={key}>{key.replace(/_/g, ' ').toUpperCase()}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Performance by Strategy */}
      {performance && performance.by_strategy && Object.keys(performance.by_strategy).length > 0 && (
        <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 12, padding: 20, marginBottom: 24 }}>
          <h2 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16, fontSize: 22 }}>PERFORMANCE BY STRATEGY</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
            {Object.entries(performance.by_strategy).map(([strategy, agent]) => (
              <div key={strategy} style={{ background: '#0a0a0f', border: '1px solid #2a2a35', borderRadius: 8, padding: 16 }}>
                <div style={{ color: '#00ff88', fontWeight: 'bold', fontSize: 16, marginBottom: 12 }}>
                  {strategy.replace(/_/g, ' ').toUpperCase()}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
                  <div><span style={{ color: '#888' }}>Revenue:</span> <span style={{ color: '#00ff88' }}>${agent.revenue.toFixed(2)}</span></div>
                  <div><span style={{ color: '#888' }}>Expenses:</span> <span style={{ color: '#ff4444' }}>${agent.expenses.toFixed(2)}</span></div>
                  <div><span style={{ color: '#888' }}>Profit:</span> <span style={{ color: agent.profit >= 0 ? '#00ff88' : '#ff4444' }}>${agent.profit.toFixed(2)}</span></div>
                  <div><span style={{ color: '#888' }}>ROI:</span> <span style={{ color: '#00aaff' }}>{agent.roi.toFixed(2)}</span></div>
                  <div><span style={{ color: '#888' }}>Cycles:</span> <span style={{ color: '#e0e0e0' }}>{agent.cycles}</span></div>
                  <div><span style={{ color: '#888' }}>Status:</span> <span style={{ color: agent.status === 'GROWING' ? '#00ff88' : agent.status === 'ALIVE' ? '#00aaff' : '#ffaa00' }}>{agent.status}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategy Recommendation */}
      <div style={{ background: '#111118', border: '1px solid #2a2a35', borderRadius: 12, padding: 20 }}>
        <h2 style={{ color: '#00ff88', marginTop: 0, marginBottom: 16, fontSize: 22 }}>STRATEGY RECOMMENDATION</h2>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ background: '#1a1a2e', borderRadius: 6, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 11 }}>CURRENT CAPITAL</div>
            <div style={{ color: '#00ff88', fontSize: 18, fontWeight: 'bold' }}>${performance?.total_revenue || 50}</div>
          </div>
          <div style={{ background: '#1a1a2e', borderRadius: 6, padding: '12px 16px' }}>
            <div style={{ color: '#888', fontSize: 11 }}>RISK TOLERANCE</div>
            <select
              value={riskTolerance}
              onChange={(e) => setRiskTolerance(e.target.value)}
              style={{ background: '#0a0a0f', color: '#e0e0e0', border: '1px solid #2a2a35', padding: '8px 12px', borderRadius: 4, marginTop: 4 }}
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
            </select>
          </div>
          <button
            onClick={getRecommendation}
            disabled={activeAction === 'recommend'}
            style={{
              background: activeAction === 'recommend' ? '#2a2a35' : '#00ff88',
              color: '#000',
              border: 'none',
              padding: '12px 20px',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 14,
              fontWeight: 'bold',
            }}
          >
            {activeAction === 'recommend' ? 'RECOMMENDING...' : 'GET RECOMMENDATION'}
          </button>
        </div>
        {recommendation && (
          <div style={{ background: '#1a1a2e', borderLeft: '4px solid #00ff88', borderRadius: 6, padding: '12px 16px', marginBottom: 16 }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 4 }}>RECOMMENDED FOR ${recommendation.capital.toFixed(2)} @ {recommendation.risk_tolerance} RISK</div>
            <div style={{ color: '#00ff88', fontSize: 20, fontWeight: 'bold' }}>
              {recommendation.recommended_strategy.replace(/_/g, ' ').toUpperCase()}
            </div>
          </div>
        )}
        {recommendError && (
          <div style={{ background: '#2a1a1a', borderLeft: '4px solid #ff4444', borderRadius: 6, padding: '12px 16px', marginBottom: 16, color: '#ff6666', fontSize: 13 }}>
            {recommendError}
          </div>
        )}
        <div style={{ color: '#aaa', fontSize: 13, lineHeight: 1.6 }}>
          <strong>Recommendation Logic:</strong>
          <ul style={{ marginTop: 8, paddingLeft: 20 }}>
            <li><strong>{'<$5:'}</strong> Affiliate Content (lowest cost, no upfront investment)</li>
            <li><strong>$5-20:</strong> Digital Products (higher ROI, requires content creation)</li>
            <li><strong>$20-100:</strong> Print-on-Demand or Multi-Channel (low risk physical products)</li>
            <li><strong>{'>$100:'}</strong> Shopify Store or Multi-Channel (full e-commerce operation)</li>
          </ul>
        </div>
      </div>
    </div>
  )
}