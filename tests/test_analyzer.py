from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer, DependencyGraph
from fusion_code_modelization.core.client import MLXClient

logger = logging.getLogger(__name__)


class TestDependencyGraph:
    def test_default_construction(self):
        graph = DependencyGraph()
        assert graph.nodes == {}
        assert graph.edges == []

    def test_construction_with_data(self):
        nodes = {"a.py": {"path": "a.py", "language": "python", "size_bytes": 50}}
        edges = [{"source": "a.py", "target": "os", "type": "import"}]
        graph = DependencyGraph(nodes=nodes, edges=edges)
        assert "a.py" in graph.nodes
        assert len(graph.edges) == 1
        assert graph.edges[0]["source"] == "a.py"

    def test_to_dict(self):
        nodes = {"a.py": {"path": "a.py"}, "b.py": {"path": "b.py"}}
        edges = [{"source": "a.py", "target": "b.py", "type": "import"}]
        graph = DependencyGraph(nodes=nodes, edges=edges)
        result = graph.to_dict()
        assert result["nodes"] == nodes
        assert result["edges"] == edges
        assert isinstance(result, dict)

    def test_to_dict_empty(self):
        graph = DependencyGraph()
        result = graph.to_dict()
        assert result == {"nodes": {}, "edges": []}

    def test_nodes_mutable(self):
        graph = DependencyGraph()
        graph.nodes["x.py"] = {"path": "x.py", "language": "python", "size_bytes": 10}
        assert "x.py" in graph.nodes

    def test_edges_mutable(self):
        graph = DependencyGraph()
        graph.edges.append({"source": "a", "target": "b", "type": "import"})
        assert len(graph.edges) == 1


class TestDependencyAnalyzer:
    def test_init_default(self):
        analyzer = DependencyAnalyzer()
        assert isinstance(analyzer._client, MLXClient)

    def test_init_custom_url(self):
        analyzer = DependencyAnalyzer(mlx_url="http://custom:9999/v1")
        assert analyzer._client.config.base_url == "http://custom:9999/v1"

    def test_init_with_client(self):
        client = MLXClient()
        analyzer = DependencyAnalyzer(client=client)
        assert analyzer._client is client

    def test_scan_directory_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.py").write_text("import os\nimport sys\n")
            Path(tmpdir, "utils.py").write_text("from pathlib import Path\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert len(graph.nodes) == 2
            assert "main.py" in graph.nodes
            assert "utils.py" in graph.nodes
            assert "os" in graph.nodes["main.py"]["dependencies"]
            assert "pathlib" in graph.nodes["utils.py"]["dependencies"]

    def test_scan_directory_multi_language(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("import json\n")
            Path(tmpdir, "Main.java").write_text("import java.util.List;\n")
            Path(tmpdir, "readme.txt").write_text("not code\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert len(graph.nodes) == 2
            assert "app.py" in graph.nodes
            assert "Main.java" in graph.nodes
            assert "readme.txt" not in graph.nodes

    def test_scan_directory_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = Path(tmpdir, "sub")
            sub.mkdir()
            Path(tmpdir, "root.py").write_text("import os\n")
            Path(sub, "child.py").write_text("import json\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert len(graph.nodes) == 2
            assert any("child.py" in n for n in graph.nodes)

    def test_scan_directory_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert len(graph.nodes) == 0
            assert len(graph.edges) == 0

    def test_scan_directory_nonexistent(self):
        analyzer = DependencyAnalyzer()
        graph = analyzer.scan_directory("/nonexistent/path/xyz")
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_scan_directory_edges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.py").write_text("import os\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert len(graph.edges) >= 1
            edge = graph.edges[0]
            assert edge["source"] == "a.py"
            assert edge["target"] == "os"
            assert edge["type"] == "import"

    def test_scan_directory_node_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "mod.py").write_text("import json\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            node = graph.nodes["mod.py"]
            assert "path" in node
            assert "language" in node
            assert "size_bytes" in node
            assert "dependencies" in node
            assert node["language"] == "python"
            assert node["size_bytes"] > 0

    def test_identify_dead_code(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.nodes["b.py"] = {"path": "b.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.edges = [{"source": "a.py", "target": "b.py", "type": "import"}]
        dead = DependencyAnalyzer().identify_dead_code(graph)
        assert "a.py" in dead
        assert "b.py" not in dead

    def test_identify_dead_code_all_dead(self):
        graph = DependencyGraph()
        graph.nodes["x.py"] = {"path": "x.py", "language": "python", "size_bytes": 10, "dependencies": []}
        graph.nodes["y.py"] = {"path": "y.py", "language": "python", "size_bytes": 20, "dependencies": []}
        dead = DependencyAnalyzer().identify_dead_code(graph)
        assert len(dead) == 2
        assert "x.py" in dead
        assert "y.py" in dead

    def test_identify_dead_code_none_dead(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.nodes["b.py"] = {"path": "b.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.edges = [
            {"source": "a.py", "target": "b.py", "type": "import"},
            {"source": "b.py", "target": "a.py", "type": "import"},
        ]
        dead = DependencyAnalyzer().identify_dead_code(graph)
        assert len(dead) == 0

    def test_identify_dead_code_empty_graph(self):
        graph = DependencyGraph()
        dead = DependencyAnalyzer().identify_dead_code(graph)
        assert dead == []

    def test_estimate_tech_debt(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 1024, "dependencies": []}
        graph.nodes["b.py"] = {"path": "b.py", "language": "java", "size_bytes": 2048, "dependencies": []}
        graph.edges = [{"source": "a.py", "target": "b.py", "type": "import"}]
        debt = DependencyAnalyzer().estimate_tech_debt(graph)
        assert debt["total_files"] == 2
        assert debt["total_size_bytes"] == 3072
        assert debt["total_size_mb"] == round(3072 / (1024 * 1024), 2)
        assert debt["dead_files"] == 1

    def test_estimate_tech_debt_empty(self):
        graph = DependencyGraph()
        debt = DependencyAnalyzer().estimate_tech_debt(graph)
        assert debt["total_files"] == 0
        assert debt["total_size_bytes"] == 0
        assert debt["total_size_mb"] == 0.0
        assert debt["dead_files"] == 0

    def test_estimate_tech_debt_size_mb_precision(self):
        graph = DependencyGraph()
        graph.nodes["big.py"] = {"path": "big.py", "language": "python", "size_bytes": 1572864, "dependencies": []}
        debt = DependencyAnalyzer().estimate_tech_debt(graph)
        assert debt["total_size_mb"] == 1.5

    @pytest.mark.asyncio
    async def test_analyze_with_llm_json_response(self):
        analyzer = DependencyAnalyzer()
        payload = {"purpose": "data processing", "inputs": ["csv file"], "outputs": ["report"]}
        with patch.object(
            analyzer._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": json.dumps(payload)}),
        ):
            result = await analyzer.analyze_with_llm("import pandas as pd\ndf = pd.read_csv('data.csv')", "python")
            assert result["purpose"] == "data processing"
            assert "inputs" in result

    @pytest.mark.asyncio
    async def test_analyze_with_llm_non_json_response(self):
        analyzer = DependencyAnalyzer()
        with patch.object(
            analyzer._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "This code processes data files."}),
        ):
            result = await analyzer.analyze_with_llm("x = 1", "python")
            assert "analysis" in result
            assert result["analysis"] == "This code processes data files."

    @pytest.mark.asyncio
    async def test_analyze_with_llm_failure(self):
        analyzer = DependencyAnalyzer()
        with patch.object(
            analyzer._client,
            "chat",
            new=AsyncMock(return_value={"status": "failed", "error": "connection refused"}),
        ):
            result = await analyzer.analyze_with_llm("x = 1", "python")
            assert "error" in result
            assert result["error"] == "connection refused"

    def test_detect_language_known(self):
        assert DependencyAnalyzer._detect_language(".py") == "python"
        assert DependencyAnalyzer._detect_language(".java") == "java"
        assert DependencyAnalyzer._detect_language(".c") == "c"
        assert DependencyAnalyzer._detect_language(".cpp") == "cpp"
        assert DependencyAnalyzer._detect_language(".cs") == "csharp"
        assert DependencyAnalyzer._detect_language(".js") == "javascript"
        assert DependencyAnalyzer._detect_language(".ts") == "typescript"
        assert DependencyAnalyzer._detect_language(".go") == "go"
        assert DependencyAnalyzer._detect_language(".rs") == "rust"
        assert DependencyAnalyzer._detect_language(".php") == "php"
        assert DependencyAnalyzer._detect_language(".rb") == "ruby"
        assert DependencyAnalyzer._detect_language(".swift") == "swift"
        assert DependencyAnalyzer._detect_language(".kt") == "kotlin"
        assert DependencyAnalyzer._detect_language(".scala") == "scala"
        assert DependencyAnalyzer._detect_language(".cbl") == "cobol"
        assert DependencyAnalyzer._detect_language(".cpy") == "cobol"
        assert DependencyAnalyzer._detect_language(".vba") == "vb6"
        assert DependencyAnalyzer._detect_language(".bas") == "vb6"

    def test_detect_language_unknown(self):
        assert DependencyAnalyzer._detect_language(".xyz") == ""
        assert DependencyAnalyzer._detect_language(".txt") == ""
        assert DependencyAnalyzer._detect_language("") == ""

    def test_extract_imports_python(self):
        code = "import os\nimport sys\nfrom pathlib import Path\nfrom collections import defaultdict\n"
        deps = DependencyAnalyzer._extract_imports(code, "python")
        assert "os" in deps
        assert "sys" in deps
        assert "pathlib" in deps
        assert "collections" in deps

    def test_extract_imports_python_no_duplicates(self):
        code = "import os\nimport os\n"
        deps = DependencyAnalyzer._extract_imports(code, "python")
        assert deps.count("os") == 1

    def test_extract_imports_java(self):
        code = "import java.util.List;\nimport java.io.File;\n"
        deps = DependencyAnalyzer._extract_imports(code, "java")
        assert "java.util.List" in deps
        assert "java.io.File" in deps

    def test_extract_imports_c(self):
        code = '#include <stdio.h>\n#include "myheader.h"\n'
        deps = DependencyAnalyzer._extract_imports(code, "c")
        assert "stdio.h" in deps
        assert "myheader.h" in deps

    def test_extract_imports_cpp(self):
        code = '#include <vector>\n#include "utils.h"\n'
        deps = DependencyAnalyzer._extract_imports(code, "cpp")
        assert "vector" in deps
        assert "utils.h" in deps

    def test_extract_imports_csharp(self):
        code = "using System;\nusing System.Collections.Generic;\n"
        deps = DependencyAnalyzer._extract_imports(code, "csharp")
        assert "System" in deps
        assert "System.Collections.Generic" in deps

    def test_extract_imports_javascript_import(self):
        code = "import React from 'react';\nimport * as fs from 'fs';\n"
        deps = DependencyAnalyzer._extract_imports(code, "javascript")
        assert "react" in deps
        assert "fs" in deps

    def test_extract_imports_javascript_require(self):
        code = "require 'lodash';\nrequire 'express';\n"
        deps = DependencyAnalyzer._extract_imports(code, "javascript")
        assert "lodash" in deps
        assert "express" in deps

    def test_extract_imports_go(self):
        code = 'import "fmt"\nimport "os"\n'
        deps = DependencyAnalyzer._extract_imports(code, "go")
        assert "fmt" in deps
        assert "os" in deps

    def test_extract_imports_unsupported_language(self):
        deps = DependencyAnalyzer._extract_imports("some code", "brainfuck")
        assert deps == []

    def test_generate_report(self):
        graph = DependencyGraph()
        graph.nodes["a.py"] = {"path": "a.py", "language": "python", "size_bytes": 100, "dependencies": []}
        graph.nodes["b.java"] = {"path": "b.java", "language": "java", "size_bytes": 200, "dependencies": []}
        debt = {"total_files": 2, "total_size_bytes": 300, "total_size_mb": 0.0, "dead_files": 1}
        report = DependencyAnalyzer.generate_report(graph, debt)
        assert "# Code Modernization Analysis Report" in report
        assert "2" in report
        assert "python" in report
        assert "java" in report

    def test_generate_report_empty(self):
        graph = DependencyGraph()
        debt = {"total_files": 0, "total_size_bytes": 0, "total_size_mb": 0.0, "dead_files": 0}
        report = DependencyAnalyzer.generate_report(graph, debt)
        assert "Total files: 0" in report

    def test_generate_report_language_distribution_sorted(self):
        graph = DependencyGraph()
        for i in range(5):
            graph.nodes[f"mod{i}.py"] = {
                "path": f"mod{i}.py",
                "language": "python",
                "size_bytes": 10,
                "dependencies": [],
            }
        graph.nodes["app.java"] = {"path": "app.java", "language": "java", "size_bytes": 20, "dependencies": []}
        debt = {"total_files": 6, "total_size_bytes": 70, "total_size_mb": 0.0, "dead_files": 0}
        report = DependencyAnalyzer.generate_report(graph, debt)
        lines = report.split("\n")
        python_idx = next(i for i, ln in enumerate(lines) if "python" in ln)
        java_idx = next(i for i, ln in enumerate(lines) if "java" in ln)
        assert python_idx < java_idx

    @pytest.mark.asyncio
    async def test_analyze_with_llm_invalid_json(self):
        analyzer = DependencyAnalyzer()
        with patch.object(
            analyzer._client,
            "chat",
            new=AsyncMock(return_value={"status": "completed", "content": "{invalid json"}),
        ):
            result = await analyzer.analyze_with_llm("x = 1", "python")
            assert "analysis" in result

    def test_scan_directory_with_cobol(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "legacy.cbl").write_text("IDENTIFICATION DIVISION.\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(tmpdir)
            assert "legacy.cbl" in graph.nodes
            assert graph.nodes["legacy.cbl"]["language"] == "cobol"

    def test_scan_directory_path_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "mod.py").write_text("import os\n")
            analyzer = DependencyAnalyzer()
            graph = analyzer.scan_directory(Path(tmpdir))
            assert "mod.py" in graph.nodes
