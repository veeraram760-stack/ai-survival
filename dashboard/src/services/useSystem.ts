/* ─────────────────────────────────────────────────────────
   AI Survival · System orchestrator
   Polls the backend, builds one immutable SystemSnapshot,
   and derives the 10 orbit domains + agent nodes.
   ───────────────────────────────────────────────────────── */

import { useEffect, useRef, useState, useCallback } from 'react'
import {
  fetchCapital, fetchSystemState, fetchAgents,
  fetchTransactions, fetchDecisions, fetchRiskEvents,
  fetchLearning, fetchExperiments, fetchTasksStats, fetchWithdrawal,
} from './api'
import type {
  SystemSnapshot, AgentResponse, AgentNode, DomainInfo,
  DomainKey, AgentClass, SystemMode, ActivityEvent,
} from '../types/system'

export const POLL_MS = 10000

// ── Class → domain mapping (the 10 orbit domains) ───────
export const CLASS_TO_DOMAIN: Record<AgentClass, DomainKey> = {
  CEO: 'exec',
  Research: 'research',
  Market: 'market',
  Experiment: 'protocol',
  Content: 'content',
  Affiliate: 'content',
  Sales: 'content',
  Finance: 'treasury',
  RiskManager: 'risk',
  Learning: 'learning',
  Factory: 'fabrication',
  DigitalProduct: 'product',
}

export const DOMAIN_META: Record<DomainKey, { label: string; color: string }> = {
  exec:        { label: 'COMMAND',     color: 'var(--violet)' },
  research:    { label: 'RESEARCH',    color: 'var(--cyan)' },
  market:      { label: 'MARKET',      color: 'var(--cyan)' },
  content:     { label: 'CONTENT',     color: 'var(--magenta)' },
  treasury:    { label: 'TREASURY',    color: 'var(--gold)' },
  risk:        { label: 'RISK',        color: 'var(--red)' },
  learning:    { label: 'LEARNING',    color: 'var(--green)' },
  protocol:    { label: 'EVOLUTION',   color: 'var(--magenta)' },
  fabrication: { label: 'FABRICATION', color: 'var(--amber)' },
  product:     { label: 'PRODUCT',     color: 'var(--gold)' },
}

export const DOMAIN_ORDER: DomainKey[] = [
  'exec', 'research', 'market', 'content',
  'treasury', 'risk', 'learning', 'protocol',
  'fabrication', 'product',
]

export const CLASS_LABEL: Record<AgentClass, string> = {
  CEO: 'CEO', Research: 'Research', Market: 'Market', Experiment: 'Lab',
  Content: 'Content', Affiliate: 'Affiliate', Sales: 'Sales',
  Finance: 'Finance', RiskManager: 'Risk', Learning: 'Learning',
  Factory: 'Factory', DigitalProduct: 'Digital',
}

const MODE_COLOR: Record<SystemMode, string> = {
  GROWTH: 'var(--green)',
  DEFENSIVE: 'var(--amber)',
  SURVIVAL: 'var(--red)',
  DEAD: 'var(--text-ghost)',
}

/**
 * A mostly-empty snapshot used as the initial render target.
 * All numeric fields are 0 so React never shows fabricated values.
 */
export function emptySnapshot(): SystemSnapshot {
  const domains = DOMAIN_ORDER.map<DomainInfo>((key) => ({
    key,
    ...DOMAIN_META[key],
    agents: [],
    totalRevenue: 0,
    totalExpenses: 0,
    totalProfit: 0,
  }))
  return {
    connected: false,
    lastContact: null,
    mode: 'GROWTH',
    capital: {
      total_capital: 0, survival_reserve: 0, operating_capital: 0,
      growth_capital: 0, total_revenue: 0, total_expenses: 0,
      realized_profit: 0, unrealized_pnl: 0, net_profit: 0, roi: 0,
      real_revenue: 0, real_expenses: 0, pending_real_revenue: 0,
      simulated_revenue: 0, simulated_expenses: 0,
    },
    state: {
      current_mode: 'GROWTH', capital: 0, reserve: 0, operating: 0,
      growth: 0, total_agents: 0, active_agents: 0, daily_loss: 0, weekly_loss: 0,
    },
    domains,
    allAgents: [],
    transactions: [],
    decisions: [],
    riskEvents: [],
    learning: [],
    experiments: [],
    performance: [],
    tasks: { total: 0, by_status: {} },
    withdrawal: null,
    activity: [],
  }
}

function toAgentNode(a: AgentResponse): AgentNode {
  return {
    id: a.id,
    type: a.agent_type,
    status: a.status,
    revenue: a.revenue,
    expenses: a.expenses,
    profit: a.profit,
    roi: a.roi,
    risk_score: a.risk_score,
    level: a.level,
    generation: a.generation,
    days_alive: a.days_alive,
    success_rate: a.success_rate,
    domain: CLASS_TO_DOMAIN[a.agent_type] ?? 'exec',
    parent_id: a.parent_id,
    strategy: a.strategy,
    budget: a.budget,
    experiments_count: a.experiments_count,
  }
}

/** Derive a fused activity stream from transactions/risk/decisions/learning. */
function buildActivity(s: {
  transactions: SystemSnapshot['transactions']
  riskEvents: SystemSnapshot['riskEvents']
  decisions: SystemSnapshot['decisions']
  learning: SystemSnapshot['learning']
  agents: AgentNode[]
}): ActivityEvent[] {
  const byId = new Map(s.agents.map((a) => [a.id, a]))
  const out: ActivityEvent[] = []

  for (const t of s.transactions) {
    const ag = t.agent_id != null ? byId.get(t.agent_id) : undefined
    out.push({
      id: `tx-${t.id}`,
      type: 'transaction',
      timestamp: t.timestamp,
      agentId: t.agent_id != null ? t.agent_id : null,
      agentType: ag?.type ?? null,
      label: t.action ? t.action.toUpperCase() : t.category?.toUpperCase() ?? 'TRANSFER',
      detail: `${t.category} · bal ${fmtNum(t.balance_after)}`,
      amount: t.amount,
    })
  }
  for (const r of s.riskEvents) {
    const ag = r.agent_id != null ? byId.get(r.agent_id) : undefined
    out.push({
      id: `risk-${r.id}`,
      type: 'risk',
      timestamp: new Date().toISOString(), // risk events carry no ts; stamp at fetch
      agentId: r.agent_id,
      agentType: ag?.type ?? null,
      label: r.event_type.toUpperCase(),
      detail: r.details,
      severity: r.severity,
    })
  }
  for (const d of s.decisions) {
    const ag = d.agent_id != null ? byId.get(d.agent_id) : undefined
    out.push({
      id: `dec-${d.id}`,
      type: 'decision',
      timestamp: d.executed_at,
      agentId: d.agent_id,
      agentType: ag?.type ?? null,
      label: d.decision_type.toUpperCase(),
      detail: d.approval_status,
    })
  }
  for (const l of s.learning) {
    out.push({
      id: `mem-${l.id}`,
      type: 'learning',
      timestamp: new Date().toISOString(), // learning rows carry no ts; stamp at fetch
      agentId: null,
      agentType: null,
      label: `MEMORY:${l.key.toUpperCase()}`,
      detail: l.value.slice(0, 60),
    })
  }
  return out
}

function fmtNum(n: number): string {
  if (Math.abs(n) >= 1000) return `$${(n / 1000).toFixed(1)}k`
  return `$${n.toFixed(2)}`
}

export function useSystem() {
  const [snapshot, setSnapshot] = useState<SystemSnapshot>(emptySnapshot())
  const [connected, setConnected] = useState<true | false | 'recovering'>(false)
  const mounted = useRef(true)

  const tick = useCallback(async () => {
    // Primary batch — the two core endpoints must both succeed to go live.
    const [cap, state, agents] = await Promise.all([
      fetchCapital(),
      fetchSystemState(),
      fetchAgents(),
    ])

    // Secondary batch — richer context if core is up.
    const [
      tx, decisions, risk, learning, experiments, tasks, withdrawal,
    ] = await Promise.all([
      fetchTransactions(),
      fetchDecisions(),
      fetchRiskEvents(),
      fetchLearning(),
      fetchExperiments(),
      fetchTasksStats(),
      fetchWithdrawal(),
    ])

    if (!mounted.current) return

    if (cap && state && agents) {
      const nodes = agents.map(toAgentNode)
      const domains = DOMAIN_ORDER.map<DomainInfo>((key) => {
        const list = nodes.filter((n) => n.domain === key)
        const tot = (f: (n: AgentNode) => number) =>
          list.reduce((acc, n) => acc + f(n), 0)
        return {
          key,
          ...DOMAIN_META[key],
          agents: list,
          totalRevenue: tot((n) => n.revenue),
          totalExpenses: tot((n) => n.expenses),
          totalProfit: tot((n) => n.profit),
        }
      })

      const next: SystemSnapshot = {
        connected: true,
        lastContact: new Date().toISOString(),
        mode: state.current_mode,
        capital: cap,
        state,
        domains,
        allAgents: nodes,
        transactions: tx ?? [],
        decisions: decisions ?? [],
        riskEvents: risk ?? [],
        learning: learning ?? [],
        experiments: experiments ?? [],
        performance: [],
        tasks: tasks ?? { total: 0, by_status: {} },
        withdrawal: withdrawal ?? null,
        activity: buildActivity({
          transactions: tx ?? [],
          riskEvents: risk ?? [],
          decisions: decisions ?? [],
          learning: learning ?? [],
          agents: nodes,
        }),
      }
      setConnected(true)
      setSnapshot(next)
    } else {
      // Degraded — keep previous values dimmed, mark disconnected.
      setConnected('recovering')
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { mounted.current = false; clearInterval(id) }
  }, [tick])

  return { snapshot, connected, tick }
}

export { MODE_COLOR, fmtNum }