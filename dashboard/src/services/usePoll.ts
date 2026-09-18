/* ─────────────────────────────────────────────────────────
   AI Survival · Polling hook
   Fires an async fetcher on interval; returns latest result + status.
   ───────────────────────────────────────────────────────── */

import { useEffect, useRef, useState, useCallback } from 'react'

interface PollResult<T> {
  data: T | null
  loading: boolean
  lastUpdated: number | null
}

export function usePoll<T>(
  fetcher: () => Promise<T | null>,
  intervalMs: number,
  deps: readonly unknown[] = []
): PollResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<number | null>(null)
  const mounted = useRef(true)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const tick = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      if (!mounted.current) return
      if (result !== null) {
        setData(result)
        setLastUpdated(Date.now())
      }
    } catch {
      // swallow — apiOrNull handles errors
    } finally {
      if (mounted.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    tick()
    const id = setInterval(tick, intervalMs)
    return () => { mounted.current = false; clearInterval(id) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps])

  return { data, loading, lastUpdated }
}
