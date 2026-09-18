import { memo } from 'react'
import type { CapitalResponse, SystemStateResponse, WithdrawalStatus } from '../../types/system'
import { MODE_RAW } from '../system/SystemBar'

interface Props {
  capital: CapitalResponse
  state: SystemStateResponse
  withdrawal: WithdrawalStatus | null
  connected: boolean
  lastContact: string | null
}

function fmt(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(1)}k`
  return `$${n.toFixed(2)}`
}

/** Survival / withdrawal readout — real numbers, explicit degraded state. */
export default memo(function SurvivalPanel({ capital, state, withdrawal, connected, lastContact }: Props) {
  const mode = state.current_mode
  const threshold = withdrawal?.threshold ?? 0
  const ratio = threshold > 0 ? Math.min(1, (withdrawal?.real_revenue ?? 0) / threshold) : 0
  const targetMet = !!withdrawal?.eligible

  return (
    <div className="rail-block">
      <div className="rb-head">SURVIVAL</div>

      <div style={{ marginBottom: 10 }}>
        <span className="pill" style={{ color: MODE_RAW[mode], borderColor: `${MODE_RAW[mode]}55`, background: `${MODE_RAW[mode]}14` }}>
          {connected ? mode : 'NO LINK'}
        </span>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 8 }}>
        <div className="kpi">
          <div className="k-key">Total</div>
          <div className="k-val">{connected ? fmt(capital.total_capital) : '—'}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Real Rev</div>
          <div className="k-val">{connected ? fmt(capital.real_revenue) : '—'}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Sim Rev</div>
          <div className="k-val" style={{ color: 'var(--cyan)' }}>{connected ? fmt(capital.simulated_revenue) : '—'}</div>
        </div>
        <div className="kpi">
          <div className="k-key">Net P&L</div>
          <div className={`k-val ${(connected && capital.net_profit >= 0) ? 'pos' : 'neg'}`}>
            {connected ? fmt(capital.net_profit) : '—'}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span className="uppercase mono" style={{ color: 'var(--text-muted)', fontSize: 9 }}>WITHDRAWAL TARGET</span>
        <span className={`pill ${targetMet ? 'g' : 'a'}`}>{targetMet ? 'ELIGIBLE' : 'PENDING'}</span>
      </div>
      <div className="prog" style={{ marginBottom: 4 }}>
        <i style={{ width: `${connected ? ratio * 100 : 0}%`, background: targetMet ? 'var(--green)' : 'var(--amber)' }} />
      </div>
      <div className="mono" style={{ fontSize: 10, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
        <span>{connected ? fmt(withdrawal?.real_revenue ?? 0) : '—'} / {fmt(threshold)}</span>
        <span>{connected ? `gap ${fmt(withdrawal?.remaining_to_threshold ?? 0)}` : '—'}</span>
      </div>

      {!connected && (
        <div className="mono" style={{ fontSize: 9, color: 'var(--text-ghost)', marginTop: 8 }}>
          last contact {lastContact ? new Date(lastContact).toLocaleTimeString() : '—'}
        </div>
      )}
    </div>
  )
})