# Evidence-grade recon engine (issue #37): mounts an external REA MCP server
# over stdio and turns its findings into versioned, auditable pipeline artifacts.
#
# Degradation contract: any MCP failure (missing allowlist entry, spawn error,
# protocol error, timeout) degrades to status="skipped" — the modernization
# pipeline continues without recon. REA runs on operator infrastructure only,
# against targets the customer owns or has written authorization to analyze.

from .engine import DEFAULT_RECON_PLAN, ReconEngine
from .parity import ParityChecker

__all__ = ["ReconEngine", "ParityChecker", "DEFAULT_RECON_PLAN"]
