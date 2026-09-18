import type { SystemSnapshot } from '../../types/system'
import { fmtNum } from '../../services/useSystem'

export default function RevenueView({ snapshot }: { snapshot: SystemSnapshot }) {
  return (
    <div className="v2-page">
      <div className="v2-page-header">REVENUE ENGINE & CAPITAL FLOW</div>
      
      <div className="kpi-grid mt-6">
        <div className="kpi">
          <div className="k-key">TOTAL REVENUE</div>
          <div className="k-val pos">{fmtNum(snapshot.capital.total_revenue)}</div>
        </div>
        <div className="kpi">
          <div className="k-key">TOTAL EXPENSES</div>
          <div className="k-val neg">{fmtNum(snapshot.capital.total_expenses)}</div>
        </div>
        <div className="kpi">
          <div className="k-key">OPERATING CAPITAL</div>
          <div className="k-val">{fmtNum(snapshot.capital.operating_capital)}</div>
        </div>
        <div className="kpi">
          <div className="k-key">SURVIVAL RESERVE</div>
          <div className="k-val">{fmtNum(snapshot.capital.survival_reserve)}</div>
        </div>
      </div>

      <div className="v2-page-header mt-8">CAPITAL MOVEMENT (RECENT)</div>
      
      <div className="v2-table mt-4">
        <div className="vt-head">
          <span>TIME</span>
          <span>ACTION</span>
          <span>AGENT</span>
          <span>AMOUNT</span>
          <span>NEW BALANCE</span>
        </div>
        {snapshot.transactions.slice(0, 50).map(t => (
          <div key={t.id} className="vt-row">
            <span className="dim">{new Date(t.timestamp).toLocaleTimeString()}</span>
            <span>{t.action || t.category}</span>
            <span className="ghost">{t.agent_id ? `AGENT-${t.agent_id}` : 'SYSTEM'}</span>
            <span className={t.amount >= 0 ? 'pos' : 'neg'}>{fmtNum(t.amount)}</span>
            <span>{fmtNum(t.balance_after)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
