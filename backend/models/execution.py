# backend/models/execution.py
"""
Execution Database Model
====================
SQLAlchemy model for tracking research executions within the isolated compute container.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ResearchLog(Base):
    """
    Stores all AI queries and responses for audit trailing and debugging.
    """
    __tablename__ = "research_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=True, index=True)
    
    query = Column(Text, nullable=False)
    query_type = Column(String(50), default="research")
    
    response = Column(Text, nullable=True)
    response_tokens = Column(Integer, nullable=True)
    
    context = Column(Text, nullable=True)
    tools_used = Column(Text, nullable=True)
    agent_flow = Column(Text, nullable=True)
    
    search_results = Column(Text, nullable=True)
    
    latency_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ResearchLog id={self.id} session_id={self.session_id} query={self.query[:30]}...>"


class ResearchExecution(Base):
    """Tracks a full research session (Beast Execution)"""
    __tablename__ = "research_executions"

    id = Column(String(255), primary_key=True)  # trace_id
    query = Column(Text, nullable=False)
    status = Column(String(50), default="pending")  # pending, running, success, error
    mode = Column(String(50), default="standard")   # deep, standard, fast
    
    # Timing
    start_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_s = Column(Float, nullable=True)
    
    # Results
    final_report = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    
    # Metadata
    context = Column(Text, nullable=True)
    stats = Column(Text, nullable=True)

    # Relationships
    steps = relationship("TraceStep", back_populates="execution", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="execution", cascade="all, delete-orphan")


class TraceStep(Base):
    """Tracks individual steps within a research session"""
    __tablename__ = "trace_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255), ForeignKey("research_executions.id", ondelete="CASCADE"), nullable=False)
    
    step_type = Column(String(50))
    agent_id = Column(String(255), nullable=True)
    tool_name = Column(String(255), nullable=True)
    
    status = Column(String(50), default="running")
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    
    start_time = Column(DateTime(timezone=True), default=datetime.utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_s = Column(Float, nullable=True)
    
    metadata_json = Column(Text, nullable=True)

    execution = relationship("ResearchExecution", back_populates="steps")


class Artifact(Base):
    """Tracks files generated during research"""
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(255), ForeignKey("research_executions.id", ondelete="CASCADE"), nullable=False)
    
    artifact_type = Column(String(50))
    filename = Column(String(255))
    file_path = Column(String(512))
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    execution = relationship("ResearchExecution", back_populates="artifacts")
