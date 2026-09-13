import uuid
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..agents.base import Agent
from config.settings import settings

logger = logging.getLogger("ai_survival.specialists")


class Specialist(Agent):
    def __init__(self, agent_id: str, agent_type: str, strategy: str = "default", capabilities: Optional[List[str]] = None):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            strategy=strategy,
            capabilities=capabilities or self._default_capabilities(agent_type),
        )
        self.supervisor_id: Optional[str] = None

    def _default_capabilities(self, agent_type: str) -> List[str]:
        capabilities_map = {
            "web_research": ["web_search", "web_fetch", "summarization"],
            "market_research": ["web_search", "web_fetch", "analysis"],
            "trend": ["web_search", "analysis", "prediction"],
            "fact_check": ["web_search", "verification", "validation"],
            "script": ["writing", "scripting", "editing"],
            "video_prompt": ["writing", "visual_design", "prompting"],
            "voice": ["audio_generation", "scripting", "editing"],
            "thumbnail": ["image_generation", "design", "branding"],
            "seo": ["research", "optimization", "analysis"],
            "sales": ["lead_generation", "outreach", "qualification"],
            "marketing": ["campaign_design", "promotion", "analytics"],
            "strategy": ["planning", "analysis", "decision"],
            "finance": ["accounting", "reporting", "analysis"],
            "database": ["query", "schema", "migration"],
            "code": ["development", "debugging", "testing"],
            "qa": ["testing", "validation", "reporting"],
            "learning": ["summarization", "pattern_recognition", "storage"],
            "product_creation": ["creation", "publishing", "marketing"],
            "market_analysis": ["analysis", "prediction", "simulation"],
            "experiment": ["design", "execution", "analysis"],
            "agent_evolution": ["creation", "mutation", "evolution"],
            "risk_monitoring": ["evaluation", "monitoring", "approval"],
        }
        return capabilities_map.get(agent_type, ["generic"])

    def format_output(self, task_id: str, status: str, summary: str, result: Any, confidence: float, issues: str, recommendation: str, next_action: str) -> Dict[str, Any]:
        return {
            "agent_name": f"{self.agent_type}:{self.strategy}",
            "task_id": task_id,
            "status": status,
            "summary": summary,
            "result": result,
            "confidence": confidence,
            "issues": issues,
            "recommendation": recommendation,
            "next_action": next_action,
        }


SPECIALIST_TYPE_MAP = {
    "research": "web_research",
    "content": "script",
    "affiliate": "marketing",
    "sales": "sales",
    "finance": "finance",
    "risk": "risk_monitoring",
    "digital_product": "product_creation",
    "market": "market_analysis",
    "experiment": "experiment",
    "learning": "learning",
    "factory": "agent_evolution",
    "web_research": "web_research",
    "market_research": "market_research",
    "trend": "trend",
    "fact_check": "fact_check",
    "script": "script",
    "video_prompt": "video_prompt",
    "voice": "voice",
    "thumbnail": "thumbnail",
    "seo": "seo",
    "strategy": "strategy",
    "database": "database",
    "code": "code",
    "qa": "qa",
}


def map_to_specialist_type(agent_type: str) -> str:
    return SPECIALIST_TYPE_MAP.get(agent_type, agent_type)
