import { memo, useState, useEffect } from 'react'
import type { LearningMemory } from '../../types/system'
import { apiFetch } from '../../services/rest'

const PALETTE = ['var(--green)', 'var(--cyan)', 'var(--violet)', 'var(--magenta)', 'var(--amber)', 'var(--gold)']

interface MemoryLayer {
  label: string
  key: string
  data: LearningMemory[]
  color: string
}

export default memo(function MemoryLayers() {
  const [layers, setLayers] = useState<MemoryLayer[]>([])

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      try {
        const data = await apiFetch<LearningMemory[]>('/learning/memory?limit=120')
        if (!controller.signal.aborted) {
          const byCat = new Map<string, LearningMemory[]>()
          for (const m of data) {
            const cat = m.category || 'general'
            const list = byCat.get(cat) ?? []
            list.push(m)
            byCat.set(cat, list)
          }
          const cats = [...byCat.keys()].sort()
          setLayers(cats.map((c, i) => ({
            label: c.toUpperCase(),
            key: c,
            data: (byCat.get(c) ?? []).slice(0, 16),
            color: PALETTE[i % PALETTE.length],
          })))
        }
      } catch {
        if (!controller.signal.aborted) setLayers([])
      }
    }
    load()
    return () => controller.abort()
  }, [])

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="ph-title">MEMORY LAYERS</span>
        <span className="ph-sub">{layers.reduce((s, l) => s + l.data.length, 0)} entries</span>
      </div>

      <div className="mem-flex">
        {layers.map((layer) => (
          <div className="mem-col" key={layer.key}>
            <div className="mc-title" style={{ color: layer.color }}>{layer.label}</div>
            {layer.data.length > 0 ? layer.data.map((m) => (
              <div className="mem-item" key={m.id}>
                <div className="mi-key">{m.key}</div>
                <div className="mi-val">{String(m.value).slice(0, 120)}</div>
                <div className="dim" style={{ fontSize: 9, marginTop: 2 }}>
                  {m.category} · conf {Number(m.confidence).toFixed(2)}
                </div>
              </div>
            )) : (
              <div className="mem-item dim mono" style={{ fontSize: 11 }}>no entries</div>
            )}
          </div>
        ))}
        {layers.length === 0 && (
          <div className="mem-col">
            <div className="mc-title">NO MEMORY</div>
            <div className="mem-item dim mono" style={{ fontSize: 11 }}>no memory entries recorded</div>
          </div>
        )}
      </div>
    </div>
  )
})