import type { AppView } from './CommandCenterV2'

interface Props {
  activeView: AppView
  onView: (v: AppView) => void
}

const NAV_GROUPS = [
  {
    title: 'CORE',
    items: [
      { id: 'map', label: 'System Map' },
      { id: 'activity', label: 'Live Activity' },
      { id: 'agents', label: 'Agents' },
      { id: 'tasks', label: 'Tasks' },
    ]
  },
  {
    title: 'OPERATIONS',
    items: [
      { id: 'research', label: 'Research' },
      { id: 'content', label: 'Content' },
      { id: 'product', label: 'Product' },
      { id: 'fabrication', label: 'Fabrication' },
      { id: 'revenue', label: 'Revenue' },
      { id: 'treasury', label: 'Treasury' },
    ]
  },
  {
    title: 'INTELLIGENCE',
    items: [
      { id: 'memory', label: 'Memory' },
      { id: 'learning', label: 'Learning' },
      { id: 'experiments', label: 'Experiments' },
    ]
  },
  {
    title: 'EVOLUTION',
    items: [
      { id: 'evolution', label: 'Evolution' },
      { id: 'lineage', label: 'Lineage' },
      { id: 'performance', label: 'Performance' },
    ]
  },
  {
    title: 'CONTROL',
    items: [
      { id: 'risk', label: 'Risk' },
      { id: 'quality', label: 'Quality' },
      { id: 'logs', label: 'Logs' },
    ]
  }
]

export default function LeftNav({ activeView, onView }: Props) {
  return (
    <nav className="v2-nav">
      {NAV_GROUPS.map(g => (
        <div className="nav-group" key={g.title}>
          <div className="nav-group-title">{g.title}</div>
          {g.items.map(item => (
            <button 
              key={item.id} 
              className={`nav-item ${activeView === item.id ? 'on' : ''}`}
              onClick={() => onView(item.id as AppView)}
            >
              <div className="nav-ind" />
              {item.label}
            </button>
          ))}
        </div>
      ))}
    </nav>
  )
}
