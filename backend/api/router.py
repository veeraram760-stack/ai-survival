from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timezone, timedelta
import os
import sys
import logging
sys.path.insert(0, "C:\\ai_survival")

from ..database.connection import get_db
from ..models.database import (
    Agent, AgentStatus, Transaction, TransactionStatus, Decision, Experiment,
    SystemState, RiskEvent, LearningMemory, AuditLog, Opportunity, ContentAsset, Campaign, Trade
)
from ..agents.orchestrator import AgentOrchestrator
from ..finance.ledger import CapitalLedger
from ..risk.manager import RiskManager
from ..agents.strategies import list_strategies, get_strategy
from ..agents.revenue_agent import RevenueAgentFactory
from config.settings import settings

logger = logging.getLogger("ai_survival.api")

router = APIRouter()


def get_orchestrator(request: Request) -> AgentOrchestrator:
    return request.app.state.orchestrator


def get_capital_ledger(request: Request) -> CapitalLedger:
    return request.app.state.capital_ledger


def get_risk_manager(request: Request) -> RiskManager:
    return request.app.state.risk_manager


@router.get("/health")
async def health():
    return {"status": "alive"}


def _confirmed_real_filter():
    """Real money only counts when the transaction is COMPLETED (confirmed received/paid)
    and not logged under a throwaway test agent."""
    return (
        Transaction.category.ilike("real%"),
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.agent_id.notlike("test-%"),
    )


@router.get("/capital")
async def get_capital(ledger: CapitalLedger = Depends(get_capital_ledger), db: AsyncSession = Depends(get_db)):
    snapshot = ledger.get_capital_snapshot()
    real_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount > 0,
            *_confirmed_real_filter()
        )
    )
    real_expenses_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount < 0,
            *_confirmed_real_filter()
        )
    )
    simulated_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount > 0,
            Transaction.category.ilike("simulated%")
        )
    )
    simulated_expenses_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount < 0,
            Transaction.category.ilike("simulated%")
        )
    )
    # Include a pending-real breakout so the dashboard can show "unconfirmed" honestly
    pending_real_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount > 0,
            Transaction.category.ilike("real%"),
            Transaction.status != TransactionStatus.COMPLETED,
        )
    )
    snapshot["real_revenue"] = float(real_revenue_result.scalar_one() or 0.0)
    snapshot["real_expenses"] = abs(float(real_expenses_result.scalar_one() or 0.0))
    snapshot["pending_real_revenue"] = float(pending_real_revenue_result.scalar_one() or 0.0)
    snapshot["simulated_revenue"] = float(simulated_revenue_result.scalar_one() or 0.0)
    snapshot["simulated_expenses"] = abs(float(simulated_expenses_result.scalar_one() or 0.0))
    return snapshot


@router.get("/agents")
async def get_agents(orch: AgentOrchestrator = Depends(get_orchestrator)):
    return [a.to_dict() for a in orch.get_all_agents()]


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, orch: AgentOrchestrator = Depends(get_orchestrator)):
    agent = orch.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_dict()


@router.get("/agents/{agent_id}/lineage")
async def get_agent_lineage(agent_id: str, orch: AgentOrchestrator = Depends(get_orchestrator)):
    return orch.get_lineage(agent_id)


@router.get("/transactions")
async def get_transactions(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transaction).order_by(Transaction.timestamp.desc()).limit(limit)
    )
    transactions = result.scalars().all()
    return [
        {
            "id": t.id,
            "timestamp": t.timestamp.isoformat(),
            "agent_id": t.agent_id,
            "category": t.category,
            "action": t.action,
            "amount": float(t.amount),
            "balance_before": float(t.balance_before),
            "balance_after": float(t.balance_after),
            "status": t.status.value,
            "risk_level": t.risk_level,
        }
        for t in transactions
    ]


@router.get("/decisions")
async def get_decisions(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Decision).order_by(Decision.created_at.desc()).limit(limit)
    )
    decisions = result.scalars().all()
    return [
        {
            "id": d.id,
            "agent_id": d.agent_id,
            "decision_type": d.decision_type.value,
            "approval_status": d.approval_status.value,
            "risk_assessment": d.risk_assessment,
            "executed_at": d.executed_at.isoformat() if d.executed_at else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in decisions
    ]


@router.get("/experiments")
async def get_experiments(limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Experiment).order_by(Experiment.created_at.desc()).limit(limit)
    )
    experiments = result.scalars().all()
    return [
        {
            "id": e.id,
            "agent_id": e.agent_id,
            "hypothesis": e.hypothesis,
            "budget": float(e.budget),
            "status": e.status.value,
            "actual_result": float(e.actual_result) if e.actual_result else None,
            "conclusion": e.conclusion,
            "created_at": e.created_at.isoformat(),
        }
        for e in experiments
    ]


@router.get("/system/state")
async def get_system_state(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemState).where(SystemState.id == "current"))
    state = result.scalar_one_or_none()
    if not state:
        return {"current_mode": "GROWTH", "capital": 0, "reserve": 0, "operating": 0, "growth": 0}
    return {
        "current_mode": state.current_mode.value,
        "capital": float(state.capital),
        "reserve": float(state.reserve) if state.reserve is not None else 0.0,
        "operating": float(state.operating) if state.operating is not None else 0.0,
        "growth": float(state.growth) if state.growth is not None else 0.0,
        "total_agents": state.total_agents,
        "active_agents": state.active_agents,
        "daily_loss": float(state.daily_loss),
        "weekly_loss": float(state.weekly_loss),
    }


@router.get("/risk/events")
async def get_risk_events(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskEvent).order_by(RiskEvent.created_at.desc()).limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type.value,
            "agent_id": e.agent_id,
            "severity": e.severity,
            "details": e.details,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/learning/memory")
async def get_learning_memory(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LearningMemory).order_by(LearningMemory.updated_at.desc()).limit(limit)
    )
    memories = result.scalars().all()
    return [
        {
            "id": m.id,
            "category": m.category,
            "key": m.key,
            "value": m.value,
            "confidence": m.confidence,
            "created_at": m.created_at.isoformat(),
        }
        for m in memories
    ]


@router.get("/modal/status")
async def get_modal_status():
    configured = bool(
        (settings.modal_token_id and settings.modal_token_secret) or
        (settings.modal_api_key)
    )
    status = {
        "configured": configured,
        "enabled": False,
        "gpu_types": settings.modal_gpu_types,
    }
    try:
        from ..execution.engine import _init_modal
        app = _init_modal()
        status["enabled"] = app is not None
    except Exception as e:
        status["error"] = str(e)
    return status


@router.post("/agents/{agent_id}/tasks")
async def run_agent_task(
    agent_id: str,
    task_type: str,
    payload: dict,
    orch: AgentOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
):
    agent = orch.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not hasattr(orch, "execution_engine") or orch.execution_engine is None:
        raise HTTPException(status_code=500, detail="Execution engine not initialized")

    task_data = dict(payload or {})
    task_data.setdefault("agent_type", agent.agent_type)
    task_data.setdefault("strategy", agent.strategy)
    task_data.setdefault("capabilities", agent.capabilities)

    result = await orch.execution_engine.execute_agent_task(db, agent_id, task_type, task_data)
    return result


@router.get("/tools")
async def list_tools():
    from ..tools import tool_registry
    return tool_registry.list_tools()


@router.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, payload: dict):
    from ..tools import tool_registry
    tool = tool_registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    result = await tool_registry.execute(tool_name, **payload)
    return result


@router.post("/agents/{agent_id}/decisions")
async def create_decision(
    agent_id: str,
    decision_type: str,
    payload: dict,
    orch: AgentOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
):
    agent = orch.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    from ..models.database import Decision
    decision = Decision(
        id=str(__import__('uuid').uuid4()),
        agent_id=agent_id,
        decision_type=decision_type,
        payload=payload,
        approval_status="PENDING",
    )
    db.add(decision)
    await db.commit()
    return {"id": decision.id, "status": "PENDING"}


@router.get("/withdrawal/status")
async def get_withdrawal_status(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from ..models.database import Withdrawal, Transaction
    
    threshold = settings.withdrawal_threshold
    real_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount > 0,
            *_confirmed_real_filter()
        )
    )
    real_revenue = float(real_revenue_result.scalar_one() or 0.0)

    pending_result = await db.execute(
        select(func.count(Withdrawal.id)).where(Withdrawal.status == "PENDING")
    )
    pending_count = (pending_result.scalar_one()) or 0
    
    return {
        "threshold": threshold,
        "real_revenue": real_revenue,
        "remaining_to_threshold": max(0.0, threshold - real_revenue),
        "eligible": real_revenue >= threshold,
        "pending_withdrawals": pending_count,
    }


@router.post("/withdrawal/request")
async def request_withdrawal(db: AsyncSession = Depends(get_db), test: bool = False, test_amount: float | None = None):
    from sqlalchemy import select, func
    from ..models.database import Withdrawal, Transaction

    threshold = settings.withdrawal_threshold
    real_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.amount > 0,
            *_confirmed_real_filter()
        )
    )
    real_revenue = float(real_revenue_result.scalar_one() or 0.0)

    if test and test_amount is not None:
        amount = float(test_amount)
        threshold = 0.0
    else:
        amount = real_revenue
        if real_revenue < threshold:
            return {
                "status": "denied",
                "reason": f"Real revenue ${real_revenue:.2f} is below withdrawal threshold ${threshold:.2f}",
                "real_revenue": real_revenue,
                "threshold": threshold,
                "remaining": threshold - real_revenue,
            }
    
    withdrawal = Withdrawal(
        id=str(__import__('uuid').uuid4()),
        amount=amount,
        currency="USD",
        status="PENDING",
        threshold=threshold,
        real_revenue_at_request=real_revenue,
    )
    db.add(withdrawal)
    await db.commit()
    await db.refresh(withdrawal)

    payout_result = None
    try:
        from backend.tools.api import PayoutTool
        payout_tool = PayoutTool()
        payout_result = await payout_tool.execute(
            amount=amount,
            currency=withdrawal.currency,
            destination=os.getenv("PAYOUT_EMAIL") or os.getenv("RAZORPAY_CONTACT_ID"),
        )
        if payout_result.get("status") == "success":
            withdrawal.status = "COMPLETED"
            await db.commit()
    except Exception as e:
        logger.error(f"Payout failed: {e}")

    return {
        "status": "pending",
        "withdrawal_id": withdrawal.id,
        "amount": amount,
        "currency": withdrawal.currency,
        "real_revenue": real_revenue,
        "threshold": threshold,
        "payout": payout_result,
        "test": test,
        "created_at": withdrawal.created_at.isoformat() if withdrawal.created_at else None,
    }


@router.post("/razorpay/create-order")
async def create_razorpay_order(request: Request):
    data = await request.json()
    amount = data.get("amount")
    currency = data.get("currency", "INR")
    receipt = data.get("receipt", f"order_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")

    if not amount or float(amount) < 1.0:
        raise HTTPException(status_code=400, detail="Amount must be at least 1.0 INR / 100 paise")

    razorpay_key_id = settings.razorpay_key_id or os.getenv("RAZORPAY_KEY_ID")
    razorpay_key_secret = settings.razorpay_key_secret or os.getenv("RAZORPAY_KEY_SECRET")
    if not razorpay_key_id or not razorpay_key_secret:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured")

    try:
        import razorpay
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
        order_data = {
            "amount": int(float(amount) * 100),
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        }
        order = client.order.create(data=order_data)
        return {
            "status": "success",
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "key_id": razorpay_key_id,
        }
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/razorpay/verify-payment")
async def verify_razorpay_payment(request: Request):
    data = await request.json()
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        raise HTTPException(status_code=400, detail="Missing payment verification fields")

    razorpay_key_secret = settings.razorpay_key_secret or os.getenv("RAZORPAY_KEY_SECRET")
    if not razorpay_key_secret:
        raise HTTPException(status_code=500, detail="Razorpay secret not configured")

    try:
        import hmac
        import hashlib
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            razorpay_key_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if generated_signature == razorpay_signature:
            return {"status": "success", "verified": True}
        else:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Razorpay verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(limit: int = 100, db: AsyncSession = Depends(get_db)):
    from ..models.database import Task as DBTask
    result = await db.execute(select(DBTask).order_by(DBTask.created_at.desc()).limit(limit))
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "project_id": t.project_id,
            "parent_task_id": t.parent_task_id,
            "title": t.title,
            "description": t.description,
            "goal": t.goal,
            "priority": t.priority.value,
            "status": t.status.value,
            "assigned_agent": t.assigned_agent,
            "supervisor": t.supervisor,
            "retry_count": t.retry_count,
            "max_retries": t.max_retries,
            "autonomy_level": t.autonomy_level,
            "created_at": t.created_at.isoformat(),
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]


@router.post("/tasks")
async def create_task(payload: dict, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    task_manager = getattr(orch, "task_manager", None)
    if not task_manager:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    task = await task_manager.create_task(
        db=db,
        title=payload.get("title", "Untitled Task"),
        description=payload.get("description", ""),
        goal=payload.get("goal", ""),
        priority=payload.get("priority", "MEDIUM"),
        project_id=payload.get("project_id"),
        parent_task_id=payload.get("parent_task_id"),
        input_data=payload.get("input_data"),
        expected_output=payload.get("expected_output"),
        assigned_agent=payload.get("assigned_agent"),
        supervisor=payload.get("supervisor"),
        tools_required=payload.get("tools_required"),
        memory_required=payload.get("memory_required"),
        max_retries=payload.get("max_retries", 3),
        autonomy_level=payload.get("autonomy_level", 3),
        timeout_minutes=payload.get("timeout_minutes"),
    )
    await db.commit()
    return {"id": task.id, "status": task.status.value}


@router.get("/tasks/stats")
async def get_task_stats(db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    task_manager = getattr(orch, "task_manager", None)
    if not task_manager:
        raise HTTPException(status_code=500, detail="Task manager not initialized")
    stats = await task_manager.get_task_stats(db)
    return stats


@router.get("/hierarchy")
async def get_hierarchy(orch: AgentOrchestrator = Depends(get_orchestrator)):
    return orch.get_hierarchy_tree()


@router.get("/memory/short-term")
async def get_short_term_memory(key: str, task_id: Optional[str] = None, project_id: Optional[str] = None, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    memory_manager = getattr(orch, "memory_manager", None)
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    value = await memory_manager.get_short_term(db, key, task_id, project_id)
    return {"key": key, "value": value}


@router.post("/memory/short-term")
async def set_short_term_memory(payload: dict, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    memory_manager = getattr(orch, "memory_manager", None)
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    await memory_manager.set_short_term(
        db,
        key=payload.get("key"),
        value=payload.get("value"),
        task_id=payload.get("task_id"),
        project_id=payload.get("project_id"),
        ttl_minutes=payload.get("ttl_minutes"),
    )
    await db.commit()
    return {"status": "stored"}


@router.get("/memory/project")
async def get_project_memory(project_id: str, key: str, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    memory_manager = getattr(orch, "memory_manager", None)
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    value = await memory_manager.get_project(db, project_id, key)
    return {"project_id": project_id, "key": key, "value": value}


@router.post("/memory/project")
async def set_project_memory(payload: dict, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    memory_manager = getattr(orch, "memory_manager", None)
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    await memory_manager.set_project(
        db,
        project_id=payload.get("project_id"),
        key=payload.get("key"),
        value=payload.get("value"),
        confidence=payload.get("confidence", 0.5),
    )
    await db.commit()
    return {"status": "stored"}


@router.get("/memory/long-term")
async def get_long_term_memory(category: str, key: str, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    memory_manager = getattr(orch, "memory_manager", None)
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    value = await memory_manager.get_long_term(db, category, key)
    return {"category": category, "key": key, "value": value}


@router.post("/memory/long-term")
async def set_long_term_memory(payload: dict, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    memory_manager = getattr(orch, "memory_manager", None)
    if not memory_manager:
        raise HTTPException(status_code=500, detail="Memory manager not initialized")
    await memory_manager.set_long_term(
        db,
        category=payload.get("category"),
        key=payload.get("key"),
        value=payload.get("value"),
        confidence=payload.get("confidence", 0.5),
    )
    await db.commit()
    return {"status": "stored"}


@router.get("/performance/top")
async def get_top_agents(limit: int = 10, metric: str = "reliability_score", db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    tracker = getattr(orch, "performance_tracker", None)
    if not tracker:
        raise HTTPException(status_code=500, detail="Performance tracker not initialized")
    return await tracker.get_top_agents(db, limit=limit, metric=metric)


@router.get("/performance/{agent_id}")
async def get_agent_performance(agent_id: str, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    tracker = getattr(orch, "performance_tracker", None)
    if not tracker:
        raise HTTPException(status_code=500, detail="Performance tracker not initialized")
    perf = await tracker.get_performance(db, agent_id)
    if not perf:
        raise HTTPException(status_code=404, detail="No performance data")
    return perf


@router.get("/self-improve/agents")
async def get_self_improving_agents(orch: AgentOrchestrator = Depends(get_orchestrator)):
    si = orch.get_self_improver()
    dev = orch.get_agent_developer()
    result = []
    if si:
        result.append(si.to_dict())
    if dev:
        result.append(dev.to_dict())
    return {"agents": result, "count": len(result)}


@router.get("/self-improve/cycle")
async def get_latest_cycle(agent_id: str, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    from backend.models.improvement import AgentImprovement
    result = await db.execute(
        select(AgentImprovement)
        .where(AgentImprovement.agent_id == agent_id)
        .order_by(AgentImprovement.cycle.desc())
        .limit(1)
    )
    improvement = result.scalar_one_or_none()
    if not improvement:
        raise HTTPException(status_code=404, detail="No improvement cycles found")
    return {
        "id": improvement.id,
        "agent_id": improvement.agent_id,
        "cycle": improvement.cycle,
        "status": improvement.status,
        "started_at": improvement.started_at.isoformat() if improvement.started_at else None,
        "completed_at": improvement.completed_at.isoformat() if improvement.completed_at else None,
        "improvements_applied": improvement.improvements_applied,
        "improvements_failed": improvement.improvements_failed,
    }


@router.get("/self-improve/history")
async def get_improvement_history(agent_id: str, limit: int = 10, db: AsyncSession = Depends(get_db), orch: AgentOrchestrator = Depends(get_orchestrator)):
    from backend.models.improvement import AgentImprovement
    result = await db.execute(
        select(AgentImprovement)
        .where(AgentImprovement.agent_id == agent_id)
        .order_by(AgentImprovement.cycle.desc())
        .limit(limit)
    )
    improvements = result.scalars().all()
    return [
        {
            "id": m.id,
            "agent_id": m.agent_id,
            "cycle": m.cycle,
            "status": m.status,
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "completed_at": m.completed_at.isoformat() if m.completed_at else None,
            "weaknesses_found": m.weaknesses_found,
            "improvements_applied": m.improvements_applied,
            "improvements_failed": m.improvements_failed,
        }
        for m in improvements
    ]


@router.post("/self-improve/cycle")
async def trigger_self_improvement_cycle(orch: AgentOrchestrator = Depends(get_orchestrator), db: AsyncSession = Depends(get_db)):
    result = await orch.run_self_improvement_cycle(db)
    return result


@router.get("/revenue/strategies")
async def get_revenue_strategies():
    """List all available revenue strategies"""
    return list_strategies()


@router.get("/revenue/agents")
async def get_revenue_agents(orch: AgentOrchestrator = Depends(get_orchestrator)):
    """Get all revenue agents with performance summary"""
    revenue_agents = orch.get_revenue_agents()
    return [a.get_performance_summary() for a in revenue_agents]


@router.get("/revenue/performance")
async def get_revenue_performance(orch: AgentOrchestrator = Depends(get_orchestrator)):
    """Get aggregate revenue performance across all revenue agents"""
    return orch.get_revenue_performance_summary()


@router.post("/revenue/agents/{agent_id}/cycle")
async def trigger_revenue_cycle(
    agent_id: str,
    context: dict = None,
    orch: AgentOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a revenue cycle for a specific agent"""
    agent = orch.get_agent(agent_id)
    if not agent or agent.agent_type != "revenue":
        raise HTTPException(status_code=404, detail="Revenue agent not found")
    
    # Need to access the RevenueAgent's execute_cycle method
    if not hasattr(agent, 'execute_cycle'):
        raise HTTPException(status_code=500, detail="Agent is not a revenue agent")
    
    ledger = getattr(orch, 'ledger', None) or orch.ledger if hasattr(orch, 'ledger') else None
    if not ledger:
        from ..finance.ledger import CapitalLedger
        ledger = CapitalLedger(starting_capital=50.0)
    
    result = await agent.execute_cycle(db, ledger, context or {})
    return result


@router.post("/revenue/agents/{agent_id}/switch-strategy")
async def switch_revenue_strategy(
    agent_id: str,
    strategy_name: str,
    orch: AgentOrchestrator = Depends(get_orchestrator),
):
    """Switch a revenue agent's strategy"""
    agent = orch.get_agent(agent_id)
    if not agent or agent.agent_type != "revenue":
        raise HTTPException(status_code=404, detail="Revenue agent not found")
    
    if not hasattr(agent, 'switch_strategy'):
        raise HTTPException(status_code=500, detail="Agent is not a revenue agent")
    
    success = agent.switch_strategy(strategy_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy_name}")
    
    return {"status": "success", "agent_id": agent_id, "new_strategy": strategy_name}


@router.post("/revenue/agents/create")
async def create_revenue_agent(
    strategy_name: str,
    orch: AgentOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new revenue agent with specified strategy"""
    from ..agents.factory import AgentFactory
    import uuid
    
    factory = AgentFactory(orch.risk_manager)
    agent_id = str(uuid.uuid4())
    
    try:
        agent = await factory.create_agent(
            db=db,
            agent_type="revenue",
            strategy=strategy_name,
            level="SPECIALIST",
        )
        orch.agents[agent.id] = agent
        return {"status": "success", "agent_id": agent.id, "strategy": strategy_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue/recommend-strategy")
async def recommend_strategy(
    capital: float = 50.0,
    risk_tolerance: str = "MEDIUM",
):
    """Get recommended strategy based on capital and risk tolerance"""
    strategy = RevenueAgentFactory.get_recommended_strategy(capital, risk_tolerance)
    return {
        "recommended_strategy": strategy,
        "capital": capital,
        "risk_tolerance": risk_tolerance,
        "available_strategies": list(list_strategies().keys()),
    }
