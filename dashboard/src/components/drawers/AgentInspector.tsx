import { useState, useEffect } from 'react'
import type { AgentNode, Transaction, LineageNode, PerformanceData } from '../../types/system'
import { CLASS_LABEL, fmtNum } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'
import { apiFetch } from '../../services/rest'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'

interface Props {
  agent: AgentNode
  transactions: Transaction[]
  onOpenParent?: (id: number) => void
  onClose: () => void
}

function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <span className="dim" style={{ fontSize: 10 }}>—</span>
  return (
    <ResponsiveContainer width="100%" height={32}>
      <AreaChart data={values.map((v, i) => ({ i, v }))} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1} fill="none" isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default function AgentInspector({ agent, transactions, onOpenParent, onClose }: Props) {
  const [lineage, setLineage] = useState<LineageNode | null>(null)
  const [perf, setPerf] = useState<PerformanceData | null>(null)

  useEffect(() => {
    const abort = new AbortController()
    const fetchAll = async () => {
      try {
        const [l, p] = await Promise.all([
          apiFetch<LineageNode>(`/agents/${agent.id}/lineage`),
          apiFetch<PerformanceData>(`/performance/${agent.id}`),
        ])
        if (!abort.signal.aborted) { setLineage(l); setPerf(p) }
      } catch { if (!abort.signal.aborted) { setLineage(null); setPerf(null) } }
    }
    fetchAll()
    return () => abort.abort()
  }, [agent.id])

  const agentTx = transactions.filter((t) => t.agent_id === agent.id).slice(-20)
  const sparkData = agentTx.map((t) => +t.amount.toFixed(2))

  return (
    <>
      <div className="drawer-scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`Agent ${agent.id} inspector`}>
        <div className="drawer-head">
          <span className="dh-color" style={{ background: CLASS_COLOR[agent.type] || '#8896A6' }} />
          <div>
            <div className="dh-title">#{agent.id} {CLASS_LABEL[agent.type]}</div>
            <div className="dh-sub">
              gen {agent.generation} · {agent.status} · {agent.days_alive}d · {agent.strategy?.slice(0, 24) ?? '—'}
            </div>
          </div>
          <button className="dh-close" onClick={onClose} aria-label="close">✕</button>
        </div>

        <div className="drawer-body">
          <div className="dsec">
            <div className="kpi-grid">
              <div className="kpi">
                <div className="k-key">Revenue</div>
                <div className="k-val">{fmtNum(agent.revenue)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">Expenses</div>
                <div className="k-val">{fmtNum(agent.expenses)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">Profit</div>
                <div className={`k-val ${agent.profit >= 0 ? 'pos' : 'neg'}`}>{fmtNum(agent.profit)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">ROI</div>
                <div className={`k-val ${agent.roi >= 0 ? 'pos' : 'neg'}`}>{agent.roi}</div>
              </div>
            </div>
            <div className="kpi-grid" style={{ marginTop: 6 }}>
              <div className="kpi">
                <div className="k-key">Risk</div>
                <div className="k-val">{(agent.risk_score * 100).toFixed(0)}%</div>
              </div>
              <div className="kpi">
                <div className="k-key">Success</div>
                <div className="k-val">{(agent.success_rate * 100).toFixed(0)}%</div>
              </div>
              <div className="kpi">
                <div className="k-key">Budget</div>
                <div className="k-val">{fmtNum(agent.budget ?? 0)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">Experiments</div>
                <div className="k-val">{agent.experiments_count ?? 0}</div>
              </div>
            </div>
          </div>

          <div className="dsec">
            <div className="dsec-title">CURRENT STATUS</div>
            <div className="drow">
              <span className="dr-key">working for</span>
              <span className="dr-val" style={{ color: 'var(--text-main)', textAlign: 'right' }}>{agent.strategy || 'General Operations'}</span>
            </div>
            <div className="drow">
              <span className="dr-key">doing now</span>
              <span className="dr-val" style={{ color: 'var(--cyan)', textAlign: 'right' }}>{agent.status === 'ALIVE' ? 'Active / Processing' : agent.status}</span>
            </div>
            <div className="drow">
              <span className="dr-key">already done</span>
              <span className="dr-val" style={{ textAlign: 'right' }}>
                {perf ? `${perf.task_count} tasks completed` : `${agent.experiments_count || 0} experiments run`}
                {agentTx.length > 0 ? ` (${agentTx.length} recent txs)` : ''}
              </span>
            </div>
          </div>

          {sparkData.length > 0 && (
            <div className="dsec">
              <div className="dsec-title">REVENUE TRAJECTORY</div>
              <div style={{ height: 36 }}>
                <Sparkline values={sparkData} color={CLASS_COLOR[agent.type] || '#00D26A'} />
              </div>
            </div>
          )}

          {lineage && lineage.children && lineage.children.length > 0 && (
            <div className="dsec">
              <div className="dsec-title">LINEAGE</div>
              <div className="drow">
                <span className="dr-key">children</span>
                <span className="dr-val">{lineage.children.length}</span>
              </div>
              {lineage.children.map((c) => (
                <div className="drow" key={c.id} onClick={() => onOpenParent?.(c.id)}
                  style={{ cursor: 'pointer' }}>
                  <span className="dr-key">#{c.id} {c.type}</span>
                  <span className="dr-val" style={{ color: 'var(--cyan)' }}>
                    level {c.level}
                  </span>
                </div>
              ))}
            </div>
          )}

          {perf && (
            <div className="dsec">
              <div className="dsec-title">PERFORMANCE</div>
              <div className="kpi-grid">
                <div className="kpi">
                  <div className="k-key">Reliability</div>
                  <div className="k-val">{(perf.reliability_score * 100).toFixed(0)}%</div>
                </div>
                <div className="kpi">
                  <div className="k-key">Quality</div>
                  <div className="k-val">{(perf.quality_score * 100).toFixed(0)}%</div>
                </div>
                <div className="kpi">
                  <div className="k-key">Tasks</div>
                  <div className="k-val">{perf.task_count}</div>
                </div>
                <div className="kpi">
                  <div className="k-key">Errors</div>
                  <div className="k-val">{perf.failure_count}</div>
                </div>
              </div>
            </div>
          )}

          {agentTx.length > 0 && (
            <div className="dsec">
              <div className="dsec-title">LAST {agentTx.length} TRANSACTIONS</div>
              <div className="dtable-wrap">
                <div className="dtable dt-cols-3">
                <div className="dt-head">
                  <span>type</span><span>amount</span><span>balance</span>
                </div>
                {agentTx.slice(-8).reverse().map((t) => (
                  <div className="dt-row" key={t.id}>
                    <span>{t.action || t.category}</span>
                    <span className={t.amount >= 0 ? 'pos' : 'neg'}>{t.amount >= 0 ? '+' : ''}{fmtNum(t.amount)}</span>
                    <span>{fmtNum(t.balance_after)}</span>
                  </div>
                ))}
              </div>
              </div>
            </div>
          )}

          {agent.parent_id && (
            <div className="dsec">
              <div className="drow">
                <span className="dr-key">parent</span>
                <span className="dr-val" style={{ color: 'var(--cyan)', cursor: 'pointer' }}
                  onClick={() => onOpenParent?.(agent.parent_id!)}>
                  #{agent.parent_id}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}