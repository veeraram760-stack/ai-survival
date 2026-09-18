import { memo } from 'react'
import type { AgentNode as AgentNodeT } from '../../types/system'
import { CLASS_COLOR } from './colors'
import { CLASS_LABEL } from '../../services/useSystem'

interface Props {
  agent: AgentNodeT
  onClick: (id: number) => void
}

/** A single orbiting agent sprite — coloured square with a status light. */
export default memo(function AgentNode({ agent, onClick }: Props) {
  const color = CLASS_COLOR[agent.type]
  const status = agent.status.toLowerCase()
  return (
    <button
      className={`anode s-${status}`}
      style={{ '--sd-color': color } as React.CSSProperties}
      onClick={(e) => { e.stopPropagation(); onClick(agent.id) }}
      aria-label={`${CLASS_LABEL[agent.type]} agent ${agent.id}, ROI ${agent.roi}`}
      title={`${CLASS_LABEL[agent.type]} · ROI ${agent.roi} · rev ${agent.revenue}`}
    >
      <span className="a-dot" />
      <span className="a-tip">
        {`#${agent.id} ${CLASS_LABEL[agent.type]}`} · gen {agent.generation}
        {'   '}ROI {agent.roi} · ${agent.revenue.toFixed(0)}
      </span>
    </button>
  )
})