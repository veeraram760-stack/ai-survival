import type { CapitalResponse, SystemStateResponse } from '../../types/system'
import { MODE_RAW } from '../system/SystemBar'

interface Props {
  capital: CapitalResponse
  state: SystemStateResponse
  connected: boolean
  survivalRatio: number   // real_revenue / withdrawal threshold, clamped 0..1
  eligible: boolean
  onOpen: () => void
}

function fmtCap(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(1)}k`
  return `$${n.toFixed(0)}`
}

/** Central SYSTEM CORE orb — survival arc gauge + total capital readout. */
export default function CommandCore({ capital, state, connected, survivalRatio, eligible, onOpen }: Props) {
  const mode = state.current_mode
  const color = connected ? MODE_RAW[mode] : '#3A4757'
  const ratio = Math.max(0.02, Math.min(1, survivalRatio))

  // SVG arc: full circle, gap at the bottom
  const R = 46
  const C = 2 * Math.PI * R
  const arcLen = C * ratio

  return (
    <div
      className="core"
      onClick={onOpen}
      role="button"
      aria-label="system core — open treasury"
      title={connected ? (eligible ? 'SURVIVAL TARGET MET' : 'target not yet met') : 'no link'}
    >
      <div className="core-orbital" />
      <svg viewBox="0 0 100 100" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
        <circle cx="50" cy="50" r={R} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="2" />
        <circle
          cx="50" cy="50" r={R} fill="none"
          stroke={color} strokeWidth="2.5" strokeLinecap="round"
          strokeDasharray={`${arcLen} ${C - arcLen}`}
          style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <span className="core-mode">{mode}{connected ? '' : ' · NO LINK'}</span>
      <span className="core-cap">{(connected ? fmtCap(capital.total_capital) : '— — —')}</span>
      <span className="core-sub">
        <span style={{ color: 'var(--green)' }}>R {fmtCap(capital.real_revenue)}</span>
        <span className="dim">/ S {fmtCap(capital.simulated_revenue)}</span>
      </span>
      <span className="core-sub" style={{ fontSize: 9 }}>
        reserve {fmtCap(capital.survival_reserve)} · op {fmtCap(capital.operating_capital)}
      </span>
    </div>
  )
}