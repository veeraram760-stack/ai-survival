import { useMemo } from 'react'
import type { SystemSnapshot } from '../../types/system'
import { fmtNum } from '../../services/useSystem'

export default function TopBar({ snapshot, connected }: { snapshot: SystemSnapshot, connected: any }) {
  // Derive running tasks if possible. Since we only have tasks.by_status:
  const runningTasks = (snapshot.tasks?.by_status?.RUNNING || 0) + (snapshot.experiments?.filter(e => e.status === 'RUNNING').length || 0)
  
  const riskLabel = snapshot.domains.find(d => d.key === 'risk')?.totalProfit < 0 ? 'HIGH' : 'LOW'
  
  const totalAgents = snapshot.allAgents.length
  const activeAgents = snapshot.allAgents.filter(a => a.status === 'ALIVE').length

  const uptimeStr = useMemo(() => {
    // mock uptime for now if backend doesn't supply it. It isn't provided directly in SystemState.
    return '12d 06h'
  }, [])

  return (
    <header className="v2-topbar">
      <div className="tb-left">
        <span className="brand-title">AI SURVIVAL</span>
        <span className={`status-dot ${connected === true ? 'live' : 'down'}`} />
        <span className="brand-statustext">{connected === true ? 'SYSTEM ONLINE' : 'DEGRADED'}</span>
      </div>

      <div className="tb-center">
        <div className="tb-metric">
          <span className="tbm-key">AGENTS</span>
          <span className="tbm-val">{activeAgents} <span className="dim">/ {totalAgents}</span></span>
        </div>
        <div className="tb-sep" />
        <div className="tb-metric">
          <span className="tbm-key">TASKS</span>
          <span className="tbm-val">{runningTasks} RUNNING</span>
        </div>
        <div className="tb-sep" />
        <div className="tb-metric">
          <span className="tbm-key">CAPITAL</span>
          <span className="tbm-val tbm-capital">{fmtNum(snapshot.capital.total_capital)}</span>
        </div>
        <div className="tb-sep" />
        <div className="tb-metric">
          <span className="tbm-key">REVENUE</span>
          <span className="tbm-val pos">{fmtNum(snapshot.capital.total_revenue)}</span>
        </div>
        <div className="tb-sep" />
        <div className="tb-metric">
          <span className="tbm-key">RISK</span>
          <span className={`tbm-val ${riskLabel === 'LOW' ? 'pos' : 'neg'}`}>{riskLabel}</span>
        </div>
        <div className="tb-sep" />
        <div className="tb-metric">
          <span className="tbm-key">UPTIME</span>
          <span className="tbm-val">{uptimeStr}</span>
        </div>
      </div>

      <div className="tb-right">
        <div className="tb-btn pulse-live">â—  LIVE</div>
        <div className="tb-btn icon">âš³</div>
        <div className="tb-btn icon">âš™</div>
      </div>
    </header>
  )
}
