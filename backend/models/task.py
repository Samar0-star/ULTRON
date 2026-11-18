from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set


@dataclass
class SubTask:
    """
    Godzilla Atomic Sub-Task.
    Represents a single unit of work for a multi-agent swarm.
    """
    id: str
    description: str
    type: str = "research"
    task_type: str = "research"  # BACKWARD COMPATIBILITY
    agent: Optional[str] = "research_agent"
    tool: Optional[str] = None
    adapter: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    can_run_parallel: bool = True
    priority: int = 5
    status: str = "pending"
    required_tools: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    capabilities_needed: List[str] = field(default_factory=list)
    estimated_minutes: float = 30.0
    estimated_seconds: float = 10.0
    timeout: float = 120.0
    retry_count: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)
    target_hypothesis_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        # [GODZILLA ALIGNMENT] Support both 'type' and 'task_type' for cross-version stability
        if hasattr(self, "task_type") and not self.type:
            self.type = getattr(self, "task_type")
        elif self.type and self.task_type == "research" and self.type != "research":
            self.task_type = self.type

    def has_dependencies(self) -> bool:
        return bool(self.dependencies)

    def can_run_after(self, completed_ids: Set[str]) -> bool:
        if not self.dependencies:
            return True
        return all(dep in completed_ids for dep in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubTask":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
