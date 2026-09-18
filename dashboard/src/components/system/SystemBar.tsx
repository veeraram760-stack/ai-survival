import { useEffect, useState } from 'react'
import type { SystemMode } from '../../types/system'
import type { PanelKey } from '../panels/types'

export const MODE_RAW: Record<SystemMode, string> = {
  GROWTH: '#00D26A',
  DEFENSIVE: '#F5A623',
  SURVIVAL: '#FF3B5C',
  DEAD: '#3A4757',
}

const NAV: { key: PanelKey; label: string }[] = [
  { key: 'orbit', label: 'ORBIT' },
  { key: 'lineage', label: 'LINEAGE' },
  { key: 'memory', label: 'MEMORY' },
  { key: 'lab', label: 'LAB' },
  { key: 'revenue', label: 'REVENUE' },
  { key: 'qa', label: 'QA' },
  { key: 'perf', label: 'PERF' },
]

interface Props {
  connected: true | false | 'recovering'
  mode: SystemMode
  view: PanelKey
  onView: (v: PanelKey) => void
  onRefresh: () => void
}

export default function SystemBar({ connected, mode, view, onView, onRefresh }: Props) {
  const [clock, setClock] = useState('')
  useEffect(() => {
    const id = setInterval(() => {
      const d = new Date()
      const p = (n: number) => String(n).padStart(2, '0')
      setClock(`${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())} UTC`)
    }, 1000)
    return () => clearInterval(id)
  }, [])

  const syncClass = connected === true ? 'live' : connected === 'recovering' ? 'recovering' : 'down'
  const syncLabel = connected === true ? 'SYNC' : connected === 'recovering' ? 'RECOVERING' : 'NO LINK'

  return (
    <header className="sysbar">
      <span onClick={onRefresh} className={`sync ${syncClass}`} title="core link status — click to poll now">
        <span className="dot" /> {syncLabel}
      </span>
      <span className="sep xh" />
      <a className="brand" href="/" onClick={(e) => { e.preventDefault(); onView('orbit') }}>
        <span className="mark">◉</span> AI&nbsp;SURVIVAL
      </a>
      <span className="sep xh" />
      <span className="modebadge" style={{ color: MODE_RAW[mode], borderColor: `${MODE_RAW[mode]}55` }}>
        {mode}
      </span>

      <nav className="sysnav">
        {NAV.map((n) => (
          <a key={n.key} href="#" className={view === n.key ? 'on' : ''}
             onClick={(e) => { e.preventDefault(); onView(n.key) }}>{n.label}</a>
        ))}
      </nav>

      <span className="sep xh hide-mobile" />
      <span className="sysclock hide-mobile">{clock}</span>
    </header>
  )
}