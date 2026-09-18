import { useState, useMemo } from 'react'
import { useSystem } from '../../services/useSystem'
import TopBar from './TopBar'
import LeftNav from './LeftNav'
import SystemMap from './SystemMap'
import RightInspector from './RightInspector'
import AgentTable from './AgentTable'
import TaskList from './TaskList'
import EvolutionTree from './EvolutionTree'
import MemoryView from './MemoryView'
import RevenueView from './RevenueView'
import LiveTelemetry from './LiveTelemetry'

export type AppView = 'map' | 'activity' | 'agents' | 'tasks' | 'research' | 'content' | 'product' | 'fabrication' | 'revenue' | 'treasury' | 'memory' | 'learning' | 'experiments' | 'evolution' | 'lineage' | 'performance' | 'risk' | 'quality' | 'logs'

export default function CommandCenterV2() {
  const { snapshot, connected, _tick } = useSystem()

  // Navigation state
  const [view, setView] = useState<AppView>('map')

  // Inspector state: can be a department ('domain_XXX') or an agent ('agent_XXX')
  const [inspectedEntity, setInspectedEntity] = useState<string | null>(null)

  // Active domain/agent object extraction for the inspector
  const activeDomain = useMemo(() => {
    if (inspectedEntity?.startsWith('domain_')) {
      const k = inspectedEntity.split('_')[1]
      return snapshot.domains.find(d => d.key === k) || null
    }
    return null
  }, [inspectedEntity, snapshot.domains])

  const activeAgent = useMemo(() => {
    if (inspectedEntity?.startsWith('agent_')) {
      const id = parseInt(inspectedEntity.split('_')[1], 10)
      return snapshot.allAgents.find(a => a.id === id) || null
    }
    return null
  }, [inspectedEntity, snapshot.allAgents])

  const onSelectEntity = (entityId: string) => {
    setInspectedEntity(entityId)
  }

  // Determine what to render in center
  const renderCenter = () => {
    switch (view) {
      case 'map':
        return <SystemMap snapshot={snapshot} onSelectNode={onSelectEntity} activeNode={inspectedEntity} />
      case 'agents':
        return <AgentTable agents={snapshot.allAgents} onSelectAgent={(id) => onSelectEntity(`agent_${id}`)} />
      case 'tasks':
        return <TaskList tasks={snapshot.tasks} experiments={snapshot.experiments} />
      case 'evolution':
      case 'lineage':
        return <EvolutionTree agents={snapshot.allAgents} onSelectAgent={(id) => onSelectEntity(`agent_${id}`)} />
      case 'memory':
        return <MemoryView memory={snapshot.learning} />
      case 'revenue':
      case 'treasury':
        return <RevenueView snapshot={snapshot} />
      default:
        // Fallback to map or placeholder
        return (
          <div className="flex-col h-full center dim mono uppercase p-8">
            <div>{view} â€” VIEW NOT YET IMPLEMENTED</div>
            <div className="mt-4"><button className="btn" onClick={() => setView('map')}>RETURN TO CORE</button></div>
          </div>
        )
    }
  }

  return (
    <div className="layout-root">
      <TopBar snapshot={snapshot} connected={connected} />
      
      <div className="layout-body">
        <LeftNav activeView={view} onView={setView} />
        
        <div className="layout-center">
          <div className="center-content">
            {renderCenter()}
          </div>
          
          <LiveTelemetry events={snapshot.activity} />
        </div>
        
        <RightInspector 
          domain={activeDomain} 
          agent={activeAgent} 
          snapshot={snapshot}
          onClose={() => setInspectedEntity(null)}
          onSelectAgent={(id) => onSelectEntity(`agent_${id}`)}
        />
      </div>
    </div>
  )
}
