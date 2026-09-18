import { memo, useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import type { Transaction } from '../../types/system'

interface Props {
  transactions: Transaction[]
}

/** Capital trajectory — the treasury balance over the last 50 ledger entries. */
export default memo(function CapitalFlow({ transactions }: Props) {
  const data = useMemo(() => {
    const sorted = [...transactions].sort((a, b) => a.id - b.id).slice(-50)
    return sorted.map((t) => ({
      id: t.id,
      cap: +t.balance_after.toFixed(2),
      amt: +t.amount.toFixed(2),
    }))
  }, [transactions])

  if (data.length === 0) {
    return (
      <div className="rail-block">
        <div className="rb-head">CAPITAL FLOW</div>
        <div className="dim mono" style={{ fontSize: 11 }}>no ledger data</div>
      </div>
    )
  }

  return (
    <div className="rail-block">
      <div className="rb-head">CAPITAL FLOW</div>
      <div className="chart-box" style={{ height: 96 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="capFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00D26A" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#00D26A" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis dataKey="id" hide />
            <YAxis hide domain={['auto', 'auto']} />
            <Tooltip
              contentStyle={{ background: '#0D1219', border: '1px solid #1E2D3D', borderRadius: 6, fontFamily: 'IBM Plex Mono', fontSize: 10 }}
              labelStyle={{ color: '#697789' }}
              itemStyle={{ color: '#E8EDF3' }}
              formatter={(v: any) => [`$${Number(v).toFixed(2)}`, 'balance']}
            />
            <Area type="monotone" dataKey="cap" stroke="#00D26A" strokeWidth={1.5} fill="url(#capFill)" isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
})