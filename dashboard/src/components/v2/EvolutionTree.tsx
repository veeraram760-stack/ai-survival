import type { AgentNode } from '../../types/system'
import { CLASS_COLOR } from '../orbit/colors'

export default function EvolutionTree({ agents, onSelectAgent }: { agents: AgentNode[], onSelectAgent: (id: number) => void }) {
  // Simple representation sorting by generation
  const byGen = agents.reduce((acc, a) => {
    acc[a.generation] = acc[a.generation] || []
    acc[a.generation].push(a)
    return acc
  }, {} as Record<number, AgentNode[]>)

  return (
    <div className="v2-page">
      <div className="v2-page-header">EVOLUTION & LINEAGE</div>
      <div className="evo-container mt-6">
        {Object.keys(byGen).map(g => (
          <div key={g} className="evo-gen">
            <div className="eg-label">GEN {g}</div>
            <div className="eg-agents">
              {byGen[parseInt(g, 10)].map(a => (
                <div key={a.id} className="eg-node" style={{ borderColor: CLASS_COLOR[a.type] || 'var(--border-default)' }} onClick={() => onSelectAgent(a.id)}>
                  Agent {a.id} <br/><span className="dim">{a.type}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
