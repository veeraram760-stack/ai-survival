import { memo } from 'react'
import type { DomainInfo } from '../../types/system'
import AgentNode from './AgentNode'

interface Props {
  domain: DomainInfo
  active: boolean
  style: React.CSSProperties
  onOpen: (key: string) => void
  onOpenAgent: (id: number) => void
}

function fmt(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(1)}k`
  return `$${n.toFixed(0)}`
}

/** A domain ring on the orbit map — labelled, agent-swarmed, clickable. */
export default memo(function DomainNode({ domain, active, style, onOpen, onOpenAgent }: Props) {
  return (
    <div
      className={`dnode${active ? ' on' : ''}`}
      style={{ '--dcolor': domain.color, ...style } as React.CSSProperties}
      onClick={() => onOpen(domain.key)}
      role="button"
      aria-label={`${domain.label} department — ${domain.agents.length} agents`}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onOpen(domain.key) }}
    >
      {domain.agents.length > 0 && (
        <span className="dcount">{domain.agents.length}</span>
      )}
      <span className="dstat">
        {domain.agents.length === 0
          ? `P&L ${fmt(domain.totalProfit)}`
          : `rev ${fmt(domain.totalRevenue)} · P&L ${fmt(domain.totalProfit)}`}
      </span>
      <span className="dagents">
        {domain.agents.map((a) => (
          <AgentNode key={a.id} agent={a} onClick={onOpenAgent} />
        ))}
        {domain.agents.length === 0 && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-ghost)' }}>—</span>
        )}
      </span>
      <span className="dlabel">{domain.label}</span>
    </div>
  )
})