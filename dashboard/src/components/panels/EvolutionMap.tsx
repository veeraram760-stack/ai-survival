import { memo, useMemo } from 'react'
import type { AgentNode } from '../../types/system'
import { CLASS_LABEL, fmtNum } from '../../services/useSystem'
import { CLASS_COLOR } from '../orbit/colors'

interface Props {
  agents: AgentNode[]
  onOpenAgent: (id: number) => void
}

/** Children keyed by parent_id; a null/dangling parent_id lands under the synthetic root -1. */
function buildForest(agents: AgentNode[]): Map<number, AgentNode[]> {
  const ids = new Set(agents.map((a) => a.id))
  const byParent = new Map<number, AgentNode[]>()
  for (const a of agents) {
    const key = a.parent_id != null && ids.has(a.parent_id) ? a.parent_id : -1
    const list = byParent.get(key) ?? []
    list.push(a)
    byParent.set(key, list)
  }
  for (const list of byParent.values()) list.sort((a, b) => a.id - b.id)
  return byParent
}

function TreeRow({ agent, byParent, depth, visited, onOpen }: {
  agent: AgentNode
  byParent: Map<number, AgentNode[]>
  depth: number
  visited: Set<number>
  onOpen: (id: number) => void
}) {
  const color = CLASS_COLOR[agent.type] || '#8896A6'
  const kids = (byParent.get(agent.id) ?? []).filter((c) => !visited.has(c.id))
  return (
    <>
      <div className="drow lineage-row" style={{ paddingLeft: depth * 16 }}
        onClick={() => onOpen(agent.id)}>
        <span className="dr-key" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className="a-dot" style={{ background: color }} />
          <span className="mono">#{agent.id}</span>
          <span style={{ color }}>{CLASS_LABEL[agent.type]}</span>
        </span>
        <span className="dr-val">
          <span className="mono" style={{ marginRight: 8 }}>gen {agent.generation}</span>
          <span className={`pill ${agent.status === 'TERMINATED' || agent.status === 'FAILED' ? 'r' : 'g'}`}>
            {agent.status}
          </span>
          <span className="mono" style={{ marginLeft: 6 }}>{agent.profit >= 0 ? '+' : ''}{fmtNum(agent.profit)}</span>
        </span>
      </div>
      {kids.map((c) => {
        const next = new Set(visited)
        next.add(c.id)
        return <TreeRow key={c.id} agent={c} byParent={byParent} depth={depth + 1} visited={next} onOpen={onOpen} />
      })}
    </>
  )
}

export default memo(function EvolutionMap({ agents, onOpenAgent }: Props) {
  const byParent = useMemo(() => buildForest(agents), [agents])
  const roots = byParent.get(-1) ?? []

  const maxGen = agents.reduce((m, a) => Math.max(m, a.generation), 0)
  const activeCount = agents.filter((a) => a.status !== 'TERMINATED' && a.status !== 'FAILED').length

  const genCounts = useMemo(() => {
    const counts: Record<number, number> = {}
    for (const a of agents) {
      counts[a.generation] = (counts[a.generation] ?? 0) + 1
    }
    return counts
  }, [agents])
  const gens = Object.keys(genCounts).sort((a, b) => Number(a) - Number(b))

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="ph-title">EVOLUTION / LINEAGE MAP</span>
        <span className="ph-sub">{agents.length} agents · {maxGen} generations</span>
      </div>

      <div className="dsec">
        <div className="kpi-grid">
          <div className="kpi">
            <div className="k-key">total agents</div>
            <div className="k-val">{agents.length}</div>
          </div>
          <div className="kpi">
            <div className="k-key">generations</div>
            <div className="k-val">{maxGen}</div>
          </div>
          <div className="kpi">
            <div className="k-key">active</div>
            <div className="k-val pos">{activeCount}</div>
          </div>
        </div>
      </div>

      {gens.length > 0 && (
        <div className="dsec">
          <div className="dsec-title">GENERATIONS</div>
          {gens.map((gen) => (
            <div className="drow" key={gen}>
              <span className="dr-key">gen {gen}</span>
              <span className="dr-val">
                <span className="mono">{genCounts[Number(gen)]} agents</span>
                <span style={{ display: 'inline-block', width: genCounts[Number(gen)] * 4, height: 6, background: 'var(--green)', borderRadius: 2, marginLeft: 8, opacity: 0.6 }} />
              </span>
            </div>
          ))}
        </div>
      )}

      {roots.length > 0 ? (
        <div className="dsec">
          <div className="dsec-title">LINEAGE TREE</div>
          <div className="lineage-tree">
            {roots.map((r) => (
              <TreeRow key={r.id} agent={r} byParent={byParent} depth={0} visited={new Set([r.id])} onOpen={onOpenAgent} />
            ))}
          </div>
        </div>
      ) : (
        <div className="dim mono" style={{ fontSize: 11 }}>no lineage data</div>
      )}
    </div>
  )
})