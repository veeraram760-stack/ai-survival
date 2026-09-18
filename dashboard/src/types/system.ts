/* ─────────────────────────────────────────────────────────
   AI Survival · Command Center · Shared Types
   ───────────────────────────────────────────────────────── */

// ── System modes (from backend SystemMode enum) ──────────
export type SystemMode = 'GROWTH' | 'DEFENSIVE' | 'SURVIVAL' | 'DEAD'

// ── Agent statuses (from backend AgentStatus enum) ───────
export type AgentStatus =
  | 'ALIVE' | 'TESTING' | 'GROWING' | 'REPRODUCTION_READY'
  | 'PAUSED' | 'TERMINATED' | 'FAILED'

// ── Domain keys (the 10 orbit domains) ───────────────────
export type DomainKey =
  | 'exec' | 'research' | 'market' | 'content' | 'treasury'
  | 'risk' | 'learning' | 'protocol' | 'fabrication' | 'product'

// ── Agent class types (from backend agent_type) ──────────
export type AgentClass =
  | 'CEO' | 'Research' | 'Market' | 'Experiment'
  | 'Content' | 'Affiliate' | 'Sales' | 'Finance'
  | 'RiskManager' | 'Learning' | 'Factory' | 'DigitalProduct'

// ── Raw shapes from the API ──────────────────────────────
export interface CapitalResponse {
  total_capital: number
  survival_reserve: number
  operating_capital: number
  growth_capital: number
  total_revenue: number
  total_expenses: number
  realized_profit: number
  unrealized_pnl: number
  net_profit: number
  roi: number
  real_revenue: number
  real_expenses: number
  pending_real_revenue: number
  simulated_revenue: number
  simulated_expenses: number
}

export interface SystemStateResponse {
  current_mode: SystemMode
  capital: number
  reserve: number
  operating: number
  growth: number
  total_agents: number
  active_agents: number
  daily_loss: number
  weekly_loss: number
}

export interface AgentResponse {
  id: number
  parent_id: number | null
  generation: number
  agent_type: AgentClass
  strategy: string
  capabilities: string
  budget: number
  revenue: number
  expenses: number
  profit: number
  roi: number
  success_rate: number
  status: AgentStatus
  risk_score: number
  reproduction_permissions: boolean
  lifetime_revenue: number
  lifetime_expenses: number
  lifetime_profit: number
  days_alive: number
  experiments_count: number
  successful_experiments: number
  failed_experiments: number
  creation_timestamp: string
  terminated_at: string | null
  level: number
  supervisor_id: number | null
  autonomy_level: number
}

export interface Transaction {
  id: number
  timestamp: string
  agent_id: number
  category: string
  action: string
  amount: number
  balance_before: number
  balance_after: number
  status: string
}

export interface Decision {
  id: number
  agent_id: number
  decision_type: string
  approval_status: string
  risk_assessment: string
  executed_at: string
}

export interface Experiment {
  id: number
  agent_id: number
  hypothesis: string
  status: string
  budget: number
  actual_result: string | null
  conclusion: string | null
}

export interface RiskEvent {
  id: number
  event_type: string
  agent_id: number | null
  severity: string
  details: string
}

export interface LearningMemory {
  id: number
  category: string
  key: string
  value: string
  confidence: number
}

export interface PerformanceData {
  agent_id: number
  reliability_score: number
  quality_score: number
  task_count: number
  success_count: number
  failure_count: number
  average_cost: number
}

export interface HierarchyResponse {
  supervisors: AgentResponse[]
  specialists: AgentResponse[]
}

export interface TaskStats {
  total: number
  by_status: Record<string, number>
}

export interface WithdrawalStatus {
  threshold: number
  real_revenue: number
  remaining_to_threshold: number
  eligible: boolean
}

// ── Lineage tree (recursive) ─────────────────────────────
export interface LineageNode {
  id: number
  type: string
  level: string
  children: LineageNode[]
}

// ── Derived orbit types ──────────────────────────────────
export interface AgentNode {
  id: number
  type: AgentClass
  status: AgentStatus
  revenue: number
  expenses: number
  profit: number
  roi: number
  risk_score: number
  level: number
  generation: number
  days_alive: number
  success_rate: number
  domain: DomainKey
  parent_id?: number | null
  strategy?: string
  budget?: number
  experiments_count?: number
}

export interface DomainInfo {
  key: DomainKey
  label: string
  color: string
  agents: AgentNode[]
  totalRevenue: number
  totalExpenses: number
  totalProfit: number
}

export interface ActivityEvent {
  id: string
  type: 'transaction' | 'risk' | 'decision' | 'learning'
  timestamp: string
  agentId: number | null
  agentType: AgentClass | null
  label: string
  detail: string
  amount?: number
  severity?: string
}

export interface SystemSnapshot {
  connected: true | false | 'recovering'
  lastContact: string | null
  mode: SystemMode
  capital: CapitalResponse
  state: SystemStateResponse
  domains: DomainInfo[]
  allAgents: AgentNode[]
  transactions: Transaction[]
  decisions: Decision[]
  riskEvents: RiskEvent[]
  learning: LearningMemory[]
  experiments: Experiment[]
  performance: PerformanceData[]
  tasks: TaskStats
  withdrawal: WithdrawalStatus | null
  activity: ActivityEvent[]
}
