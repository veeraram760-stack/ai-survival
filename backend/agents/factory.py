from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from .base import Agent
from .specialist import Specialist, map_to_specialist_type
from .supervisor import Supervisor, create_supervisor
from .self_improver import SelfImproverAgent
from .developer import AgentDeveloper
from .revenue_agent import RevenueAgent, RevenueAgentFactory
from ..models.database import AgentLineage, ReproductionEvent, AgentDeath, AgentStatus
from ..risk.manager import RiskManager
from config.settings import settings
import uuid


class AgentFactory:
    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    async def create_agent(
        self,
        db,
        agent_type: str,
        strategy: str = "default",
        parent_id: Optional[str] = None,
        generation: int = 0,
        capabilities: Optional[List[str]] = None,
        mutations: Optional[Dict[str, Any]] = None,
        level: str = "SPECIALIST",
        supervisor_id: Optional[str] = None,
    ) -> Agent:
        approved, reason = await self.risk_manager.evaluate_agent_creation(db, agent_type)
        if not approved:
            raise RuntimeError(f"Agent creation denied: {reason}")

        agent_id = f"{agent_type.upper()}-{str(uuid.uuid4())[:8]}"

        if level == "SUPERVISOR":
            agent = create_supervisor(agent_id=agent_id, department=agent_type.upper())
            agent.strategy = strategy
            if capabilities:
                agent.capabilities = capabilities
        elif agent_type == "self_improver":
            agent = SelfImproverAgent(agent_id=agent_id, agent_type=agent_type, strategy=strategy)
        elif agent_type == "agent_developer":
            agent = AgentDeveloper(agent_id=agent_id, agent_type=agent_type, strategy=strategy)
        elif agent_type == "revenue":
            # Create revenue agent with specific strategy
            strategy_name = strategy if strategy in ["affiliate_content", "digital_products", "print_on_demand", "shopify_store", "multi_channel"] else "affiliate_content"
            agent = RevenueAgentFactory.create_agent(agent_id, strategy_name, parent_id)
        else:
            mapped_type = map_to_specialist_type(agent_type)
            agent = Specialist(
                agent_id=agent_id,
                agent_type=mapped_type,
                strategy=strategy,
                capabilities=capabilities,
            )
            agent.supervisor_id = supervisor_id
            agent.level = "SPECIALIST"

        agent.generation = generation
        agent.parent_id = parent_id

        if mutations:
            for key, value in mutations.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)

        await agent.persist(db)

        lineage = AgentLineage(
            id=str(uuid.uuid4()),
            ancestor_id=agent_id if not parent_id else parent_id,
            descendant_id=agent_id,
            depth=generation,
        )
        db.add(lineage)

        if parent_id:
            event = ReproductionEvent(
                id=str(uuid.uuid4()),
                parent_id=parent_id,
                child_id=agent_id,
                reproduction_type="clone" if mutations is None else "mutated_clone",
                mutations=mutations,
            )
            db.add(event)

        return agent

    async def clone_agent(
        self, db, parent: Agent, mutations: Optional[Dict[str, Any]] = None
    ) -> Agent:
        level = getattr(parent, "level", "SPECIALIST")
        return await self.create_agent(
            db=db,
            agent_type=parent.agent_type,
            strategy=mutations.get("strategy", parent.strategy) if mutations else parent.strategy,
            parent_id=parent.id,
            generation=parent.generation + 1,
            capabilities=parent.capabilities,
            mutations=mutations,
            level=level,
            supervisor_id=getattr(parent, "supervisor_id", None),
        )

    async def terminate_agent(self, db, agent: Agent, reason: str, useful_discoveries: Optional[List[str]] = None):
        agent.status = AgentStatus.TERMINATED
        agent.terminated_at = datetime.now(timezone.utc)

        death = AgentDeath(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            lifetime_revenue=float(agent.lifetime_revenue),
            lifetime_expenses=float(agent.lifetime_expenses),
            lifetime_profit=float(agent.lifetime_profit),
            days_alive=agent.days_alive,
            experiments_count=agent.experiments_count,
            successful_experiments=agent.successful_experiments,
            failed_experiments=agent.failed_experiments,
            failure_reasons=[reason],
            useful_discoveries=useful_discoveries or [],
        )
        db.add(death)
        await db.flush()

    def _default_capabilities(self, agent_type: str) -> List[str]:
        capabilities_map = {
            "ceo": ["allocation", "analysis", "decision"],
            "research": ["search", "analysis", "summarization"],
            "content": ["writing", "scripting", "editing"],
            "affiliate": ["research", "link_generation", "tracking"],
            "sales": ["lead_generation", "outreach", "qualification"],
            "finance": ["accounting", "reporting", "analysis"],
            "risk": ["evaluation", "monitoring", "approval"],
            "digital_product": ["creation", "publishing", "marketing"],
            "market": ["analysis", "prediction", "simulation"],
            "experiment": ["design", "execution", "analysis"],
            "learning": ["summarization", "pattern_recognition", "storage"],
            "factory": ["creation", "mutation", "evolution"],
            "revenue": ["revenue_generation", "strategy_execution", "multi_channel"],
        }
        return capabilities_map.get(agent_type, ["generic"])
