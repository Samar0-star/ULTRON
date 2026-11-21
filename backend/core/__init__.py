"""
SVEL BEAST Core Components
=============================

Core infrastructure for GODZILLA-tier autonomous research:
- Message bus for agent communication
- Task decomposition
- World model for shared knowledge (CHROMADB + HYPERGRAPH!)
- Result merging
- Fallback management
- Context compression (20:1 ratio for token efficiency)
"""

from .message_bus import MessageBus, Message, MessageType, get_message_bus
from .task_decomposer import NeuralFractalizer, SubTask
from backend.core.world_model import WorldModel, Fact, Conflict
from .result_merger import ResultMerger, MergeResult
from .fallback_manager import FallbackManager, get_fallback_manager, ProviderStatus
from .context_compressor import (
    ContextCompressor,
    CompressedContext,
    get_context_compressor,
    compress_task,
    compress_cycle,
    compress_mission
)

__all__ = [
    'MessageBus', 'Message', 'MessageType', 'get_message_bus',
    'NeuralFractalizer', 'SubTask',
    'WorldModel', 'Fact', 'Conflict',
    'ResultMerger', 'MergeResult',
    'FallbackManager', 'get_fallback_manager', 'ProviderStatus',
    # Ultra-Upgrade: Context Compression
    'ContextCompressor', 'CompressedContext', 'get_context_compressor',
    'compress_task', 'compress_cycle', 'compress_mission'
]

