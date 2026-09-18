import type { ActivityEvent } from '../../types/system'
import { fmtNum } from '../../services/useSystem'

export default function LiveTelemetry({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="v2-telemetry">
      <div className="vt-title">LIVE SYSTEM ACTIVITY</div>
      <div className="vt-stream">
        {events.slice(0, 50).map((ev, i) => (
          <div key={i} className="vt-event">
            <span className="vt-time">{new Date(ev.timestamp).toLocaleTimeString()}</span>
            <span className="vt-agent">{ev.agentType ? `${ev.agentType}-${ev.agentId}` : 'SYSTEM'}</span>
            <span className="vt-label" style={{ color: ev.type === 'risk' ? 'var(--red)' : ev.type === 'learning' ? 'var(--cyan)' : 'var(--text-primary)' }}>{ev.label}</span>
            <span className="vt-detail ghost">{ev.detail}</span>
            {ev.amount && <span className="vt-amt">{fmtNum(ev.amount)}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
