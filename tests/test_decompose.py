from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.decompose import BoundaryDetector, BoundarySuggestion, CouplingEdge


class TestCouplingEdge:
    def test_to_dict(self):
        e = CouplingEdge(source="a", target="b", weight=3)
        d = e.to_dict()
        assert d == {"source": "a", "target": "b", "weight": 3}

    def test_default_weight(self):
        e = CouplingEdge(source="x", target="y")
        assert e.weight == 1


class TestBoundarySuggestion:
    def test_to_dict(self):
        b = BoundarySuggestion(name="svc", modules=["m1", "m2"], coupling_score=0.9, rationale="test")
        d = b.to_dict()
        assert d["name"] == "svc"
        assert len(d["modules"]) == 2

    def test_defaults(self):
        b = BoundarySuggestion(name="svc")
        assert b.modules == []
        assert b.coupling_score == 0.0
        assert b.rationale == ""


class TestBoundaryDetector:
    def test_compute_coupling_cross_module(self):
        graph = {
            "nodes": {"auth/login.py": {}, "auth/user.py": {}, "api/handler.py": {}},
            "edges": [
                {"source": "auth/login.py", "target": "api/handler.py"},
                {"source": "auth/user.py", "target": "api/handler.py"},
            ],
        }
        detector = BoundaryDetector()
        edges = detector.compute_coupling(graph)
        assert len(edges) >= 1
        assert edges[0].weight >= 2

    def test_compute_coupling_same_module_ignored(self):
        graph = {
            "nodes": {"auth/login.py": {}, "auth/user.py": {}},
            "edges": [{"source": "auth/login.py", "target": "auth/user.py"}],
        }
        detector = BoundaryDetector()
        edges = detector.compute_coupling(graph)
        assert len(edges) == 0

    def test_compute_coupling_empty(self):
        detector = BoundaryDetector()
        edges = detector.compute_coupling({"nodes": {}, "edges": []})
        assert edges == []

    def test_detect_boundaries_static(self):
        graph = {
            "nodes": {"auth/login.py": {}, "auth/user.py": {}, "api/handler.py": {}},
            "edges": [],
        }
        detector = BoundaryDetector()
        suggestions = detector.detect_boundaries_static(graph)
        assert len(suggestions) >= 1
        auth_suggestions = [s for s in suggestions if s.name == "auth"]
        assert len(auth_suggestions) == 1
        assert len(auth_suggestions[0].modules) == 2

    def test_detect_boundaries_static_single_file(self):
        graph = {"nodes": {"auth/login.py": {}}, "edges": []}
        detector = BoundaryDetector()
        suggestions = detector.detect_boundaries_static(graph)
        assert len(suggestions) == 0

    @pytest.mark.asyncio
    async def test_detect_boundaries_llm_success(self):
        detector = BoundaryDetector()
        mock_response = json.dumps(
            {
                "boundaries": [
                    {
                        "name": "auth-service",
                        "modules": ["auth/login.py", "auth/user.py"],
                        "coupling_score": 0.9,
                        "rationale": "shared domain",
                    }
                ]
            }
        )
        with patch.object(
            detector._client, "chat", new=AsyncMock(return_value={"status": "completed", "content": mock_response})
        ):
            graph = {"nodes": {"auth/login.py": {}, "auth/user.py": {}}, "edges": []}
            result = await detector.detect_boundaries_llm(graph)
            assert len(result) >= 1
            assert result[0].name == "auth-service"

    @pytest.mark.asyncio
    async def test_detect_boundaries_llm_fallback(self):
        detector = BoundaryDetector()
        with (
            patch.object(
                detector._client,
                "chat",
                new=AsyncMock(return_value={"status": "completed", "content": "not json at all"}),
            ),
            patch.object(detector._client, "extract_code", return_value="still not json"),
        ):
            graph = {"nodes": {"auth/login.py": {}, "auth/user.py": {}}, "edges": []}
            result = await detector.detect_boundaries_llm(graph)
            assert len(result) >= 1
