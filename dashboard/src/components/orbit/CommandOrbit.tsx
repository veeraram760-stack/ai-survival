import { useMemo } from 'react'
import type { SystemSnapshot, DomainKey } from '../../types/system'
import { DOMAIN_ORDER } from '../../services/useSystem'
import { DOMAIN_HEX } from './colors'
import DomainNode from './DomainNode'
import CommandCore from '../core/CommandCore'
import type { PanelKey } from '../panels/types'

interface Props {
  snapshot: SystemSnapshot
  connected: true | false | 'recovering'
  activeDomain: DomainKey | null
  onOpenDomain: (key: DomainKey) => void
  onOpenAgent: (id: number) => void
  onView: (v: PanelKey) => void
}

/** Layout of the 10 domains on a 0–100 square. */
export function domainLayout() {
  const pos: Record<string, { x: number; y: number }> = {}
  DOMAIN_ORDER.forEach((key, i) => {
    const angle = (i / DOMAIN_ORDER.length) * Math.PI * 2 - Math.PI / 2
    const r = 38
    pos[key] = { x: +(50 + r * Math.cos(angle)).toFixed(2), y: +(50 + r * Math.sin(angle)).toFixed(2) }
  })
  return pos
}

export default function CommandOrbit({ snapshot, connected, activeDomain, onOpenDomain, onOpenAgent, onView }: Props) {
  const pos = useMemo(domainLayout, [])

  // Survival arc = real revenue progress toward the withdrawal threshold.
  const w = snapshot.withdrawal
  const survivalRatio = w && w.threshold > 0 ? Math.min(1, w.real_revenue / w.threshold) : 0
  const eligible = w?.eligible ?? false

  // Flow links around the ring (domain → next domain)
  const ringLinks = DOMAIN_ORDER.map((key, i) => {
    const a = pos[key]
    const b = pos[DOMAIN_ORDER[(i + 1) % DOMAIN_ORDER.length]]
    const mx = (a.x + b.x) / 2
    const my = (a.y + b.y) / 2
    // pull the control point away from the centre for an arc
    const len = Math.hypot(mx - 50, my - 50)
    const px = len === 0 ? mx : (mx - 50) * (1 + 0.25) + 50
    const py = len === 0 ? my : (my - 50) * (1 + 0.25) + 50
    return (
      <path key={`ring-${key}`} d={`M ${a.x} ${a.y} Q ${px} ${py} ${b.x} ${b.y}`}
        stroke={DOMAIN_HEX[key]} className="link-flow" strokeWidth={0.6} />
    )
  })

  // Core → domain radial links
  const coreLinks = DOMAIN_ORDER.map((key) => {
    const a = pos[key]
    const dx = a.x - 50, dy = a.y - 50
    const len = Math.hypot(dx, dy)
    const sx = 50 + (dx / len) * 16  // start at core radius
    const sy = 50 + (dy / len) * 16
    const ex = 50 + (dx / len) * (len - 8) // stop at node edge
    const ey = 50 + (dy / len) * (len - 8)
    return (
      <line key={`core-${key}`} x1={sx} y1={sy} x2={ex} y2={ey}
        stroke={DOMAIN_HEX[key]} strokeWidth={0.5} opacity={0.14} />
    )
  })

  return (
    <div className={`cc-orbit${connected ? '' : ' down'}`}>
      <div className="orbit-wrap">
        <div className="orbit-cross" />
        <div className="orbit-ring r1" />
        <div className="orbit-ring r2" />

        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid meet"
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}
        >
          {coreLinks}
          {ringLinks}
        </svg>

        <CommandCore
          capital={snapshot.capital}
          state={snapshot.state}
          connected={connected === true}
          survivalRatio={survivalRatio}
          eligible={eligible}
          onOpen={() => onOpenDomain('treasury')}
        />

        {DOMAIN_ORDER.map((key) => {
          const p = pos[key]
          return (
            <DomainNode
              key={key}
              domain={snapshot.domains.find((d) => d.key === key)!}
              active={activeDomain === key}
              style={{ left: `${p.x}%`, top: `${p.y}%` }}
              onOpen={(k) => {
                if (k === 'protocol') onView('lineage')
                else onOpenDomain(k as DomainKey)
              }}
              onOpenAgent={onOpenAgent}
            />
          )
        })}
      </div>
    </div>
  )
}