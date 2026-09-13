from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Text
from datetime import datetime
from ..database.connection import Base


class AgentImprovement(Base):
    __tablename__ = "agent_improvements"

    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    cycle = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="PENDING")
    self_analysis = Column(JSON, nullable=True)
    weaknesses_found = Column(JSON, nullable=False, default=list)
    improvement_plan = Column(JSON, nullable=True)
    execution_results = Column(JSON, nullable=True)
    learning = Column(JSON, nullable=True)
    improvements_applied = Column(Integer, nullable=False, default=0)
    improvements_failed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
