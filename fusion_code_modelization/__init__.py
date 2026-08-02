"""Fusion-Code-Modelization — Legacy code modernization and cross-language migration.

All model inference goes through fusion-mlx HTTP API via MLXClient.
Never imports OpenAI, Anthropic, or any cloud AI service directly.
"""

from .analyzer.dependency import DependencyAnalyzer, DependencyGraph
from .audit import AuditAction, AuditEntry, AuditFilter, AuditLogger, AuditReport, AuditSeverity, AuditStore
from .cluster import ClusterScheduler, NodeClient, NodeInfo, NodeStatus, TaskDispatch, TaskDispatchStatus
from .core.client import DualStackClient, MLXClient
from .core.config import (
    MODEL_PRESETS,
    DualModelConfig,
    ModelConfig,
    ModelRouter,
    ModelStack,
    RoutingStrategy,
    get_model_config,
)
from .decompose import BoundaryDetector, BoundarySuggestion, CouplingEdge
from .doc_gen import DocSection, DocumentationGenerator
from .memory import MemoryContext, MemoryEntry, MemoryTier, MemoryTierManager
from .migration.transpiler import CodeTranspiler
from .pipeline import AuditLog, PipelineIntegrator, PriorityScorer
from .plugin import PluginAction, PluginCategory, PluginManager, PluginManifest, PluginRegistry, PluginStatus
from .pr_gen import DocGenerator, MicroserviceDecomposer, PRGenerator
from .refactor.refactorer import IncrementalRefactorer
from .security.scanner import SecurityScanner
from .session import Session, SessionEngine, SessionState, SessionStore
from .snapshot import FileDelta, Snapshot, SnapshotManager, apply_delta, compute_delta
from .test_gen.generator import UnitTestGenerator
from .workflow import (
    WORKFLOW_TEMPLATES,
    SubTask,
    SubTaskResult,
    TaskDecomposer,
    WorkflowExecutor,
    WorkflowPlan,
    WorkflowResult,
)

__all__ = [
    "MLXClient",
    "DualStackClient",
    "ModelConfig",
    "DualModelConfig",
    "ModelRouter",
    "ModelStack",
    "RoutingStrategy",
    "MODEL_PRESETS",
    "get_model_config",
    "DependencyAnalyzer",
    "DependencyGraph",
    "CodeTranspiler",
    "IncrementalRefactorer",
    "UnitTestGenerator",
    "SecurityScanner",
    "PipelineIntegrator",
    "PriorityScorer",
    "AuditLog",
    "PRGenerator",
    "DocGenerator",
    "MicroserviceDecomposer",
    "SessionEngine",
    "Session",
    "SessionState",
    "SessionStore",
    "FileDelta",
    "Snapshot",
    "compute_delta",
    "apply_delta",
    "SnapshotManager",
    "SubTask",
    "WorkflowPlan",
    "TaskDecomposer",
    "WORKFLOW_TEMPLATES",
    "SubTaskResult",
    "WorkflowResult",
    "WorkflowExecutor",
    "MemoryTier",
    "MemoryEntry",
    "MemoryTierManager",
    "MemoryContext",
    "CouplingEdge",
    "BoundarySuggestion",
    "BoundaryDetector",
    "DocSection",
    "DocumentationGenerator",
    "AuditLogger",
    "AuditStore",
    "AuditAction",
    "AuditSeverity",
    "AuditEntry",
    "AuditFilter",
    "AuditReport",
    "ClusterScheduler",
    "NodeClient",
    "NodeInfo",
    "NodeStatus",
    "TaskDispatch",
    "TaskDispatchStatus",
    "PluginManager",
    "PluginRegistry",
    "PluginManifest",
    "PluginAction",
    "PluginCategory",
    "PluginStatus",
]
