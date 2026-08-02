# GateGuard: New file. Importers: fusion_code_modelization/__init__.py, cli/__init__.py, core/config.py, tests/test_offline.py. Affected API: none. Data schemas: OfflineMode, OfflineCapability, OfflinePackage. User instruction: Phase 4 V2.0 — offline module exports per enhancement doc.

from .cache import OfflineCache
from .manager import OfflineManager
from .models import CAPABILITY_MATRIX, OfflineCapability, OfflineMode, OfflinePackage

__all__ = [
    "CAPABILITY_MATRIX",
    "OfflineCache",
    "OfflineCapability",
    "OfflineManager",
    "OfflineMode",
    "OfflinePackage",
]
