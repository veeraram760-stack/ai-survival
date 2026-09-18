import type { SystemSnapshot, DomainInfo } from '../../types/system'
import { DOMAIN_META } from '../../services/useSystem'

interface Props {
  snapshot: SystemSnapshot
  onSelectNode: (id: string) => void
  activeNode: string | null
}

const POSITIONS: Record<string, { x: number, y: number }> = {
  // Center
  core: { x: 500, y: 350 },
  
  // Value flow (Arc top left to bottom left)
  research: { x: 150, y: 150 },
  market: { x: 100, y: 280 },
  content: { x: 150, y: 420 },
  product: { x: 260, y: 530 },
  fabrication: { x: 400, y: 600 },
  revenue: { x: 600, y: 600 },
  treasury: { x: 740, y: 530 },

  // Control flow (Top right)
  risk: { x: 650, y: 150 },
  qa: { x: 800, y: 240 },

  // Intelligence flow (Bottom right)
  learning: { x: 850, y: 380 },
  protocol: { x: 900, y: 500 }, // Evolution
}

const CONNECTIONS = [
  ['research', 'market'],
  ['market', 'content'],
  ['content', 'product'],
  ['product', 'fabrication'],
  ['fabrication', 'revenue'],
  ['revenue', 'treasury'],
  ['treasury', 'core'],

  ['core', 'risk'],
  ['risk', 'qa'],

  ['core', 'learning'],
  ['learning', 'protocol'], // evolution
  ['protocol', 'core']
]

export default function SystemMap({ snapshot, onSelectNode, activeNode }: Props) {
  
  const getDomain = (key: string): DomainInfo | undefined => {
    return snapshot.domains.find(d => d.key === key)
  }

  // Draw lines
  const lines = CONNECTIONS.map(([src, dst], i) => {
    const p1 = POSITIONS[src]
    const p2 = POSITIONS[dst]
    if(!p1 || !p2) return null
    return (
      <line 
        key={i} 
        x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} 
        stroke="var(--border-active)" strokeWidth={2} strokeDasharray="4 4" 
        className="flow-line" 
      />
    )
  })

  const renderNode = (key: string, customDomain?: DomainInfo) => {
    const p = POSITIONS[key]
    if (!p) return null
    const domain = customDomain || getDomain(key)
    // Always show node, even with empty domain (fallback for disconnected state)
    const d = domain || { label: DOMAIN_META[key as any]?.label || key.toUpperCase(), agents: [], color: DOMAIN_META[key as any]?.color || 'var(--text-ghost)', totalRevenue: 0, totalProfit: 0, key }
    const activeLength = d.agents.filter(a => a.status === 'ALIVE' || a.status === 'WORKING').length
    
    // Determine status (mocked for now, but inferred from active agents or risk)
    const hasAgents = d.agents.length > 0
    let nodeStatus = hasAgents ? 'LIVE' : 'NO AGENTS'
    if (d.key === 'risk' && d.totalProfit < 0) nodeStatus = 'ALERT'

    const active = activeNode === `domain_${d.key}`

    return (
      <div 
        key={d.key} 
        className={`map-node ${active ? 'on' : ''}`}
        style={{ left: p.x, top: p.y, transform: 'translate(-50%, -50%)', borderColor: d.color }}
        onClick={() => onSelectNode(`domain_${d.key}`)}
      >
        <div className="mn-header">
          <span className="mn-dot" style={{ background: d.color }} />
          <span className="mn-title">{d.label}</span>
          <span className="mn-status">{nodeStatus}</span>
        </div>
        
        <div className="mn-body">
          <div className="mn-row">{d.agents.length} AGENTS</div>
          
          <div className="mn-bar-wrap">
            <div className="mn-bar" style={{ width: `${d.agents.length === 0 ? 0 : (activeLength / d.agents.length) * 100}%`, background: d.color }} />
          </div>
          
          <div className="mn-row ghost">
            {activeLength} working Â· {d.agents.length - activeLength} idle
          </div>
          
          {d.totalRevenue > 0 && (
            <div className="mn-row pos mt-2">
              REV: ${(d.totalRevenue).toFixed(0)}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="system-map-container">
      <svg className="sm-svg" viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid meet">
        {lines}
      </svg>
      {/* Core Node */}
      <div 
        className="map-core" 
        style={{ left: POSITIONS.core.x, top: POSITIONS.core.y, transform: 'translate(-50%, -50%)' }}
        onClick={() => onSelectNode('domain_exec')}
      >
        <div className="mc-title">AI SURVIVAL CORE</div>
        <div className="mc-stat">{snapshot.allAgents.length} AGENTS ONLINE</div>
        <div className="mc-stat pulse-green">SYSTEM HEALTHY</div>
      </div>

      {Object.keys(POSITIONS).filter(k => k !== 'core').map(k => renderNode(k))}
    </div>
  )
}
