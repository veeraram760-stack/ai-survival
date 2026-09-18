/* ─────────────────────────────────────────────────────────
   AI Survival · Domain API clients
   Thin wrappers over rest.ts, one per backend resource.
   ───────────────────────────────────────────────────────── */

import { apiOrNull, API_BASE } from './rest'
import type {
  CapitalResponse, SystemStateResponse, AgentResponse,
  Transaction, Decision, Experiment, RiskEvent,
  LearningMemory, PerformanceData, HierarchyResponse,
  TaskStats, WithdrawalStatus, LineageNode,
} from '../types/system'

// ── Core (fetched every cycle) ──────────────────────────
export const fetchCapital      = () => apiOrNull<CapitalResponse>('/capital')
export const fetchSystemState  = () => apiOrNull<SystemStateResponse>('/system/state')
export const fetchAgents       = () => apiOrNull<AgentResponse[]>('/agents')

// ── Secondary (fetched every cycle, batched) ────────────
export const fetchTransactions = (limit = 100) =>
  apiOrNull<Transaction[]>(`/transactions?limit=${limit}`)
export const fetchDecisions    = (limit = 100) =>
  apiOrNull<Decision[]>(`/decisions?limit=${limit}`)
export const fetchRiskEvents   = (limit = 50) =>
  apiOrNull<RiskEvent[]>(`/risk/events?limit=${limit}`)
export const fetchLearning     = (limit = 50) =>
  apiOrNull<LearningMemory[]>(`/learning/memory?limit=${limit}`)
export const fetchExperiments  = (limit = 100) =>
  apiOrNull<Experiment[]>(`/experiments?limit=${limit}`)
export const fetchTasksStats   = () => apiOrNull<TaskStats>('/tasks/stats')

// ── Selection-only (fetched on user action) ─────────────
export const fetchLineage      = (id: number) =>
  apiOrNull<LineageNode>(`/agents/${id}/lineage`)
export const fetchPerformance  = (id: number) =>
  apiOrNull<PerformanceData>(`/performance/${id}`)
export const fetchTopPerformers = (limit = 10) =>
  apiOrNull<PerformanceData[]>(`/performance/top?limit=${limit}`)
export const fetchHierarchy    = () => apiOrNull<HierarchyResponse>('/hierarchy')
export const fetchWithdrawal   = () => apiOrNull<WithdrawalStatus>('/withdrawal/status')
export const fetchRevenueStrategies = () => apiOrNull<any[]>('/revenue/strategies')
export const fetchRevenueAgents     = () => apiOrNull<any[]>('/revenue/agents')
export const fetchRevenuePerf       = () => apiOrNull<any[]>('/revenue/performance')
export const fetchSelfImproveHist   = (limit = 10) =>
  apiOrNull<any[]>(`/self-improve/history?limit=${limit}`)

// ── Write actions (POST) ────────────────────────────────
export async function postTask(agentId: number, taskType: string) {
  const res = await fetch(`${API_BASE}/agents/${agentId}/tasks?task_type=${taskType}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  return res.ok
}

export async function postSelfImproveCycle() {
  const res = await fetch(`${API_BASE}/self-improve/cycle`, { method: 'POST' })
  return res.ok
}
