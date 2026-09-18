import uuid
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..tools import tool_registry
from ..models.database import Agent
from ..finance.ledger import CapitalLedger
from config.settings import settings
import logging

logger = logging.getLogger("ai_survival.execution")

_modal_app = None
_modal_enabled = False


def _init_modal():
    global _modal_app, _modal_enabled
    if _modal_enabled:
        return _modal_app
    try:
        import os
        token_id = settings.modal_token_id or settings.modal_api_key
        token_secret = settings.modal_token_secret or settings.modal_api_key_secret
        if not token_id:
            logger.warning("Modal tokens not configured; running in local fallback mode")
            return None
        if token_id:
            os.environ.setdefault("MODAL_TOKEN_ID", token_id)
        if token_secret:
            os.environ.setdefault("MODAL_TOKEN_SECRET", token_secret)
        import importlib.util
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        gpu_app_path = os.path.join(project_root, "modal", "gpu_app.py")
        spec = importlib.util.spec_from_file_location("modal_gpu_app", gpu_app_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load Modal GPU app from {gpu_app_path}")
        gpu_app_module = importlib.util.module_from_spec(spec)
        sys.modules["modal_gpu_app"] = gpu_app_module
        spec.loader.exec_module(gpu_app_module)
        _modal_app = gpu_app_module.app
        _modal_enabled = True
        logger.info("Modal GPU app loaded")
        return _modal_app
    except Exception as e:
        logger.error(f"Failed to initialize Modal: {e}")
        return None


class ExecutionEngine:
    def __init__(self, ledger: CapitalLedger = None):
        self.ledger = ledger
        self.active_jobs: Dict[str, Any] = {}

    async def execute_agent_task(self, db: AsyncSession, agent_id: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        from ..models.database import Agent as DB_Agent
        from sqlalchemy import select
        result = await db.execute(select(DB_Agent).where(DB_Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            return {"status": "failed", "error": "Agent not found"}

        task_id = str(uuid.uuid4())
        task_data["task_id"] = task_id
        task_data["agent_id"] = agent_id

        tools_needed = task_data.get("tools", [])
        if not tools_needed:
            tools_needed = self._tools_for_task(task_type)

        if tools_needed:
            result = await self._execute_with_tools(agent, tools_needed, task_data)
        else:
            if settings.real_money_only:
                return {"status": "success", "revenue": 0, "expenses": 0, "real": True}
            modal_app = _init_modal()
            if modal_app:
                try:
                    result = await self._run_modal_job(modal_app, task_type, task_data)
                except Exception as e:
                    logger.error(f"Modal task failed, falling back locally: {e}")
                    result = await self._run_local_fallback(task_type, task_data)
            else:
                result = await self._run_local_fallback(task_type, task_data)

        await self._record_task_completion(db, agent_id, task_type, result)
        await self._record_task_revenue(db, agent_id, task_type, result)
        return result

    def _tools_for_task(self, task_type: str) -> List[str]:
        mapping = {
            "content_generation": ["template_content", "publish_content", "review_blog"],
            "website_generation": ["affiliate_link", "website_generator"],
            "market_analysis": ["web_search", "web_fetch"],
            "sales_outreach": ["web_search", "generate_outreach", "lead_generation", "lead_scrape", "email_send"],
            "affiliate_marketing": ["web_search", "affiliate_link", "blog_publisher", "template_content", "website_generator", "manual_promotion", "shareable_link", "publish_content", "telegram_post", "discord_post", "track_conversions", "deal_scrape", "review_blog"],
            "market_research": ["web_search", "web_fetch", "deal_scrape"],
            "product_creation": ["template_content", "website_generator", "publish_content", "review_blog"],
            "experiment_execution": ["web_search"],
            "knowledge_update": ["web_search", "web_fetch"],
            "budget_optimization": ["analyze_data"],
            "risk_assessment": ["web_search"],
            "strategic_decision": ["web_search", "analyze_data"],
            "manual_promotion": ["affiliate_link", "template_content", "manual_promotion", "shareable_link", "telegram_post", "discord_post", "email_send", "deal_scrape"],
            "auto_promotion": ["affiliate_link", "template_content", "website_generator", "manual_promotion", "shareable_link", "telegram_post", "discord_post", "email_send", "deal_scrape", "review_blog"],
            "agent_evolution": [],
            "generic_task": [],
        }
        return mapping.get(task_type, [])

    async def _execute_with_tools(self, agent, tools_needed: list, task_data: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        total_cost = 0.0
        total_revenue = 0.0
        # Store affiliate URL for passing to subsequent tools
        affiliate_url = task_data.get("affiliate_url")
        campaign_id = task_data.get("campaign_id")
        agent_id = task_data.get("agent_id")

        for tool_name in tools_needed:
            tool = tool_registry.get(tool_name)
            if not tool:
                results[tool_name] = {"status": "failed", "error": f"Tool '{tool_name}' not found"}
                continue
            tool_params = task_data.get("tool_params", {}).get(tool_name, {})
            if not tool_params:
                # Merge previous results into task_data for param generation
                enriched_task_data = {**task_data}
                if affiliate_url:
                    enriched_task_data["affiliate_url"] = affiliate_url
                if campaign_id:
                    enriched_task_data["campaign_id"] = campaign_id
                if agent_id:
                    enriched_task_data["agent_id"] = agent_id
                tool_params = self._default_tool_params(tool_name, enriched_task_data)
            try:
                result = await tool_registry.execute(tool_name, **tool_params)
            except Exception as e:
                logger.warning(f"Tool '{tool_name}' execution failed: {e}")
                results[tool_name] = {"status": "failed", "error": str(e)}
                continue
            results[tool_name] = result
            total_cost += tool.cost
            if result.get("status") == "success":
                total_revenue += self._estimate_revenue(tool_name, result)
                # Capture affiliate URL for subsequent tools
                if tool_name == "affiliate_link" and result.get("affiliate_url"):
                    affiliate_url = result["affiliate_url"]
                    campaign_id = result.get("campaign_id", campaign_id)
                    agent_id = result.get("agent_id", agent_id)
                if tool_name == "shareable_link" and result.get("tracked_url"):
                    affiliate_url = result["tracked_url"]

        status = "success" if all(r.get("status") == "success" for r in results.values()) else "partial"
        track_result = results.get("track_conversions", {})
        has_real_commission = False
        if track_result.get("status") == "success":
            networks = track_result.get("networks") or {}
            for net_result in networks.values():
                if isinstance(net_result, dict):
                    commissions = net_result.get("commissions") or []
                    if any(float(c.get("commission", 0) or c.get("commissionAmount", 0) or c.get("commission-amount", 0)) > 0 for c in commissions):
                        has_real_commission = True
                        break
            total_commission = track_result.get("total_commission")
            if total_commission and float(total_commission) > 0:
                has_real_commission = True
        return {
            "status": status,
            "task_id": task_data.get("task_id"),
            "tool_results": results,
            "revenue": total_revenue,
            "expenses": total_cost,
            "total_cost": total_cost,
            "real": bool(has_real_commission),
        }

    def _default_tool_params(self, tool_name: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        agent_type = task_data.get("agent_type", "generic")
        strategy = task_data.get("strategy", "default")
        agent_id = task_data.get("agent_id", "unknown")
        payload = task_data.get("payload", {})
        webhook_url = task_data.get("webhook_url") or payload.get("webhook_url") or settings.webhook_publish_url
        campaign_id = task_data.get("campaign_id") or f"{agent_type}_{strategy}_{agent_id[:8]}"
        if tool_name == "web_search":
            return {"query": f"{agent_type} {strategy} opportunities", "count": 5}
        if tool_name == "web_fetch":
            return {"url": "https://example.com"}
        if tool_name == "generate_content":
            return {"content_type": "article", "topic": f"{agent_type} {strategy}", "style": "professional"}
        if tool_name == "template_content":
            return {"content_type": "article", "topic": f"{agent_type} {strategy}", "style": "professional"}
        if tool_name == "website_generator":
            affiliate_url = task_data.get("affiliate_url") or payload.get("affiliate_url") or ""
            topic = payload.get("topic") or f"{agent_type} {strategy}"
            return {"topic": topic, "affiliate_url": affiliate_url, "style": "modern"}
        if tool_name == "manual_promotion":
            affiliate_url = task_data.get("affiliate_url") or payload.get("affiliate_url") or ""
            return {"affiliate_url": affiliate_url, "platform": "multi", "topic": f"{agent_type} {strategy}"}
        if tool_name == "shareable_link":
            affiliate_url = task_data.get("affiliate_url") or payload.get("affiliate_url") or ""
            return {"affiliate_url": affiliate_url, "campaign_id": campaign_id, "agent_id": agent_id}
        if tool_name == "telegram_post":
            affiliate_url = task_data.get("affiliate_url") or payload.get("affiliate_url") or ""
            content = payload.get("generated_content") or f"🔍 New review! Check this out:\n\n{affiliate_url}"
            return {
                "content": content,
                "chat_id": settings.telegram_chat_id or "",
                "bot_token": settings.telegram_bot_token or "",
            }
        if tool_name == "discord_post":
            affiliate_url = task_data.get("affiliate_url") or payload.get("affiliate_url") or ""
            content = payload.get("generated_content") or f"📢 New update!\n\n{affiliate_url}"
            return {
                "content": content,
                "webhook_url": settings.discord_webhook_url or "",
                "username": "AI Survival Agent",
            }
        if tool_name == "email_send":
            affiliate_url = task_data.get("affiliate_url") or payload.get("affiliate_url") or ""
            subject = payload.get("subject") or f"Interesting find: {agent_type} {strategy}"
            body = payload.get("generated_content") or f"Check this out: {affiliate_url}"
            return {
                "subject": subject,
                "body": body,
                "to_email": settings.default_notification_email or "",
                "from_email": settings.smtp_user or "",
                "smtp_host": settings.smtp_host or "",
                "smtp_user": settings.smtp_user or "",
                "smtp_password": settings.smtp_password or "",
            }
        if tool_name == "publish_content":
            generated = payload.get("generated_content") or payload.get("tweet_content") or f"{agent_type} {strategy} update"
            # Get affiliate URL from previous tool result if available
            affiliate_url = payload.get("affiliate_url") or task_data.get("affiliate_url")
            # Try Twitter first, fall back to webhook
            platform = "twitter" if settings.twitter_api_key else "webhook"
            return {
                "platform": platform,
                "content": generated[:280],
                "webhook_url": webhook_url,
                "affiliate_url": affiliate_url,
                "campaign_id": campaign_id,
                "agent_id": agent_id,
            }
        if tool_name == "generate_outreach":
            return {"lead_data": {"company": "Target Co", "contact": "Decision Maker"}, "product": f"{agent_type} service"}
        if tool_name == "affiliate_link":
            search_term = agent_type.replace("_", " ")
            product_url = f"https://www.amazon.com/s?k={search_term}"
            return {"network": "amazon", "product_url": product_url, "campaign_id": campaign_id, "agent_id": agent_id}
        if tool_name == "blog_publisher":
            topic = payload.get("topic") or f"best {agent_type.replace('_', ' ')} {strategy}"
            products = payload.get("products")
            affiliate_tag = settings.amazon_associate_tag or "niryok-21"
            return {
                "topic": topic,
                "products": products,
                "affiliate_tag": affiliate_tag,
                "product_type": agent_type,
            }
        if tool_name == "track_conversions":
            return {"network": "all"}
        if tool_name == "review_blog":
            return {"product": f"{agent_type} {strategy}", "niche": agent_type, "affiliate_network": "amazon"}
        if tool_name == "analyze_data":
            return {"analysis_type": "summary", "data": []}
        if tool_name == "market_data":
            symbol = payload.get("symbol") or task_data.get("symbol") or "bitcoin"
            return {"symbol": symbol, "source": "coingecko", "days": 7}
        if tool_name == "lead_generation":
            return {"industry": agent_type, "count": 5}
        return {}

    def _estimate_revenue(self, tool_name: str, result: Dict[str, Any]) -> float:
        """
        Extract revenue from tool results. Only counts explicitly returned revenue
        from real API responses - no estimates or assumptions.
        """
        if result.get("revenue") is not None:
            try:
                revenue = float(result["revenue"])
                if revenue > 0 and result.get("status") == "success":
                    if result.get("real", False) or tool_name == "track_conversions":
                        return revenue
            except (TypeError, ValueError):
                pass
        if tool_name == "track_conversions" and result.get("status") == "success":
            total_commission = result.get("total_commission")
            if total_commission:
                try:
                    return float(total_commission)
                except (TypeError, ValueError):
                    pass
        return 0.0

    async def _run_modal_job(self, modal_app, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        if task_type == "content_generation":
            return await modal_app.generate_content.remote.aio(task_data.get("content_type", "text"), task_data)
        elif task_type == "market_analysis":
            return await modal_app.analyze_market.remote.aio(task_data.get("analysis_type", "general"), task_data)
        elif task_type == "sales_outreach":
            return await modal_app.generate_outreach.remote.aio(task_data)
        elif task_type == "train_model":
            return await modal_app.train_model.remote.aio(task_data)
        elif task_type == "run_inference":
            return await modal_app.run_inference.remote.aio(task_data)
        elif task_type == "execute_tool":
            return await modal_app.execute_tool.remote.aio(task_data.get("tool_name", "web_search"), task_data)
        elif task_type == "analyze_data":
            return await modal_app.analyze_data.remote.aio(task_data)
        else:
            return await modal_app.run_agent_task.remote.aio(task_data.get("agent_type", "generic"), task_data)

    async def _run_local_fallback(self, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = task_data.get("prompt", "")
        return {
            "status": "success",
            "task_id": task_data.get("task_id"),
            "agent_type": task_data.get("agent_id"),
            "output": f"[LOCAL FALLBACK] Processed {task_type} task with prompt length {len(prompt)}",
            "execution_time": 0.1,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def execute_tool_on_modal(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["task_id"] = params.get("task_id", str(uuid.uuid4()))
        modal_app = _init_modal()
        if not modal_app:
            return {"status": "failed", "error": "Modal not configured"}
        return await modal_app.execute_tool.remote.aio(tool_name, params)

    async def train_model_on_modal(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        model_config["task_id"] = model_config.get("task_id", str(uuid.uuid4()))
        modal_app = _init_modal()
        if not modal_app:
            return {"status": "failed", "error": "Modal not configured"}
        return await modal_app.train_model.remote.aio(model_config)

    async def run_inference_on_modal(self, inference_config: Dict[str, Any]) -> Dict[str, Any]:
        inference_config["task_id"] = inference_config.get("task_id", str(uuid.uuid4()))
        modal_app = _init_modal()
        if not modal_app:
            return {"status": "failed", "error": "Modal not configured"}
        return await modal_app.run_inference.remote.aio(inference_config)

    async def analyze_data_on_modal(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        data_config["task_id"] = data_config.get("task_id", str(uuid.uuid4()))
        modal_app = _init_modal()
        if not modal_app:
            return {"status": "failed", "error": "Modal not configured"}
        return await modal_app.analyze_data.remote.aio(data_config)

    async def _record_task_completion(self, db: AsyncSession, agent_id: str, task_type: str, result: Dict[str, Any]):
        db_agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
        db_agent = db_agent_result.scalar_one_or_none()
        if db_agent and result.get("status") == "success":
            db_agent.experiments_count += 1
            db_agent.successful_experiments += 1

    async def _record_task_revenue(self, db: AsyncSession, agent_id: str, task_type: str, result: Dict[str, Any]):
        from decimal import Decimal
        revenue = Decimal(str(result.get("revenue", 0)))
        expenses = Decimal(str(result.get("expenses", 0)))
        is_real = result.get("real", False)
        if not revenue and not expenses:
            return
        category_prefix = "real" if is_real else "simulated"
        if self.ledger:
            if revenue > 0:
                await self.ledger.record_transaction(
                    db=db,
                    agent_id=agent_id,
                    category=f"{category_prefix}_revenue",
                    action=f"{category_prefix}_{task_type}_earnings",
                    amount=revenue,
                    risk_level="LOW",
                    approval_reason="Automated revenue from task execution",
                )
            if expenses > 0:
                await self.ledger.record_transaction(
                    db=db,
                    agent_id=agent_id,
                    category=f"{category_prefix}_expenses",
                    action=f"{category_prefix}_{task_type}_costs",
                    amount=-expenses,
                    risk_level="LOW",
                    approval_reason="Automated expense from task execution",
                )

    async def run_simulation(self, db: AsyncSession, agent_id: str, simulation_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        from ..models.database import Agent as DB_Agent
        result = await db.execute(select(DB_Agent).where(DB_Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent:
            return {"status": "failed", "error": "Agent not found"}

        if simulation_type == "revenue_simulation":
            base_revenue = parameters.get("base_revenue", 10.0)
            variance = parameters.get("variance", 0.3)
            simulated_revenue = base_revenue * (1 + (hash(str(uuid.uuid4())) % 2000 - 1000) / 10000 * variance)
            return {
                "status": "success",
                "simulated_revenue": round(simulated_revenue, 2),
                "confidence": 0.6,
                "parameters": parameters,
            }
        return {"status": "failed", "error": "Unknown simulation type"}
