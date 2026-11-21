"""
AVON-1 Orchestration Layer
===========================

Multi-agent orchestration components for SVEL-level autonomous research.

Components:
- AgentCoordinator: Manages agent lifecycle and task assignment
- ParallelExecutor: Concurrent execution with dependency management
- SVELTracer: Comprehensive execution logging
- SVELOrchestrator: Main orchestration engine
"""

from .beast_tracer import SVELTracer, TraceStep, ExecutionTrace, BeastTracer
from .singularity import SingularityEngine, get_singularity
from .overmind import Overmind, get_overmind
from .swarm_manager import SwarmManager, get_swarm_manager, ConsensusEngine

__all__ = [
    'SVELTracer', 'TraceStep', 'ExecutionTrace', 'BeastTracer',
    'SingularityEngine', 'get_singularity',
    'Overmind', 'get_overmind',
    'SwarmManager', 'get_swarm_manager', 'ConsensusEngine',
]

