import { memo, useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { apiFetch } from '../../services/rest'
import { CLASS_COLOR } from '../orbit/colors'
import type { AgentNode } from '../../types/system'

interface AgentPerf { agent_id: number; strategy: string; revenue: number; expenses: number; profit: number }

interface Props {
  agents: AgentNode[]
}

export default memo(function RevenuePanel({ agents }: Props) {
  const [agentPerf, setAgentPerf] = useState<AgentPerf[]>([])

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const data = await apiFetch<AgentPerf[]>('/revenue/agents')
        if (!controller.signal.aborted) setAgentPerf(data)
      } catch {
        if (!controller.signal.aborted) setAgentPerf([])
      }
    }
    load()
    return () => controller.abort()
  }, [])

  // Build chart data from agents that have revenue
  const chartData = agentPerf
    .filter((a) => a.revenue > 0)
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 10)
    .map((a) => {
      const agent = agents.find((ag) => ag.id === a.agent_id)
      const type = agent?.type
      return {
        name: `#${a.agent_id}`,
        revenue: +a.revenue.toFixed(2),
        expenses: +a.expenses.toFixed(2),
        profit: +a.profit.toFixed(2),
        color: type ? CLASS_COLOR[type] : '#8896A6',
      }
    })

  // Domain aggregates
  const domainAgg = agents.reduce<Record<string, { rev: number; exp: number }>>((acc, a) => {
    const type = a.type
    if (!acc[type]) acc[type] = { rev: 0, exp: 0 }
    acc[type].rev += a.revenue
    acc[type].exp += a.expenses
    return acc
  }, {})

  const domainData = Object.entries(domainAgg)
    .filter(([, v]) => v.rev > 0)
    .sort(([, a], [, b]) => b.rev - a.rev)
    .map(([type, v]) => ({
      name: type.slice(0, 12),
      revenue: +v.rev.toFixed(2),
      expenses: +v.exp.toFixed(2),
      profit: +(v.rev - v.exp).toFixed(2),
      color: CLASS_COLOR[type as keyof typeof CLASS_COLOR] || '#8896A6',
    }))

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="ph-title">REVENUE ENGINE</span>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 12 }}>
        <div className="kpi">
          <div className="k-key">Top Agents</div>
          <div className="k-val">{chartData.length}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Domains Active</div>
          <div className="k-val">{domainData.length}</div>
        </div>
      </div>

      {chartData.length > 0 ? (
        <div className="dsec">
          <div className="dsec-title">PER-AGENT REVENUE</div>
          <div className="chart-box" style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#697789', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: '#0D1219', border: '1px solid #1E2D3D', borderRadius: 6, fontFamily: 'IBM Plex Mono', fontSize: 10 }}
                  formatter={(v: any) => [`$${Number(v).toFixed(2)}`, '']}
                />
                <Bar dataKey="revenue" name="revenue" radius={[2, 2, 0, 0]}>
                  {chartData.map((d, i) => <Cell key={i} fill={d.color} opacity={0.8} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="dim mono" style={{ fontSize: 11 }}>no agent revenue data</div>
      )}

      {domainData.length > 0 && (
        <div className="dsec">
          <div className="dsec-title">BY DOMAIN</div>
          <div className="chart-box" style={{ height: 140 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={domainData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#697789', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: '#0D1219', border: '1px solid #1E2D3D', borderRadius: 6, fontFamily: 'IBM Plex Mono', fontSize: 10 }}
                  formatter={(v: any) => [`$${Number(v).toFixed(2)}`, '']}
                />
                <Bar dataKey="revenue" name="revenue" radius={[2, 2, 0, 0]}>
                  {domainData.map((d, i) => <Cell key={i} fill={d.color} opacity={0.8} />)}
                </Bar>
                <Bar dataKey="expenses" name="expenses" radius={[2, 2, 0, 0]}>
                  {domainData.map((_, i) => <Cell key={i} fill="#FF3B5C" opacity={0.5} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
})