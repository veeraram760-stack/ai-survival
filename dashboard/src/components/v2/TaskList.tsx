import type { TaskStats, Experiment } from '../../types/system'

interface Props {
  tasks: TaskStats
  experiments: Experiment[]
}

export default function TaskList({ tasks, experiments }: Props) {
  return (
    <div className="v2-page">
      <div className="v2-page-header">TASK & EXPERIMENT QUEUE</div>
      
      <div className="v2-table mt-4">
        <div className="vt-head cols-task">
          <span>TASK ID</span>
          <span>DESCRIPTION</span>
          <span>STATUS</span>
          <span>AGENT</span>
          <span>BUDGET</span>
        </div>
        {experiments.map(e => (
          <div key={e.id} className="vt-row cols-task bg-base">
            <span className="cyan">EXP-{e.id}</span>
            <span>{e.hypothesis}</span>
            <span className={e.status === 'RUNNING' ? 'pos' : e.status === 'FAILED' ? 'neg' : 'dim'}>{e.status}</span>
            <span className="ghost">AGENT-{e.agent_id}</span>
            <span className="ghost">${e.budget.toFixed(2)}</span>
          </div>
        ))}
        {experiments.length === 0 && (
          <div className="p-4 dim">NO ACTIVE TASKS OR EXPERIMENTS</div>
        )}
      </div>

      <div className="mt-8 dim">
        Global Tasks Processed: {tasks?.total || 0}
      </div>
    </div>
  )
}
