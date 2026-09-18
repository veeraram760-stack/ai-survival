import type { LearningMemory } from '../../types/system'

export default function MemoryView({ memory }: { memory: LearningMemory[] }) {
  return (
    <div className="v2-page">
      <div className="v2-page-header">SYSTEM KNOWLEDGE & MEMORY</div>
      
      <div className="mem-grid mt-6">
        {memory.map(m => (
          <div key={m.id} className="mem-card">
            <div className="mc-head">{m.category.toUpperCase()} // <span className="cyan">{m.key}</span></div>
            <div className="mc-body">{m.value}</div>
            <div className="mc-foot">CONFIDENCE: {(m.confidence * 100).toFixed(1)}%</div>
          </div>
        ))}
        {memory.length === 0 && <div className="dim p-4">NO MEMORIES IN INDEX</div>}
      </div>
    </div>
  )
}
