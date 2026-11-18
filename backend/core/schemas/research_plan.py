# backend/core/schemas/research_plan.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PlannedTask(BaseModel):
    id: str = Field(description="Unique task identifier, e.g. task_1, exp_alpha")
    description: str = Field(description="Clear, actionable task description")
    agent: str = Field(description="Assigned agent: research_agent, experiment_agent, etc.")
    priority: int = Field(default=5, ge=1, le=10, description="Priority score 1-10")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks that must finish before this runs")
    estimated_minutes: float = Field(default=15.0, description="Estimated execution time in minutes")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Input parameters and query variables")

class ResearchPlanSchema(BaseModel):
    cycle: int = Field(default=1, description="Current research campaign cycle")
    objective: str = Field(description="Primary research objective")
    tasks: List[PlannedTask] = Field(min_length=1, description="Topologically ordered execution tasks")
    exploration_ratio: float = Field(default=0.3, ge=0.0, le=1.0, description="Balance between exploration and exploitation")
    rationale: str = Field(default="", description="Strategic rationale for this plan")
