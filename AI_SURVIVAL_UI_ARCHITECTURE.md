# AI SURVIVAL — COMMAND CENTER UI ARCHITECTURE

**Version:** 1.0.0 · **Date:** 2026-09-16
**Status:** Grounded in the live backend at `/api/v1` — every number rendered is a real value from the API or an explicit degraded connection state. Nothing is fabricated.

---

## 1. Mission

AI Survival is an **autonomous revenue-generation civilization**: 12 AI agents with reproduction, lineage, learning memory, an evolution engine, an experiment lab, and a capital treasury. It is not a SaaS dashboard and must not look like one.

The redesign reframes the operator surface as **a living command center** — not a page of cards, but the *bridge of the operation*. The primary experience is a **Command Orbit**: the system's 10 domains arranged as a functional map around a central core, with agents orbiting inside their domain, capital flowing along the links, and the whole thing breathing with live activity.

## 2. Design Stance (Must / Must-Not)

| Must | Must Not |
|---|---|
| Feel like an autonomous civilization / operating system | Look like a generic SaaS dashboard with sidebar + cards |
| Command Orbit / AI System Map as the primary visual | Copy any reference screenshot |
| Agent nodes (inhabited by real agents), department inspectors, agent inspector | "Profile card" grids |
| Live activity stream, survival status, capital flow | Static mock scroll pages |
| Evolution / lineage maps, memory layers, experiment lab | Fake revenue, fake status, fake agents |
| Thin system bar, minimal navigation | Heavy nav rail / tab sprawl |
| Everything driven by **real backend data** | Hardcoded financial values or statuses |

## 3. Backend Reality (verified 2026-09-16)

FastAPI app `backend/main.py` + `backend/api/router.py`, all routes under `/api/v1`. **No WebSocket or SSE endpoint exists** — push is not available. A shared `rest.ts` transport provides the seam where a WS channel can later swap in without touching components.

### 3.1 Canonical endpoints the command center consumes

| Domain | Endpoint | Shape (fields used) |
|---|---|---|
| Core | `GET /capital` | `total_capital, survival_reserve, operating_capital, growth_capital, net_profit, roi, real_revenue, simulated_revenue, total_expenses` |
| Core | `GET /system/state` | `current_mode (GROWTH/DEFENSIVE/SURVIVAL/DEAD), capital, reserve, operating, growth, total_agents, active_agents, daily_loss, weekly_loss` |
| Domains | `GET /agents` | `id, parent_id, generation, agent_type, strategy, budget, revenue, expenses, profit, roi, success_rate, status, risk_score, level, supervisor_id, days_alive` |
| Lineage | `GET /agents/{id}/lineage` | recursive `{id, type, level, children[]}` |
| Ledger | `GET /transactions?limit=100` | `id, timestamp, agent_id, category, action, amount, balance_before, balance_after, status` |
| Decisions | `GET /decisions?limit=100` | `id, agent_id, decision_type, approval_status, risk_assessment, executed_at` |
| Experiments | `GET /experiments?limit=100` | `hypothesis, status, budget, actual_result, conclusion` |
| Risk | `GET /risk/events?limit=50` | `event_type, agent_id, severity, details` |
| Learning | `GET /learning/memory?limit=50` | `category, key, value, confidence` |
| Memory | `GET /memory/short-term`, `/memory/project`, `/memory/long-term` | key/value stores |
| Performance | `GET /performance/top?limit=10`, `GET /performance/{id}` | `reliability_score, quality_score, task_count, success_count, failure_count, average_cost` |
| Hierarchy | `GET /hierarchy` | `supervisors[], specialists[]` (to_dict shapes) |
| Revenue | `GET /revenue/strategies`, `/revenue/agents`, `/revenue/performance` | per-agent + by-strategy revenue/expense/profit/roi |
| Tasks | `GET /tasks/stats`, `GET /tasks?limit=100` | `total, by_status`, task records |
| Self-improve | `GET /self-improve/history?limit=10` | improvement cycles |
| Report | `GET /withdrawal/status` | `threshold, real_revenue, remaining_to_threshold, eligible` |

### 3.2 Write actions surfaced (optional, wired to existing POST endpoints)

- `POST /agents/{id}/tasks?task_type=` (EARN/AFFILIATE/SALES adapters)
- `POST /agents/{id}/decisions?decision_type=`
- `POST /self-improve/cycle`
- `POST /revenue/agents/{id}/cycle`
- `POST /tasks` (queue a task)
- `POST /memory/*` (store)

## 4. Architecture

```
dashboard/src/
  main.tsx                     entry — mount <App/>
  App.tsx                      thin shell: <SystemBar/> + <CommandCenter/>; legacy routes kept
  theme/
    tokens.ts                  design tokens → CSS custom properties
    index.css                  token block + base/scrollbar/responsive primitives
  services/
    rest.ts                    API_BASE resolution + typed fetch + error normalization
    api.ts                     domain clients (capital, agents, lineage, ledger, memory, ...)
    usePoll.ts                 polling hook (interval, deps, refetch, stale-gap guard)
    useSystem.ts               10s orchestrator snapshot (capital+state+agents) → SystemSnapshot
  types/
    system.ts                  SystemSnapshot, AgentNode, DomainKey, Tx, ExperimentRow, ...
  components/
    system/SystemBar.tsx       thin top bar: SYNC pulse, mode, UTC clock, nav dots
    core/CommandCore.tsx       central core orb: survival gauge + capital readout
    orbit/CommandOrbit.tsx     the SVG/abs-positioned system map (10 domain nodes + core)
    orbit/DomainNode.tsx       a domain ring + its agent nodes
    orbit/AgentNode.tsx        orbiting agent sprite (class-colored, status-lit)
    orbit/links.ts             domain→domain flow animation math
    drawers/DepartmentInspector.tsx
    drawers/AgentInspector.tsx
    panels/ActivityStream.tsx
    panels/CapitalFlow.tsx
    panels/SurvivalPanel.tsx
    panels/EvolutionMap.tsx
    panels/MemoryLayers.tsx
    panels/ExperimentLab.tsx
    panels/QualityPanel.tsx
    panels/PerformancePanel.tsx
  legacy/                      untouched original pages (still routed but hidden)
```

### 4.1 Data flow

```
REST (poll every 10s) ──► usePoll ──► useSystem ──► SystemSnapshot (single immutable object)
                                                    ├─► CommandCore (survival, capital)
                                                    ├─► CommandOrbit (10 domains, agent swarms)
                                                    ├─► drawers (select domain/agent → /lineage, /performance)
                                                    ├─► ActivityStream (ledger + risk + decisions + learning fused)
                                                    └─► CapitalFlow / Survival / Evolution / Metrics
```

Every component is a **pure function of the snapshot**. Polling is centralised in `useSystem`; nothing else fetches. Selection state (active domain / active agent) lives in `App` and is passed down — no context library needed.

### 4.2 Connection states

`SystemSnapshot.connected`: `true | false | 'recovering'`.
- Live: all primary endpoints resolved → `SYNC` pulse green.
- Degraded: core endpoints down → explicit `NO LINK` state, previous data dimmed but visible, "last contact HH:MM:SS" caption. **Never fabricated numbers.** A small neutral `SAMPLE-LINK` badge may render canned demo frames only in the local-only sample rail, always labelled, never mixed into live numbers.

### 4.3 The 10 system domains (cluster of real modules, not invented)

| Key | Label | Agents (real) | Semantic color |
|---|---|---|---|
| exec | COMMAND | CEO | violet |
| research | RESEARCH | Research | cyan |
| market | MARKET | Market | cyan |
| content | CONTENT | Content, Affiliate, Sales | magenta |
| treasury | TREASURY | Finance | gold |
| risk | RISK | Risk Manager | red |
| learning | LEARNING | Learning | emerald |
| protocol | EVOLUTION | — (engine, not agent) | magenta |
| fabrication | FABRICATION | Factory | amber |
| product | PRODUCT | Digital Product | gold |

Evolution is rendered as an engine ring on the map (it reproduces agents and prunes lineages) rather than an agent cluster — its output is the lineage map.

## 5. Responsive contract

- **≥1440px:** full orbit, right reference rail (activity + survival).
- **900–1439px:** orbit scales, rail becomes bottom strip.
- **390–899px:** orbit becomes a horizontal scrollable lane; drawers become full-screen overlays; the rail stacks.
- Orbit uses absolute positioning on an `aspect-ratio` box, so it scales as one unit. Breakpoints only re-flow the shell, never the map's internal geometry.
- `prefers-reduced-motion: reduce` disables orbit rotation and flow-dash animation.

## 6. Performance & integrity

- Poll concurrency: `capital+state` → then `agents+ledger+risk+learning+decisions` in one `Promise.all` batch per cycle; lineage/performance fetched **on selection only**.
- The snapshot is a single object; React re-renders are cheap because nodes are memoised by `agent.id`.
- No secrets, keys, or URLs printed client-side beyond the public API base.
- No backend file is modified by this work.

## 7. Future seams

- `rest.ts` exposes `onSnapshot` semantics so a `/api/v1/stream` (SSE) or WebSocket channel can replace polling without component changes.
- Legacy routes remain mounted at their original paths — existing bookmarks/automations keep working.