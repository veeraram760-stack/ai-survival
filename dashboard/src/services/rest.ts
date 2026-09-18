/* ─────────────────────────────────────────────────────────
   AI Survival · REST transport layer
   Abstracts fetch + API_BASE resolution.
   Swap this module for a WS transport without touching components.
   ───────────────────────────────────────────────────────── */

const PROD = (import.meta as any).env.PROD

// Allow override from localStorage (office.html pattern)
function resolveBase(): string {
  try {
    const stored = localStorage.getItem('api_base')
    if (stored) return stored
  } catch { /* SSR / private browsing */ }
  return PROD ? '/api/v1' : 'http://localhost:8000/api/v1'
}

export let API_BASE = resolveBase()

export function setApiBase(url: string) {
  API_BASE = url
  try { localStorage.setItem('api_base', url) } catch { /* noop */ }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

/** Try fetch, return null on failure (for degraded-state wiring). */
export async function apiOrNull<T>(path: string): Promise<T | null> {
  try {
    return await apiFetch<T>(path)
  } catch {
    return null
  }
}
