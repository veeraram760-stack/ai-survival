# AI SURVIVAL — DESIGN SYSTEM

**Version:** 1.0.0 · **Date:** 2026-09-16

---

## 1. Colour

Everything is derived from **function**, never decoration. The system is near-black: the operator is looking at a command surface in a dark room.

### Backgrounds (darkest → lightest)

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#05070A` | body ground — the room itself |
| `--bg-surface` | `#080C11` | panels, drawers, the map's working surface |
| `--bg-elevated` | `#0D1219` | cards, dropdowns, popover content |
| `--bg-overlay` | `#141C26` | modals, tooltip backgrounds |

### Borders & dividers

| Token | Hex | Usage |
|---|---|---|
| `--border-subtle` | `rgba(255,255,255,0.04)` | ambient dividers |
| `--border-default` | `#18212D` | panel edges, table rows |
| `--border-active` | `#1E2D3D` | focused elements, selected nodes |

### Text

| Token | Hex | Usage |
|---|---|---|
| `--text-primary` | `#E8EDF3` | numbers, headings, labels |
| `--text-secondary` | `#8896A6` | body, descriptions |
| `--text-muted` | `#697789` | timestamps, secondary info |
| `--text-ghost` | `#3A4757` | placeholder, disabled |

### Semantic / state

| Token | Hex | Class | Meaning |
|---|---|---|---|
| `--green` | `#00D26A` | `.g` | operating, positive P&L, success |
| `--amber` | `#F5A623` | `.a` | caution, defensive mode, warning |
| `--red` | `#FF3B5C` | `.r` | danger, negative P&L, failure |
| `--cyan` | `#00B4D8` | `.c` | information, sync status |
| `--violet` | `#8B5CF6` | `.v` | CEO / executive, intelligence |
| `--magenta` | `#D946EF` | `.m` | evolution, content, reproduction |
| `--gold` | `#FFD700` | `.gl` | finance, treasury, capital |
| `--blue` | `#3B82F6` | `.bl` | learning, memory, knowledge |

### Agent class colours (orbit nodes, badges, sparklines)

```
CEO          → violet    Research    → cyan       Market       → cyan
Content      → magenta   Affiliate   → magenta    Sales        → magenta
Finance      → gold      Risk Mgr    → red        Learning     → emerald
Factory      → amber     Digital Pdt → gold       (all derived from semantic palette)
```

---

## 2. Typography

Three faces. One for code/data, one for system labels, one for body.

| Face | Weight(s) | Usage |
|---|---|---|
| IBM Plex Mono | 400, 500 | numbers, data readouts, code labels, all KPI values |
| Chakra Petch | 400, 600, 700 | headings, system labels, status badges, nav |
| IBM Plex Sans | 400, 500 | body text, descriptions, drawer content |

All sizes rem-based. Base: 14px on desktop, 13px on mobile.

| Role | Size | Line-height | Face |
|---|---|---|---|
| Caption | 0.75rem (12px) | 1.4 | IBM Plex Mono |
| Small | 0.8125rem (13px) | 1.5 | IBM Plex Mono |
| Body | 0.875rem (14px) | 1.6 | IBM Plex Sans |
| Subhead | 1rem (16px) | 1.4 | Chakra Petch 600 |
| Heading | 1.125rem (18px) | 1.3 | Chakra Petch 700 |
| Display | 1.5rem (24px) | 1.2 | Chakra Petch 700 |

---

## 3. Spacing & layout

Base unit: 4px. Every value is a multiple.

| Token | Value |
|---|---|
| `--sp-1` | 4px |
| `--sp-2` | 8px |
| `--sp-3` | 12px |
| `--sp-4` | 16px |
| `--sp-6` | 24px |
| `--sp-8` | 32px |
| `--sp-12` | 48px |
| `--sp-16` | 64px |

### Shell structure (desktop ≥1440px)

```
┌──────────────────────────────────────────────┐
│ SystemBar          36px height                │
├────────────────────────────┬─────────────────┤
│                            │  Right Rail      │
│    CommandOrbit            │  (Activity +     │
│    (flex: 1)               │   Survival +     │
│                            │   Capital)       │
│    ┌──────────┐            │  280px fixed     │
│    │ Core Orb │            │                  │
│    └──────────┘            │                  │
│                            │                  │
├────────────────────────────┴─────────────────┤
│ BottomStrip (agent chips, compact metrics)   │
└──────────────────────────────────────────────┘
```

- Orbit area: `flex: 1`, min-width 600px.
- Right rail: 280px fixed, scrollable vertically.
- Bottom strip: 48px fixed, horizontal scroll if needed.
- SystemBar: 36px fixed, full width.

---

## 4. Components

### 4.1 SystemBar

Thin, 36px. Left: `◉ SYNC` pulse (green/red/amber). Center: mode badge (GROWTH/DEFENSIVE/SURVIVAL/DEAD). Right: UTC clock. Background: `--bg-surface`, bottom border: `--border-subtle`.

### 4.2 CommandCore (center orb)

A 180×180px circular element at the orbit's center. Concentric rings:
- Outer ring: survival gauge (arc = capital vs threshold, green→amber→red)
- Inner fill: total capital in Chakra Petch 700 24px
- Below number: system mode in caption size
- `--bg-base` background, subtle radial glow matching mode colour

### 4.3 DomainNode (orbit ring)

Each domain is a 100×100px rounded container:
- Ring border in domain semantic colour
- Domain label (Chakra Petch 600, 12px, uppercase)
- Agent count badge (top-right, mono 10px)
- Inside: 1–4 AgentNode sprites
- On hover: expand to 140×140, show domain summary (revenue/expense/profit)
- On click: open DepartmentInspector drawer

### 4.4 AgentNode (orbiting dot)

8×8px square, rounded 2px:
- Background: agent class colour
- Status glow: ALIVE → solid glow; TESTING → pulse; PAUSED → dim; TERMINATED → grey ×
- On hover: tooltip with agent name, ROI, revenue
- On click: open AgentInspector drawer

### 4.5 DepartmentInspector (drawer)

Slides in from right, 400px wide, full height, `--bg-surface` background:
- Header: domain name + colour bar
- Stats row: revenue / expense / profit / ROI (mono, green/red)
- Agent list: name, status dot, revenue, ROI, click → AgentInspector
- Memory layer for this domain (if learning domain)
- Experiment list (if content/research domain)

### 4.6 AgentInspector (drawer)

Slides in from right, 360px wide, overlays DepartmentInspector:
- Header: agent class badge + name + generation
- KPIs: revenue, expenses, profit, ROI, success rate, risk score, days alive
- Mini sparkline: revenue over last N transactions
- Lineage mini-map: parent → this agent → children (3 levels)
- Performance: reliability_score, quality_score, task_count
- Actions: `POST /agents/{id}/tasks?task_type=EARN`

### 4.7 ActivityStream (right rail, top)

Scrollable list of fused events: transactions + risk events + decisions + learning:
- Each row: timestamp (mono 10px), colour-coded icon, description
- New entries slide in at top, old ones scroll down
- Max 50 visible, virtual-scroll for performance

### 4.8 CapitalFlow (right rail, middle)

A small horizontal area chart (recharts `AreaChart`):
- Two lines: real_revenue (solid green) and simulated_revenue (dashed cyan)
- Area fill: very low opacity matching line colour
- X-axis: timestamps; Y-axis: dollar amounts
- 50 data points from last 50 transactions

### 4.9 SurvivalPanel (right rail, bottom)

Compact readout:
- Mode badge (coloured pill)
- Capital vs threshold progress bar
- `remaining_to_threshold` in mono
- `eligible` badge (green check / red ×)

### 4.10 EvolutionMap (panel, accessed from orbit "EVOLUTION" ring)

Full panel view:
- Lineage tree: recursive `GET /agents/{id}/lineage` rendered as vertical tree
- Nodes: agent class colour, generation number
- Edges: thin lines, colour = parent's colour
- Click node → AgentInspector

### 4.11 MemoryLayers (panel, accessed from LEARNING domain)

Three columns:
- Short-term: scrollable key/value list
- Project: scrollable key/value list
- Long-term: scrollable key/value list
- Each has confidence bar (width = confidence × 100%)

### 4.12 ExperimentLab (panel)

Table: hypothesis, status (badge), budget (mono), actual_result, conclusion.
Rows sorted by most recent. Status badges coloured: RUNNING=blue, COMPLETED=green, FAILED=red.

### 4.13 QualityPanel (panel)

Top 10 agents by reliability_score, shown as horizontal bar chart:
- Bar fill: reliability_score / 1.0, coloured by agent class
- Labels: agent name + quality_score

### 4.14 PerformancePanel (panel)

Recharts `BarChart`: task_count by agent, stacked success (green) / failure (red).

---

## 5. Motion

All durations in ms. No easing longer than 400ms. `prefers-reduced-motion: reduce` disables everything below.

| Animation | Duration | Easing | What |
|---|---|---|---|
| Orbit rotation | 120s per full turn | linear | entire orbit container rotates slowly |
| Domain expand | 200ms | ease-out | hover → 140×140 |
| Drawer slide | 250ms | ease-out | right → left entrance |
| Activity entry | 180ms | ease-in | new event appears at top |
| Capital flow update | 400ms | ease-in-out | chart re-renders with smooth transition |
| Pulse (sync, status) | 1.5s infinite | ease-in-out | opacity 0.4→1→0.4 |
| Flow dash (domain links) | 2s infinite linear | — | `stroke-dashoffset` animation on SVG links |

---

## 6. Responsive breakpoints

| Name | Width | Behaviour |
|---|---|---|
| Desktop | ≥1440px | Full layout as described |
| Tablet | 900–1439px | Right rail → bottom strip; orbit scales to fit |
| Mobile | 390–899px | Orbit → horizontal scroll lane; drawers → full-screen overlay; bottom strip stacks vertically |

Orbit is an `aspect-ratio: 1` container with `position: relative` children positioned as percentages. It scales naturally; breakpoints only re-flow the shell.

---

## 7. Accessibility

- All interactive elements have visible focus rings (2px `--cyan` offset 2px).
- Colour is never the only indicator — status icons/text always accompany colour.
- `aria-label` on all clickable orbit nodes.
- Drawer close via Escape key.
- Screen-reader announcements for live activity entries via `aria-live="polite"`.
- Reduced motion: all animations disabled.
- Minimum touch target: 44×44px on mobile.

---

## 8. Iconography

lucide-react, 16px default. Consistent stroke width 1.5. Colour inherited from `currentColor`.

Primary icons:
- `Activity`, `Zap`, `DollarSign`, `Users`, `Brain`, `FlaskConical`, `Shield`, `Cpu`, `Package`, `TrendingUp`, `TrendingDown`, `AlertTriangle`, `CheckCircle`, `XCircle`, `Clock`, `Radio`, `GitBranch`, `Database`, `Layers`, `Target`