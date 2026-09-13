# AI Survival System

Autonomous multi-agent AI business system starting with $50 capital.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Agents**: Modular Python agent classes with CEO, Risk Manager, and 11 specialized agents
- **GPU**: Modal integration for AI workloads
- **Frontend**: React + TypeScript + Vite + Recharts
- **Task Queue**: Redis + Celery
- **Deployment**: Docker Compose

## Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Start development
make dev
```

## Environment

Copy `.env.example` to `.env` and configure:

- `OPENAI_API_KEY` - For agent intelligence
- `ANTHROPIC_API_KEY` - Alternative LLM provider
- `MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` - For GPU workloads

## Agent Types

1. CEO - High-level resource allocation
2. Research - Market research and opportunity discovery
3. Content - Content creation and publishing
4. Affiliate - Affiliate marketing
5. Sales - Lead generation and outreach
6. Finance - Budget tracking and reporting
7. Risk Manager - Independent risk oversight
8. Digital Product - Product creation and sales
9. Market - Market analysis and paper trading
10. Experiment - Hypothesis testing
11. Learning - Knowledge management
12. Factory - Agent creation and mutation
13. Self-Improver - Analyzes own performance, identifies weaknesses, and plans improvements
14. Agent Developer - Analyzes target agents and develops/evolves their strategies and capabilities

## Dashboard

Visit `http://localhost:3000` after starting the system.

## Simulation Mode

The system runs in simulation mode by default. No real money is spent until explicitly configured.
