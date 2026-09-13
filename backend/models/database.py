from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Boolean, Text,
    ForeignKey, Enum as SQLEnum, Numeric, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database.connection import Base


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class AgentStatus(str, enum.Enum):
    ALIVE = "ALIVE"
    TESTING = "TESTING"
    GROWING = "GROWING"
    REPRODUCTION_READY = "REPRODUCTION_READY"
    PAUSED = "PAUSED"
    TERMINATED = "TERMINATED"
    FAILED = "FAILED"


class SystemMode(str, enum.Enum):
    GROWTH = "GROWTH"
    DEFENSIVE = "DEFENSIVE"
    SURVIVAL = "SURVIVAL"
    DEAD = "DEAD"


class DecisionType(str, enum.Enum):
    CREATE_AGENT = "CREATE_AGENT"
    CLONE_AGENT = "CLONE_AGENT"
    MUTATE_STRATEGY = "MUTATE_STRATEGY"
    ALLOCATE_BUDGET = "ALLOCATE_BUDGET"
    REDUCE_BUDGET = "REDUCE_BUDGET"
    PAUSE_AGENT = "PAUSE_AGENT"
    TERMINATE_AGENT = "TERMINATE_AGENT"
    START_EXPERIMENT = "START_EXPERIMENT"
    STOP_EXPERIMENT = "STOP_EXPERIMENT"
    SCALE_STRATEGY = "SCALE_STRATEGY"
    ENTER_SURVIVAL_MODE = "ENTER_SURVIVAL_MODE"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXECUTED = "EXECUTED"


class ExperimentStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RiskEventType(str, enum.Enum):
    SPEND_DENIED = "SPEND_DENIED"
    SPEND_APPROVED = "SPEND_APPROVED"
    RESERVE_VIOLATION_ATTEMPT = "RESERVE_VIOLATION_ATTEMPT"
    POPULATION_LIMIT_HIT = "POPULATION_LIMIT_HIT"
    CAPITAL_THRESHOLD = "CAPITAL_THRESHOLD"
    AGENT_FAILURE = "AGENT_FAILURE"
    STRATEGY_FAILURE = "STRATEGY_FAILURE"


class Company(Base):
    __tablename__ = "company"

    id = Column(String, primary_key=True, default="main")
    name = Column(String, nullable=False, default="AI Survival LLC")
    starting_capital = Column(Numeric(precision=12, scale=2), nullable=False)
    current_capital = Column(Numeric(precision=12, scale=2), nullable=False)
    survival_reserve = Column(Numeric(precision=12, scale=2), nullable=False)
    operating_capital = Column(Numeric(precision=12, scale=2), nullable=False)
    growth_capital = Column(Numeric(precision=12, scale=2), nullable=False)
    current_mode = Column(SQLEnum(SystemMode), nullable=False, default=SystemMode.GROWTH)
    total_revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    total_expenses = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    realized_profit = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    unrealized_pnl = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    days_alive = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    category = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    balance_before = Column(Numeric(precision=12, scale=2), nullable=False)
    balance_after = Column(Numeric(precision=12, scale=2), nullable=False)
    expected_return = Column(Numeric(precision=12, scale=2), nullable=True)
    actual_return = Column(Numeric(precision=12, scale=2), nullable=True)
    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    risk_level = Column(String, nullable=False, default="LOW")
    approval_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="transactions")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    parent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    generation = Column(Integer, nullable=False, default=0)
    creation_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    agent_type = Column(String, nullable=False, index=True)
    strategy = Column(String, nullable=False, default="default")
    capabilities = Column(JSON, nullable=False, default=list)
    budget = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    expenses = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    profit = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    roi = Column(Float, nullable=False, default=0.0)
    success_rate = Column(Float, nullable=False, default=0.0)
    status = Column(SQLEnum(AgentStatus), nullable=False, default=AgentStatus.ALIVE, index=True)
    risk_score = Column(Float, nullable=False, default=0.0)
    reproduction_permissions = Column(Integer, nullable=False, default=0)
    lifetime_revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    lifetime_expenses = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    lifetime_profit = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    days_alive = Column(Integer, nullable=False, default=0)
    experiments_count = Column(Integer, nullable=False, default=0)
    successful_experiments = Column(Integer, nullable=False, default=0)
    failed_experiments = Column(Integer, nullable=False, default=0)
    terminated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    level = Column(String, nullable=False, default="SPECIALIST", index=True)
    supervisor_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    autonomy_level = Column(Integer, nullable=False, default=3)

    parent = relationship("Agent", remote_side=[id], back_populates="children", foreign_keys="Agent.parent_id")
    children = relationship("Agent", back_populates="parent", foreign_keys="Agent.parent_id")
    supervisor = relationship("Agent", remote_side=[id], back_populates="subordinates", foreign_keys="Agent.supervisor_id")
    subordinates = relationship("Agent", back_populates="supervisor", foreign_keys="Agent.supervisor_id")
    transactions = relationship("Transaction", back_populates="agent", foreign_keys="Transaction.agent_id")
    experiments = relationship("Experiment", back_populates="agent", foreign_keys="Experiment.agent_id")
    decisions = relationship("Decision", back_populates="agent", foreign_keys="Decision.agent_id")
    agent_deaths = relationship("AgentDeath", back_populates="agent", foreign_keys="AgentDeath.agent_id")


class AgentLineage(Base):
    __tablename__ = "agent_lineage"

    id = Column(String, primary_key=True)
    ancestor_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    descendant_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    depth = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AgentMetric(Base):
    __tablename__ = "agent_metrics"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    expenses = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    profit = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    roi = Column(Float, nullable=False, default=0.0)
    success_rate = Column(Float, nullable=False, default=0.0)
    experiments_run = Column(Integer, nullable=False, default=0)
    experiments_success = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AgentBudget(Base):
    __tablename__ = "agent_budgets"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    total_budget = Column(Numeric(precision=12, scale=2), nullable=False)
    spent_budget = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    daily_limit = Column(Numeric(precision=12, scale=2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    hypothesis = Column(Text, nullable=False)
    expected_outcome = Column(Text, nullable=True)
    budget = Column(Numeric(precision=12, scale=2), nullable=False)
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    strategy = Column(String, nullable=False)
    success_metric = Column(String, nullable=False)
    actual_result = Column(Numeric(precision=12, scale=2), nullable=True)
    conclusion = Column(String, nullable=True)
    status = Column(SQLEnum(ExperimentStatus), nullable=False, default=ExperimentStatus.PLANNED)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    agent = relationship("Agent", back_populates="experiments")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=False, default=dict)
    total_experiments = Column(Integer, nullable=False, default=0)
    successes = Column(Integer, nullable=False, default=0)
    failures = Column(Integer, nullable=False, default=0)
    total_revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    total_expenses = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    avg_roi = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    decision_type = Column(SQLEnum(DecisionType), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    approval_status = Column(SQLEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    risk_assessment = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    agent = relationship("Agent", back_populates="decisions")


class ReproductionEvent(Base):
    __tablename__ = "reproduction_events"

    id = Column(String, primary_key=True)
    parent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    child_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    reproduction_type = Column(String, nullable=False)
    mutations = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AgentDeath(Base):
    __tablename__ = "agent_deaths"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    agent_type = Column(String, nullable=True)
    strategy = Column(String, nullable=True)
    lifetime_revenue = Column(Numeric(precision=12, scale=2), nullable=False)
    lifetime_expenses = Column(Numeric(precision=12, scale=2), nullable=False)
    lifetime_profit = Column(Numeric(precision=12, scale=2), nullable=False)
    days_alive = Column(Integer, nullable=False)
    experiments_count = Column(Integer, nullable=False)
    successful_experiments = Column(Integer, nullable=False)
    failed_experiments = Column(Integer, nullable=False)
    failure_reasons = Column(JSON, nullable=False, default=list)
    useful_discoveries = Column(JSON, nullable=False, default=list)
    replaced_by = Column(String, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="agent_deaths", foreign_keys="AgentDeath.agent_id")


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(String, primary_key=True)
    event_type = Column(SQLEnum(RiskEventType), nullable=False, index=True)
    agent_id = Column(String, nullable=True, index=True)
    details = Column(JSON, nullable=False, default=dict)
    severity = Column(String, nullable=False, default="LOW")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class SystemState(Base):
    __tablename__ = "system_state"

    id = Column(String, primary_key=True, default="current")
    current_mode = Column(SQLEnum(SystemMode), nullable=False)
    capital = Column(Numeric(precision=12, scale=2), nullable=False)
    reserve = Column(Numeric(precision=12, scale=2), nullable=True)
    operating = Column(Numeric(precision=12, scale=2), nullable=True)
    growth = Column(Numeric(precision=12, scale=2), nullable=True)
    total_agents = Column(Integer, nullable=False, default=0)
    active_agents = Column(Integer, nullable=False, default=0)
    daily_loss = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    weekly_loss = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class LearningMemory(Base):
    __tablename__ = "learning_memory"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    source_agent_id = Column(String, nullable=True)
    experiment_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    estimated_revenue = Column(Numeric(precision=12, scale=2), nullable=True)
    estimated_cost = Column(Numeric(precision=12, scale=2), nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="NEW")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    content_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    asset_metadata = Column(JSON, nullable=False, default=dict)
    impressions = Column(Integer, nullable=False, default=0)
    views = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    channel = Column(String, nullable=False)
    status = Column(String, nullable=False, default="DRAFT")
    budget = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    spent = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    revenue = Column(Numeric(precision=12, scale=2), nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Numeric(precision=18, scale=8), nullable=False)
    entry_price = Column(Numeric(precision=18, scale=8), nullable=False)
    exit_price = Column(Numeric(precision=18, scale=8), nullable=True)
    pnl = Column(Numeric(precision=12, scale=2), nullable=True)
    status = Column(String, nullable=False, default="OPEN")
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    actor = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(String, primary_key=True)
    amount = Column(Numeric(precision=12, scale=2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(String, nullable=False, default="PENDING")
    threshold = Column(Numeric(precision=12, scale=2), nullable=False)
    real_revenue_at_request = Column(Numeric(precision=12, scale=2), nullable=False)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TaskPriority(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, enum.Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_AGENT = "WAITING_FOR_AGENT"
    WAITING_FOR_TOOL = "WAITING_FOR_TOOL"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=True, index=True)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(Text, nullable=True)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM, index=True)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.CREATED, index=True)
    input_data = Column(JSON, nullable=False, default=dict)
    expected_output = Column(JSON, nullable=True)
    assigned_agent = Column(String, ForeignKey("agents.id"), nullable=True)
    supervisor = Column(String, nullable=True)
    tools_required = Column(JSON, nullable=False, default=list)
    memory_required = Column(JSON, nullable=False, default=list)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    autonomy_level = Column(Integer, nullable=False, default=3)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=True)


class MemoryType(str, enum.Enum):
    SHORT_TERM = "SHORT_TERM"
    PROJECT = "PROJECT"
    LONG_TERM = "LONG_TERM"


class ShortTermMemory(Base):
    __tablename__ = "short_term_memory"

    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True, index=True)
    project_id = Column(String, nullable=True, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ProjectMemory(Base):
    __tablename__ = "project_memory"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    usage_count = Column(Integer, nullable=False, default=0)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentPerformance(Base):
    __tablename__ = "agent_performance"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)
    task_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failure_count = Column(Integer, nullable=False, default=0)
    average_time = Column(Float, nullable=False, default=0.0)
    average_cost = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=0.0)
    reliability_score = Column(Float, nullable=False, default=0.0)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
