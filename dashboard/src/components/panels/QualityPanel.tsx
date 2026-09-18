import { memo, useState, useEffect } from 'react'
import type { AgentNode, PerformanceData } from '../../types/system'
import { apiFetch } from '../../services/rest'
import { CLASS_LABEL } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'

interface Props {
  agents: AgentNode[]
}

type AgentPerf = PerformanceData

export default memo(function QualityPanel({ agents }: Props) {
  const [performers, setPerformers] = useState<AgentPerf[]>([])

  const byId = new Map(agents.map((a) => [a.id, a]))

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const data = await apiFetch<AgentPerf[]>('/performance/top?limit=10')
        if (!controller.signal.aborted) setPerformers(data)
      } catch {
        if (!controller.signal.aborted) setPerformers([])
      }
    }
    load()
    return () => controller.abort()
  }, [])

  const avgReliability = performers.length > 0
    ? performers.reduce((s, p) => s + p.reliability_score, 0) / performers.length
    : 0
  const avgQuality = performers.length > 0
    ? performers.reduce((s, p) => s + p.quality_score, 0) / performers.length
    : 0

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="ph-title">QUALITY CONTROL</span>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 12 }}>
        <div className="kpi">
          <div className="k-key">Avg Reliability</div>
          <div className="k-val">{(avgReliability * 100).toFixed(1)}%</div>
        </div>
        <div className="kpi">
          <div className="k-key">Avg Quality</div>
          <div className="k-val">{(avgQuality * 100).toFixed(1)}%</div>
        </div>
      </div>

      {performers.length > 0 ? (
        <div className="dtable-wrap">
        <div className="dtable dt-cols-5">
          <div className="dt-head">
            <span>agent</span>
            <span>class</span>
            <span>reliability</span>
            <span>quality</span>
            <span>tasks</span>
          </div>
          {performers.map((p) => {
            const relBar = Math.max(0, Math.min(1, p.reliability_score))
            const qualBar = Math.max(0, Math.min(1, p.quality_score))
            const type = byId.get(p.agent_id)?.type
            return (
              <div className="dt-row" key={p.agent_id}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span className="a-dot" style={{ background: type ? CLASS_COLOR[type] : '#8896A6' }} />
                  <span className="mono" style={{ fontSize: 11 }}>#{p.agent_id}</span>
                </span>
                <span className="dr-key" style={{ fontSize: 11 }}>{type ? CLASS_LABEL[type] : '—'}</span>
                <span>
                  <div className="qual-row">
                    <span style={{ width: 56, fontSize: 11, color: 'var(--text-secondary)' }}>{(relBar * 100).toFixed(0)}%</span>
                    <div className="qual-bar"><div style={{ width: `${relBar * 100}%`, background: relBar > 0.7 ? 'var(--green)' : relBar > 0.4 ? 'var(--amber)' : 'var(--red)' }} /></div>
                  </div>
                </span>
                <span>
                  <div className="qual-row">
                    <span style={{ width: 56, fontSize: 11, color: 'var(--text-secondary)' }}>{(qualBar * 100).toFixed(0)}%</span>
                    <div className="qual-bar"><div style={{ width: `${qualBar * 100}%`, background: qualBar > 0.7 ? 'var(--green)' : qualBar > 0.4 ? 'var(--amber)' : 'var(--red)' }} /></div>
                  </div>
                </span>
                <span className="mono" style={{ fontSize: 11 }}>{p.task_count}</span>
              </div>
            )
          })}
        </div>
        </div>
      ) : (
        <div className="dim mono" style={{ fontSize: 11 }}>no performance data</div>
      )}
    </div>
  )
})