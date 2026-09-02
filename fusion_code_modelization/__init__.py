"""Fusion-Code-Modelization — Legacy code modernization and cross-language migration.

All model inference goes through fusion-gateway HTTP API via MLXClient.
Never imports OpenAI, Anthropic, or any cloud AI service directly.

Public symbols are lazy-imported via __getattr__ to avoid eagerly pulling the
full 20+ submodule dependency surface on a single-module import.
"""

from __future__ import annotations

import importlib
from typing import Any

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("fusion-code-modelization")
except (ImportError, PackageNotFoundError):
    __version__ = "0.0.0"

_LAZY_EXPORTS: dict[str, str] = {
    "MLXClient": "core.client",
    "DualStackClient": "core.client",
    "ModelConfig": "core.config",
    "DualModelConfig": "core.config",
    "ModelRouter": "core.config",
    "ModelStack": "core.config",
    "OfflineConfig": "core.config",
    "OfflineMode": "core.config",
    "RoutingStrategy": "core.config",
    "MODEL_PRESETS": "core.config",
    "get_model_config": "core.config",
    "DependencyAnalyzer": "analyzer.dependency",
    "DependencyGraph": "analyzer.dependency",
    "CodeTranspiler": "migration.transpiler",
    "IncrementalRefactorer": "refactor.refactorer",
    "UnitTestGenerator": "test_gen.generator",
    "SecurityScanner": "security.scanner",
    "PipelineIntegrator": "pipeline",
    "PriorityScorer": "pipeline",
    "AuditLog": "pipeline",
    "PRGenerator": "pr_gen",
    "DocGenerator": "pr_gen",
    "MicroserviceDecomposer": "pr_gen",
    "BoundaryType": "pr_gen",
    "SessionEngine": "session",
    "Session": "session",
    "SessionState": "session",
    "SessionStore": "session",
    "FileDelta": "snapshot",
    "Snapshot": "snapshot",
    "compute_delta": "snapshot",
    "apply_delta": "snapshot",
    "SnapshotManager": "snapshot",
    "SubTask": "workflow",
    "WorkflowPlan": "workflow",
    "TaskDecomposer": "workflow",
    "WORKFLOW_TEMPLATES": "workflow",
    "SubTaskResult": "workflow",
    "WorkflowResult": "workflow",
    "WorkflowExecutor": "workflow",
    "MemoryTier": "memory",
    "MemoryEntry": "memory",
    "MemoryTierManager": "memory",
    "MemoryContext": "memory",
    "CouplingEdge": "decompose",
    "BoundarySuggestion": "decompose",
    "BoundaryDetector": "decompose",
    "DocSection": "doc_gen",
    "DocumentationGenerator": "doc_gen",
    "AuditLogger": "audit",
    "AuditStore": "audit",
    "AuditAction": "audit",
    "AuditSeverity": "audit",
    "AuditEntry": "audit",
    "AuditFilter": "audit",
    "AuditReport": "audit",
    "ClusterScheduler": "cluster",
    "NodeClient": "cluster",
    "NodeInfo": "cluster",
    "NodeStatus": "cluster",
    "TaskDispatch": "cluster",
    "TaskDispatchStatus": "cluster",
    "PluginManager": "plugin",
    "PluginRegistry": "plugin",
    "PluginManifest": "plugin",
    "PluginAction": "plugin",
    "PluginCategory": "plugin",
    "PluginStatus": "plugin",
    "BenchmarkCategory": "benchmark",
    "BenchmarkItem": "benchmark",
    "BenchmarkReport": "benchmark",
    "BenchmarkResult": "benchmark",
    "BenchmarkRunner": "benchmark",
    "BenchmarkStatus": "benchmark",
    "BenchmarkSuite": "benchmark",
    "PredefinedBenchmarkSuites": "benchmark",
    "AffinityBasedStrategy": "loadbalancer",
    "BalancerConfig": "loadbalancer",
    "LeastLoadedStrategy": "loadbalancer",
    "LoadBalanceStrategy": "loadbalancer",
    "LoadBalancer": "loadbalancer",
    "LoadMetric": "loadbalancer",
    "RoundRobinStrategy": "loadbalancer",
    "SchedulingDecision": "loadbalancer",
    "WeightedCapacityStrategy": "loadbalancer",
    "get_strategy": "loadbalancer",
    "CAPABILITY_MATRIX": "offline",
    "OfflineCache": "offline",
    "OfflineCapability": "offline",
    "OfflineManager": "offline",
    "OfflineDeployMode": "offline:OfflineMode",
    "OfflinePackage": "offline",
    "ArtifactType": "trace",
    "RelationshipType": "trace",
    "TraceChain": "trace",
    "TraceEdge": "trace",
    "TraceNode": "trace",
    "TraceReport": "trace",
    "TraceStore": "trace",
    "TraceTracker": "trace",
    "AgentChannel": "agent_comm",
    "AgentChannelManager": "agent_comm",
    "AgentMessage": "agent_comm",
    "AgentRole": "agent_comm",
    "CollaborationCoordinator": "agent_comm",
    "CollaborationStatus": "agent_comm",
    "CollaborationTask": "agent_comm",
    "MessageType": "agent_comm",
}

__all__ = sorted(_LAZY_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    spec = _LAZY_EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, _, attr_name = spec.partition(":")
    module = importlib.import_module(f"{__name__}.{module_path}")
    value = getattr(module, attr_name or name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))
