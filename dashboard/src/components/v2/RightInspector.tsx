import type { DomainInfo, AgentNode, SystemSnapshot } from '../../types/system'
import { CLASS_LABEL, fmtNum } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'

interface Props {
  domain: DomainInfo | null
  agent: AgentNode | null
  snapshot: SystemSnapshot
  onClose: () => void
  onSelectAgent: (id: number) => void
}

export default function RightInspector({ domain, agent, snapshot, onClose, onSelectAgent }: Props) {
  
  if (agent) {
    const parent = agent.parent_id ? snapshot.allAgents.find(a => a.id === agent.parent_id) : null
    const recentTx = snapshot.transactions.filter(t => t.agent_id === agent.id).slice(0, 5)

    return (
      <aside className="v2-inspector">
        <div className="insp-head">
          <div className="ih-title">
            <span style={{ color: CLASS_COLOR[agent.type] || 'var(--cyan)' }}>â— </span> 
            AGENT-{agent.id}
          </div>
          <button className="ih-close" onClick={onClose}>âœ•</button>
        </div>
        
        <div className="insp-body">
          <div className="insp-sec">
            <div className="is-row"><span className="dim">ROLE</span> <span>{CLASS_LABEL[agent.type]}</span></div>
            <div className="is-row"><span className="dim">STATUS</span> <span className="pos">{agent.status}</span></div>
            <div className="is-row"><span className="dim">CURRENT TASK</span> <span>{agent.status === 'ALIVE' ? 'Processing module' : 'Idle'}</span></div>
            <div className="is-row"><span className="dim">OBJECTIVE</span> <span className="ghost">{agent.strategy || 'Autonomous subsystem'}</span></div>
            {parent && (
              <div className="is-row cursor-pointer hover-cyan" onClick={() => onSelectAgent(parent.id)}>
                <span className="dim">PARENT AGENT</span> <span>AGENT-{parent.id} ({CLASS_LABEL[parent.type]})</span>
              </div>
            )}
          </div>

          <div className="insp-sec-title">PERFORMANCE & ECONOMICS</div>
          <div className="insp-sec">
            <div className="is-row"><span className="dim">REVENUE</span> <span className="pos">{fmtNum(agent.revenue)}</span></div>
            <div className="is-row"><span className="dim">EXPENSES</span> <span className="neg">{fmtNum(agent.expenses)}</span></div>
            <div className="is-row"><span className="dim">PROFIT</span> <span>{fmtNum(agent.profit)}</span></div>
            <div className="is-row"><span className="dim">SUCCESS RATE</span> <span>{(agent.success_rate * 100).toFixed(1)}%</span></div>
          </div>

          <div className="insp-sec-title">RESOURCE USAGE (ESTIMATED)</div>
          <div className="insp-sec">
            <div className="is-bar-row">
              <span className="dim">CPU</span>
              <div className="is-bar"><div style={{ width: '42%' }} /></div>
            </div>
            <div className="is-bar-row">
              <span className="dim">MEMORY</span>
              <div className="is-bar"><div style={{ width: '28%' }} /></div>
            </div>
            <div className="is-bar-row">
              <span className="dim">API</span>
              <div className="is-bar"><div style={{ width: '64%' }} /></div>
            </div>
          </div>

          <div className="insp-sec-title">RECENT ACTIONS</div>
          <div className="insp-sec">
            {recentTx.length > 0 ? recentTx.map(t => (
              <div key={t.id} className="is-event">
                <span className="dim">{new Date(t.timestamp).toLocaleTimeString()}</span>
                <span>{t.action || t.category} ({fmtNum(t.amount)})</span>
              </div>
            )) : <div className="dim">No recent actions</div>}
          </div>
        </div>
      </aside>
    )
  }

  if (domain) {
    const aliveCount = domain.agents.filter(a => a.status === 'ALIVE').length
    const idleCount = domain.agents.length - aliveCount

    return (
      <aside className="v2-inspector">
        <div className="insp-head">
          <div className="ih-title" style={{ color: domain.color }}>{domain.label}</div>
          <button className="ih-close" onClick={onClose}>âœ•</button>
        </div>

        <div className="insp-body">
          <div className="insp-sec-title">DEPARTMENT STATUS</div>
          <div className="insp-sec">
            <div className="is-row"><span className="dim">ACTIVE</span> <span className="pos">â—  LIVE</span></div>
            <div className="is-row"><span className="dim">TOTAL AGENTS</span> <span>{domain.agents.length}</span></div>
            <div className="is-row"><span className="dim">WORKING</span> <span className="pos">{aliveCount}</span></div>
            <div className="is-row"><span className="dim">IDLE</span> <span className="amber">{idleCount}</span></div>
            <div className="is-row"><span className="dim">FAILED</span> <span className="neg">0</span></div>
          </div>

          <div className="insp-sec-title">CURRENT OBJECTIVE</div>
          <div className="insp-sec ghost">
            Execute operational tasks for {domain.label.toLowerCase()} subroutines.
          </div>

          <div className="insp-sec-title">WORKER ROSTER</div>
          <div className="insp-sec roster">
            {domain.agents.length > 0 ? domain.agents.map(a => (
              <div key={a.id} className="roster-item" onClick={() => onSelectAgent(a.id)}>
                <div className="ri-head">
                  <span>{CLASS_LABEL[a.type]}-{a.id}</span>
                  <span style={{ color: a.status === 'ALIVE' ? 'var(--green)' : 'var(--amber)' }}>â—  {a.status}</span>
                </div>
                <div className="ri-sub ghost">{a.strategy?.slice(0,30) || 'Standing by'}</div>
              </div>
            )) : <div className="dim">No agents assigned to this department.</div>}
          </div>
        </div>
      </aside>
    )
  }

  // Default empty state / global instructions
  return (
    <aside className="v2-inspector empty">
      <div className="dim">Select a node or agent on the map to inspect operational details.</div>
    </aside>
  )
}
