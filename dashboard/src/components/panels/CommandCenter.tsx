import { useState, useMemo } from 'react'
import { useSystem } from '../../services/useSystem'
import SystemBar from '../system/SystemBar'
import CommandOrbit from '../orbit/CommandOrbit'
import DepartmentInspector from '../drawers/DepartmentInspector'
import AgentInspector from '../drawers/AgentInspector'
import ActivityStream from './ActivityStream'
import CapitalFlow from './CapitalFlow'
import SurvivalPanel from './SurvivalPanel'
import EvolutionMap from './EvolutionMap'
import MemoryLayers from './MemoryLayers'
import ExperimentLab from './ExperimentLab'
import RevenuePanel from './RevenuePanel'
import QualityPanel from './QualityPanel'
import PerformancePanel from './PerformancePanel'
import type { PanelKey } from './types'
import type { DomainInfo, DomainKey, AgentNode } from '../../types/system'

/** Command Center — the primary UI shell. */
export default function CommandCenter() {
  const { snapshot, connected, tick } = useSystem()

  // View state
  const [view, setView] = useState<PanelKey>('orbit')

  // Drawer state
  const [activeDomain, setActiveDomain] = useState<DomainInfo | null>(null)
  const [activeAgentId, setActiveAgentId] = useState<number | null>(null)

  // Derive active agent for inspector from agent list (always fresh)
  const resolvedAgent: AgentNode | null = useMemo(() => {
    if (activeAgentId == null) return null
    return snapshot.allAgents.find((a) => a.id === activeAgentId) ?? null
  }, [activeAgentId, snapshot.allAgents])

  const openAgent = (id: number) => {
    setActiveAgentId(id)
  }

  const openDomain = (key: DomainKey) => {
    setActiveDomain(snapshot.domains.find((d) => d.key === key) ?? null)
  }

  const isOrbitView = view === 'orbit'

  return (
    <div className={`cc ${!connected ? 'down' : ''}`}>
      <SystemBar
        mode={snapshot.state.current_mode}
        connected={connected}
        onRefresh={tick}
        view={view}
        onView={setView}
      />

      <div className="cc-main">
        {isOrbitView ? (
          <>
            <div className="cc-orbit">
              <CommandOrbit
                snapshot={snapshot}
                connected={connected}
                activeDomain={activeDomain?.key ?? null}
                onOpenDomain={openDomain}
                onOpenAgent={openAgent}
                onView={setView}
              />
            </div>

            <div className="cc-rail">
              <ActivityStream events={snapshot.activity} onOpenAgent={openAgent} />
              <CapitalFlow transactions={snapshot.transactions} />
              <SurvivalPanel
                capital={snapshot.capital}
                state={snapshot.state}
                withdrawal={snapshot.withdrawal}
                connected={connected === true}
                lastContact={snapshot.lastContact}
              />
            </div>
          </>
        ) : (
          <div className="panel-view" style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
            {view === 'lineage' && (
              <EvolutionMap agents={snapshot.allAgents} onOpenAgent={openAgent} />
            )}
            {view === 'memory' && <MemoryLayers />}
            {view === 'lab' && <ExperimentLab experiments={snapshot.experiments} agents={snapshot.allAgents} />}
            {view === 'revenue' && <RevenuePanel agents={snapshot.allAgents} />}
            {view === 'qa' && <QualityPanel agents={snapshot.allAgents} />}
            {view === 'perf' && <PerformancePanel agents={snapshot.allAgents} />}
          </div>
        )}
      </div>

      {/* Drawers */}
      {activeDomain && (
        <DepartmentInspector
          domain={activeDomain}
          snapshot={snapshot}
          onOpenAgent={openAgent}
          onClose={() => setActiveDomain(null)}
          onOpenPanel={setView}
        />
      )}

      {resolvedAgent && (
        <AgentInspector
          agent={resolvedAgent}
          transactions={snapshot.transactions}
          onOpenParent={openAgent}
          onClose={() => setActiveAgentId(null)}
        />
      )}
    </div>
  )
}
