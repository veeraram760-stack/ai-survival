import { memo, useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import type { AgentNode, PerformanceData } from '../../types/system'
import { apiFetch } from '../../services/rest'
import { CLASS_COLOR } from '../orbit/colors'

interface Props {
  agents: AgentNode[]
}

type AgentPerf = PerformanceData

export default memo(function PerformancePanel({ agents }: Props) {
  const [agentPerf, setAgentPerf] = useState<AgentPerf[]>([])

  const byId = new Map(agents.map((a) => [a.id, a]))

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const data = await apiFetch<AgentPerf[]>('/performance/top?limit=20')
        if (!controller.signal.aborted) setAgentPerf(data)
      } catch {
        if (!controller.signal.aborted) setAgentPerf([])
      }
    }
    load()
    return () => controller.abort()
  }, [])

  const chartData = [...agentPerf]
    .sort((a, b) => b.task_count - a.task_count)
    .slice(0, 12)
    .map((p) => {
      const type = byId.get(p.agent_id)?.type
      return {
        name: `#${p.agent_id}`,
        success: p.success_count,
        failed: p.failure_count,
        reliability: +(p.reliability_score * 100).toFixed(1),
        quality: +(p.quality_score * 100).toFixed(1),
        color: type ? CLASS_COLOR[type] : '#8896A6',
      }
    })

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="ph-title">PERFORMANCE</span>
        <span className="ph-sub">{agentPerf.length} agents tracked</span>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 12 }}>
        <div className="kpi">
          <div className="k-key">Total Tasks</div>
          <div className="k-val">{agentPerf.reduce((s, p) => s + p.task_count, 0)}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Successful</div>
          <div className="k-val pos">{agentPerf.reduce((s, p) => s + p.success_count, 0)}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Failed</div>
          <div className="k-val neg">{agentPerf.reduce((s, p) => s + p.failure_count, 0)}</div>
        </div>
      </div>

      {chartData.length > 0 ? (
        <div className="dsec">
          <div className="dsec-title">TASK EXECUTION</div>
          <div className="chart-box" style={{ height: 180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#697789', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: '#0D1219', border: '1px solid #1E2D3D', borderRadius: 6, fontFamily: 'IBM Plex Mono', fontSize: 10 }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 10, fontFamily: 'IBM Plex Mono', color: '#697789' }} />
                <Bar dataKey="success" name="success" stackId="a" fill="#00D26A" radius={[0, 0, 0, 0]} opacity={0.8} />
                <Bar dataKey="failed" name="failed" stackId="a" fill="#FF3B5C" radius={[2, 2, 0, 0]} opacity={0.6} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="dim mono" style={{ fontSize: 11 }}>no task data</div>
      )}

      {agentPerf.length > 0 && (
        <div className="dsec">
          <div className="dsec-title">RELIABILITY / QUALITY</div>
          <div className="chart-box" style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#697789', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis hide domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ background: '#0D1219', border: '1px solid #1E2D3D', borderRadius: 6, fontFamily: 'IBM Plex Mono', fontSize: 10 }}
                  formatter={(v: any) => [`${v}%`, '']}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 10, fontFamily: 'IBM Plex Mono', color: '#697789' }} />
                <Bar dataKey="reliability" name="reliability" fill="#00B4D8" radius={[2, 2, 0, 0]} opacity={0.8} />
                <Bar dataKey="quality" name="quality" fill="#8B5CF6" radius={[2, 2, 0, 0]} opacity={0.8} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
})