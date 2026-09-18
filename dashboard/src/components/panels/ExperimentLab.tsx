import { memo } from 'react'
import type { Experiment, AgentNode } from '../../types/system'
import { CLASS_LABEL } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'

interface Props {
  experiments: Experiment[]
  agents?: AgentNode[]
}

export default memo(function ExperimentLab({ experiments, agents }: Props) {
  const byId = new Map((agents ?? []).map((a) => [a.id, a]))
  const active = experiments.filter((e) => e.status === 'RUNNING' || e.status === 'QUEUED')
  const completed = experiments.filter((e) => e.status === 'COMPLETED')
  const failed = experiments.filter((e) => e.status === 'FAILED')

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="ph-title">EXPERIMENT LAB</span>
        <span className="ph-sub">{active.length} active · {completed.length} done · {failed.length} failed</span>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 12 }}>
        <div className="kpi">
          <div className="k-key">Active</div>
          <div className="k-val">{active.length}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Completed</div>
          <div className="k-val pos">{completed.length}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Failed</div>
          <div className="k-val neg">{failed.length}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Success Rate</div>
          <div className="k-val">{(completed.length + failed.length) > 0 ? ((completed.length / (completed.length + failed.length)) * 100).toFixed(1) + '%' : '—'}</div>
        </div>
      </div>

      <div className="dtable-wrap">
      <div className="dtable dt-cols-4">
        <div className="dt-head">
          <span>agent</span>
          <span>hypothesis</span>
          <span>status</span>
          <span>result</span>
        </div>
        {experiments.slice(0, 30).map((e) => {
          const type = byId.get(e.agent_id)?.type
          return (
            <div className="dt-row" key={e.id}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className="a-dot" style={{ background: type ? CLASS_COLOR[type] : '#8896A6' }} />
              <span className="mono" style={{ fontSize: 11 }}>#{e.agent_id}</span>
              <span className="dr-key" style={{ fontSize: 11 }}>{type ? CLASS_LABEL[type] : '—'}</span>
            </span>
            <span className="dr-key" style={{ maxWidth: 240 }}>{e.hypothesis.slice(0, 52)}</span>
            <span>
              <span className={`pill ${e.status === 'COMPLETED' ? 'g' : e.status === 'FAILED' ? 'r' : 'c'}`}>
                {e.status}
              </span>
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              {e.actual_result != null ? e.actual_result : e.status === 'COMPLETED' ? '—' : 'pending'}
            </span>
            </div>
          )
        })}
        {experiments.length === 0 && (
          <div className="dt-row dim mono" style={{ fontSize: 11 }}>no experiments recorded</div>
        )}
      </div>
      </div>
    </div>
  )
})