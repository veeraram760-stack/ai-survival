import { useMemo } from 'react'
import type { DomainInfo, SystemSnapshot } from '../../types/system'
import { CLASS_LABEL, fmtNum } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'
import type { PanelKey } from '../panels/types'

interface Props {
  domain: DomainInfo
  snapshot: SystemSnapshot
  onOpenAgent: (id: number) => void
  onClose: () => void
  onOpenPanel: (p: PanelKey) => void
}

const DOMAIN_PANEL: Partial<Record<string, PanelKey>> = {
  learning: 'memory',
  protocol: 'lineage',
  content: 'lab',
  research: 'lab',
  qa: 'qa',
  perf: 'perf',
}

/** Right-side department inspector — stats, agent roster, domain modules. */
export default function DepartmentInspector({ domain, snapshot, onOpenAgent, onClose, onOpenPanel }: Props) {
  const agentIds = useMemo(() => new Set(domain.agents.map((a) => a.id)), [domain])

  const domainExps = useMemo(
    () => snapshot.experiments.filter((e) => agentIds.has(e.agent_id)).slice(0, 8),
    [snapshot.experiments, agentIds]
  )

  const domainMemory = domain.key === 'learning'
    ? snapshot.learning.slice(0, 8)
    : []

  const roi = domain.totalRevenue > 0
    ? (domain.totalProfit / domain.totalRevenue) * 100
    : 0

  const openPanel: PanelKey | null = DOMAIN_PANEL[domain.key] ?? null

  return (
    <>
      <div className="drawer-scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`${domain.label} department inspector`}>
        <div className="drawer-head">
          <span className="dh-color" style={{ background: domain.color }} />
          <div>
            <div className="dh-title">{domain.label}</div>
            <div className="dh-sub">
              {domain.agents.filter(a => a.status === 'ALIVE' || a.status === 'GROWING').length} working agents 
              (out of {domain.agents.length} total)
            </div>
          </div>
          <button className='dh-close' onClick={onClose} aria-label="close">✕</button>
        </div>

        <div className="drawer-body">
          <div className="dsec">
            <div className="kpi-grid">
              <div className="kpi">
                <div className="k-key">Revenue</div>
                <div className="k-val">{fmtNum(domain.totalRevenue)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">Expenses</div>
                <div className="k-val">{fmtNum(domain.totalExpenses)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">Profit</div>
                <div className={`k-val ${domain.totalProfit >= 0 ? 'pos' : 'neg'}`}>{fmtNum(domain.totalProfit)}</div>
              </div>
              <div className="kpi">
                <div className="k-key">ROI</div>
                <div className={`k-val ${roi >= 0 ? 'pos' : 'neg'}`}>{roi.toFixed(1)}%</div>
              </div>
            </div>
          </div>

          <div className="dsec">
            <div className="dsec-title">AGENTS</div>
            {domain.agents.length > 0 ? (
              <div className="agentlist">
                {domain.agents.map((a) => (
                  <div className="arow" key={a.id} style={{ '--dcolor': CLASS_COLOR[a.type] } as React.CSSProperties}
                    onClick={() => onOpenAgent(a.id)}>
                    <span className="a-dot" style={{ background: CLASS_COLOR[a.type] }} />
                    <span className="a-name">#{a.id} {CLASS_LABEL[a.type]}</span>
                    <span className="a-meta">
                      {a.status} · ROI {a.roi}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="dim mono" style={{ fontSize: 11 }}>no agents — engine module</div>
            )}
          </div>

          {domainExps.length > 0 && (
            <div className="dsec">
              <div className="dsec-title">EXPERIMENTS RUNNING</div>
              {domainExps.map((e) => (
                <div className="drow" key={e.id}>
                  <span className="dr-key">{e.hypothesis.slice(0, 42)}</span>
                  <span><span className={`pill ${e.status === 'COMPLETED' ? 'g' : e.status === 'FAILED' ? 'r' : 'c'}`}>{e.status}</span></span>
                </div>
              ))}
            </div>
          )}

          {domainMemory.length > 0 && (
            <div className="dsec">
              <div className="dsec-title">LEARNING MEMORY</div>
              {domainMemory.map((m, i) => (
                <div className="drow" key={i}>
                  <span className="dr-key">[{m.category}] {m.key}</span>
                  <span className="dr-val" style={{ color: 'var(--cyan)' }}>{Number(m.confidence).toFixed(2)}</span>
                </div>
              ))}
            </div>
          )}

          {openPanel && (
            <div style={{ marginTop: 4 }}>
              <button className="btn primary" onClick={() => onOpenPanel(openPanel!)}>
                OPEN FULL MODULE →
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
