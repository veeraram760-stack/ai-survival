import type { AgentNode } from '../../types/system'
import { CLASS_LABEL, fmtNum } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'

export default function AgentTable({ agents, onSelectAgent }: { agents: AgentNode[], onSelectAgent: (id: number) => void }) {
  return (
    <div className="v2-page">
      <div className="v2-page-header">AGENT ROSTER</div>
      
      <div className="v2-table">
        <div className="vt-head">
          <span>AGENT</span>
          <span>DEPARTMENT</span>
          <span>STATUS</span>
          <span>CURRENT TASK</span>
          <span>PERFORMANCE</span>
          <span>CPU / MEM</span>
        </div>
        {agents.map(a => (
          <div key={a.id} className="vt-row" onClick={() => onSelectAgent(a.id)}>
            <span style={{ color: CLASS_COLOR[a.type] || 'var(--cyan)' }}>{CLASS_LABEL[a.type]}-{a.id}</span>
            <span className="ghost uppercase">{a.domain}</span>
            <span className={a.status === 'ALIVE' ? 'pos' : 'dim'}>{a.status}</span>
            <span className="ghost">{a.status === 'ALIVE' ? 'Executing core loop...' : 'Awaiting instructions'}</span>
            <span>{fmtNum(a.profit)} <span className="dim">P&L</span></span>
            <span className="dim">14% / 22%</span>
          </div>
        ))}
        {agents.length === 0 && <div className="p-4 dim">NO AGENTS ONLINE</div>}
      </div>
    </div>
  )
}
