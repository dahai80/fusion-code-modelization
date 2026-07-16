"""Fusion-Code-Modelization — Legacy code modernization and cross-language migration.

All model inference goes through fusion-mlx HTTP API.
Never imports OpenAI, Anthropic, or any cloud AI service directly.
"""

from .analyzer.dependency import DependencyAnalyzer, DependencyGraph
from .migration.transpiler import CodeTranspiler
from .refactor.refactorer import IncrementalRefactorer
from .test_gen.generator import TestGenerator
from .security.scanner import SecurityScanner
from .pipeline import PipelineIntegrator, PriorityScorer, AuditLog
from .pr_gen import PRGenerator, DocGenerator, MicroserviceDecomposer

__all__ = [
    "DependencyAnalyzer", "DependencyGraph",
    "CodeTranspiler",
    "IncrementalRefactorer",
    "TestGenerator",
    "SecurityScanner",
    "PipelineIntegrator", "PriorityScorer", "AuditLog",
    "PRGenerator", "DocGenerator", "MicroserviceDecomposer",
]