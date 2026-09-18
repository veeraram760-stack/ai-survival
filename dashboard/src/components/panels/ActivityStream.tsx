import { useMemo } from 'react'
import type { ActivityEvent } from '../../types/system'
import { ACTIVITY_COLOR } from '../orbit/colors'
import { CLASS_LABEL } from '../../services/useSystem'

function timeStr(ts: string): string {
  const d = new Date(ts)
  if (isNaN(d.getTime())) return '--:--'
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function signChar(amount: number | undefined): string {
  if (amount == null) return '·'
  return amount >= 0 ? '+' : ''
}

/** Fused live activity stream — transactions, risk, decisions, memory. */
export default function ActivityStream({ events, onOpenAgent }: {
  events: ActivityEvent[]
  onOpenAgent: (id: number) => void
}) {
  const sorted = useMemo(() => {
    const arr = [...events]
    arr.sort((a, b) => {
      const ta = new Date(a.timestamp).getTime()
      const tb = new Date(b.timestamp).getTime()
      if (!isNaN(ta) && !isNaN(tb)) return tb - ta
      return 0
    })
    return arr.slice(0, 60)
  }, [events])

  return (
    <div className="rail-block">
      <div className="rb-head"><span className="icon" />LIVE ACTIVITY</div>
      <div className="act-list" aria-live="polite">
        {sorted.map((e) => (
          <div className="act-item" key={e.id}>
            <span className="a-icon" style={{ background: ACTIVITY_COLOR[e.type] }} />
            <div className="a-body" onClick={() => e.agentId != null && onOpenAgent(e.agentId)}
              style={e.agentId != null ? { cursor: 'pointer' } : undefined}>
              <div className="a-label">
                {e.agentType ? `#${e.agentId} ${CLASS_LABEL[e.agentType]}` : e.type.toUpperCase()}
                {' · '}{signChar(e.amount)}{e.amount != null ? `$${e.amount.toFixed(2)} · ` : ''}{e.label}
              </div>
              <div className="a-detail">{e.detail}</div>
            </div>
            <span className="a-time">{timeStr(e.timestamp)}</span>
          </div>
        ))}
        {sorted.length === 0 && (
          <div className="act-item"><div className="a-body"><div className="a-label dim">waiting for link…</div></div></div>
        )}
      </div>
    </div>
  )
}