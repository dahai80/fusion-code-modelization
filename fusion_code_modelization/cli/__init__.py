# GateGuard: Importers: pyproject.toml [project.scripts]. Affected API: adds --stream flag to 5 subcommands, bumps VERSION. Data schemas: none. User instruction: Phase 6 — streaming CLI support.

"""Fusion-Code-Modelization CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

VERSION = "0.6.0"

logger = logging.getLogger("fusion_code_modelization")


class _GlobalFlags:
    json_output: bool = False
    quiet: bool = False


_global_flags = _GlobalFlags()


def main():
    parser = argparse.ArgumentParser(description="Fusion-Code-Modelization — Legacy code modernization")
    parser.add_argument("--mlx-url", default="http://localhost:11434/v1", help="fusion-mlx URL")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")

    sub = parser.add_subparsers(dest="command")

    # analyze
    a = sub.add_parser("analyze", help="Analyze codebase dependencies")
    a.add_argument("path", help="Directory to analyze")
    a.add_argument("--output", default="", help="Report output path")

    # transpile
    t = sub.add_parser("transpile", help="Transpile code between languages")
    t.add_argument("file", help="Source file to transpile")
    t.add_argument("--from", dest="source_lang", required=True, help="Source language")
    t.add_argument("--to", dest="target_lang", required=True, help="Target language")
    t.add_argument("--output", default="", help="Output file path")
    t.add_argument("--stream", action="store_true", help="Stream LLM output in real time")

    # refactor
    r = sub.add_parser("refactor", help="Refactor code incrementally")
    r.add_argument("file", help="File to refactor")
    r.add_argument("--instructions", default="", help="Refactoring instructions")
    r.add_argument("--output", default="", help="Output file path")
    r.add_argument("--stream", action="store_true", help="Stream LLM output in real time")

    # test-gen
    tg = sub.add_parser("test-gen", help="Generate unit tests")
    tg.add_argument("file", help="Source file")
    tg.add_argument("--language", default="", help="Programming language")
    tg.add_argument("--output", default="", help="Output file path")
    tg.add_argument("--stream", action="store_true", help="Stream LLM output in real time")

    # security
    s = sub.add_parser("security", help="Scan for security vulnerabilities")
    s.add_argument("file", help="File to scan")
    s.add_argument("--language", default="", help="Programming language")
    s.add_argument("--output", default="", help="Output file path")
    s.add_argument("--stream", action="store_true", help="Stream LLM output in real time")

    # session
    se = sub.add_parser("session", help="Manage parallel sessions")
    se.add_argument("action", choices=["create", "list", "start", "pause", "resume", "complete", "delete"])
    se.add_argument("--id", dest="session_id", default="", help="Session ID")
    se.add_argument("--name", default="", help="Session name")

    # snapshot
    sn = sub.add_parser("snapshot", help="Incremental snapshots and rollback")
    sn.add_argument("action", choices=["create", "list", "restore", "rewind", "delete"])
    sn.add_argument("--project-dir", default=".", help="Project directory")
    sn.add_argument("--id", dest="snapshot_id", default="", help="Snapshot ID")
    sn.add_argument("--label", default="", help="Snapshot label")
    sn.add_argument("--steps", type=int, default=1, help="Steps to rewind")

    # workflow
    wf = sub.add_parser("workflow", help="Dynamic task decomposition and execution")
    wf.add_argument("action", choices=["decompose", "run"])
    wf.add_argument("--description", default="", help="Task description to decompose")
    wf.add_argument("--template", default="generic", help="Workflow template")
    wf.add_argument("--max-parallel", type=int, default=4, help="Max parallel tasks")

    # memory
    me = sub.add_parser("memory", help="Three-tier project memory (FUSION.md)")
    me.add_argument("action", choices=["init", "list", "load", "query"])
    me.add_argument("--project-dir", default=".", help="Project directory")
    me.add_argument("--query", default="", help="Query text")

    # sandbox
    sb = sub.add_parser("sandbox", help="Security sandbox and audit")
    sb.add_argument("action", choices=["check", "audit"])
    sb.add_argument("--path", default=".", help="Path to check")
    sb.add_argument("--mode", default="readonly", choices=["readonly", "manual", "auto"], help="Security mode")

    # decompose
    dc = sub.add_parser("decompose", help="Microservice boundary detection")
    dc.add_argument("path", help="Project directory to analyze")
    dc.add_argument("--method", default="static", choices=["static", "llm"], help="Detection method")
    dc.add_argument("--output", default="", help="Output file path")

    # doc-gen
    dg = sub.add_parser("doc-gen", help="Documentation generation")
    dg.add_argument("file", help="Source file")
    dg.add_argument("--type", dest="doc_type", default="module", choices=["module", "class", "api"], help="Doc type")
    dg.add_argument("--language", default="", help="Programming language")
    dg.add_argument("--output", default="", help="Output file path")
    dg.add_argument("--stream", action="store_true", help="Stream LLM output in real time")

    # audit
    au = sub.add_parser("audit", help="Enterprise audit system")
    au.add_argument("action", choices=["log", "search", "export", "stats", "cleanup"])
    au.add_argument("--action-type", default="", help="Filter by action type")
    au.add_argument("--actor", default="", help="Filter by actor")
    au.add_argument("--severity", default="", choices=["info", "warning", "critical"], help="Filter by severity")
    au.add_argument("--start-time", default="", help="Start time filter (ISO format)")
    au.add_argument("--end-time", default="", help="End time filter (ISO format)")
    au.add_argument("--format", default="json", choices=["json", "csv", "markdown"], help="Export format")
    au.add_argument("--output", default="", help="Output file path")
    au.add_argument("--max-age-days", type=int, default=90, help="Cleanup: max age in days")

    # cluster
    cl = sub.add_parser("cluster", help="Distributed cluster scheduling")
    cl.add_argument("action", choices=["discover", "dispatch", "status", "schedule", "migrate", "register", "tasks"])
    cl.add_argument("--node-id", default="", help="Target node ID")
    cl.add_argument("--host", default="localhost", help="Node host")
    cl.add_argument("--port", type=int, default=11434, help="Node port")
    cl.add_argument("--session-id", default="", help="Session ID to dispatch")
    cl.add_argument("--from-node", default="", help="Source node for migration")
    cl.add_argument("--to-node", default="", help="Target node for migration")
    cl.add_argument("--description", default="", help="Task description")
    cl.add_argument("--require-gpu", action="store_true", help="Require GPU for scheduling")

    # plugin
    pl = sub.add_parser("plugin", help="MCP plugin platform")
    pl.add_argument("action", choices=["list", "search", "install", "load", "unload", "execute", "status"])
    pl.add_argument("--plugin-id", default="", help="Plugin ID")
    pl.add_argument("--name", default="", help="Plugin name for registration")
    pl.add_argument("--category", default="", help="Filter by category")
    pl.add_argument("--action-name", default="", help="Action to execute")
    pl.add_argument("--query", default="", help="Search query")

    # version
    sub.add_parser("version", help="Show version")

    # benchmark
    bm = sub.add_parser("benchmark", help="Run benchmark suites and compare reports")
    bm.add_argument("action", choices=["run", "list", "compare", "history"])
    bm.add_argument("--suite", default="", help="Benchmark suite name")
    bm.add_argument("--report-id", default="", help="Report ID for compare/history")
    bm.add_argument("--report-a", default="", help="First report ID for compare")
    bm.add_argument("--report-b", default="", help="Second report ID for compare")
    bm.add_argument("--limit", type=int, default=10, help="History limit")

    # loadbalancer
    lb = sub.add_parser("loadbalancer", help="Cluster load balancing and scheduling")
    lb.add_argument("action", choices=["overview", "rebalance", "predict", "select"])
    lb.add_argument(
        "--strategy",
        default="least_loaded",
        choices=["round_robin", "least_loaded", "weighted_capacity", "affinity_based"],
        help="Strategy",
    )
    lb.add_argument("--session-id", default="", help="Session ID for select")
    lb.add_argument("--duration-hours", type=float, default=1.0, help="Hours to predict")

    # offline
    of = sub.add_parser("offline", help="Offline deployment management")
    of.add_argument("action", choices=["detect", "capabilities", "prepare", "validate", "restore"])
    of.add_argument("--mode", default="", choices=["full_offline", "semi_offline", "online"], help="Target mode")
    of.add_argument("--package-dir", default="", help="Package directory")
    of.add_argument("--name", default="offline-package", help="Package name")
    of.add_argument("--model-ids", default="", help="Comma-separated model IDs")
    of.add_argument("--plugin-ids", default="", help="Comma-separated plugin IDs")

    # trace
    tr = sub.add_parser("trace", help="End-to-end traceability tracking")
    tr.add_argument("action", choices=["create", "link", "forward", "backward", "report"])
    tr.add_argument("--artifact-type", default="", help="Artifact type")
    tr.add_argument("--artifact-id", default="", help="Artifact ID")
    tr.add_argument("--name", default="", help="Node name")
    tr.add_argument("--source-id", default="", help="Source node ID")
    tr.add_argument("--target-id", default="", help="Target node ID")
    tr.add_argument("--relationship", default="", help="Relationship type")
    tr.add_argument("--max-depth", type=int, default=10, help="Max trace depth")

    # agent-comm
    ac = sub.add_parser("agent-comm", help="Agent cross-machine communication")
    ac.add_argument("action", choices=["create", "submit", "conflict", "resolve", "complete", "list", "status"])
    ac.add_argument("--description", default="", help="Collaboration task description")
    ac.add_argument("--agents", default="", help="Comma-separated agent IDs")
    ac.add_argument("--collab-id", default="", help="Collaboration ID")
    ac.add_argument("--agent-id", default="", help="Agent ID")
    ac.add_argument("--resolution", default="", help="Conflict resolution description")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    _configure_logging(args)

    _global_flags.json_output = args.json_output
    _global_flags.quiet = args.quiet

    dispatch = {
        "version": _cmd_version,
        "analyze": lambda: asyncio.run(_cmd_analyze(args)),
        "transpile": lambda: asyncio.run(_cmd_transpile(args)),
        "refactor": lambda: asyncio.run(_cmd_refactor(args)),
        "test-gen": lambda: asyncio.run(_cmd_test_gen(args)),
        "security": lambda: asyncio.run(_cmd_security(args)),
        "session": lambda: _cmd_session(args),
        "snapshot": lambda: _cmd_snapshot(args),
        "workflow": lambda: asyncio.run(_cmd_workflow(args)),
        "memory": lambda: asyncio.run(_cmd_memory(args)),
        "sandbox": lambda: _cmd_sandbox(args),
        "decompose": lambda: asyncio.run(_cmd_decompose(args)),
        "doc-gen": lambda: asyncio.run(_cmd_doc_gen(args)),
        "audit": lambda: asyncio.run(_cmd_audit(args)),
        "cluster": lambda: asyncio.run(_cmd_cluster(args)),
        "plugin": lambda: _cmd_plugin(args),
        "benchmark": lambda: _cmd_benchmark(args),
        "loadbalancer": lambda: _cmd_loadbalancer(args),
        "offline": lambda: _cmd_offline(args),
        "trace": lambda: _cmd_trace(args),
        "agent-comm": lambda: _cmd_agent_comm(args),
    }
    try:
        dispatch[args.command]()
    except Exception as exc:
        if args.json_output:
            json.dump({"status": "failed", "error": str(exc)}, sys.stdout)
            print()
        else:
            logger.error("Command failed: %s", exc)
        sys.exit(1)


def _configure_logging(args):
    if args.quiet:
        level = logging.ERROR
    elif args.verbose:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _cmd_version():
    if _global_flags.json_output:
        json.dump({"version": VERSION, "base": "fusion-mlx"}, sys.stdout)
        print()
    else:
        print(f"Fusion-Code-Modelization v{VERSION}")
        print("Base: fusion-mlx")


async def _cmd_analyze(args):
    from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer

    analyzer = DependencyAnalyzer(mlx_url=args.mlx_url)
    print(f"Analyzing {args.path}...")
    graph = analyzer.scan_directory(args.path)
    debt = analyzer.estimate_tech_debt(graph)
    report = analyzer.generate_report(graph, debt)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to {args.output}")
    else:
        print(report)


async def _cmd_transpile(args):
    from fusion_code_modelization.migration.transpiler import CodeTranspiler

    code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    transpiler = CodeTranspiler(mlx_url=args.mlx_url)
    print(f"Transpiling {args.file} from {args.source_lang} to {args.target_lang}...")
    if getattr(args, "stream", False):
        result = None
        async for chunk in transpiler.transpile_stream(code, args.source_lang, args.target_lang):
            if chunk["type"] == "token":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "done":
                result = chunk["result"]
        print()
        if result and result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["code"], encoding="utf-8")
                print(f"Transpiled code saved to {args.output}")
        else:
            print(f"Error: {result.get('error', 'Unknown') if result else 'No result'}")
    else:
        result = await transpiler.transpile(code, args.source_lang, args.target_lang)
        if result["status"] == "completed":
            output = result["code"]
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8")
                print(f"Transpiled code saved to {args.output}")
            else:
                print(output)
        else:
            print(f"Error: {result.get('error', 'Unknown')}")


async def _cmd_refactor(args):
    from fusion_code_modelization.refactor.refactorer import IncrementalRefactorer

    code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    refactorer = IncrementalRefactorer(mlx_url=args.mlx_url)
    lang = Path(args.file).suffix[1:] or "unknown"
    print(f"Refactoring {args.file}...")
    if getattr(args, "stream", False):
        result = None
        async for chunk in refactorer.refactor_stream(code, lang, args.instructions):
            if chunk["type"] == "token":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "done":
                result = chunk["result"]
        print()
        if result and result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["refactored"], encoding="utf-8")
                print(f"Refactored code saved to {args.output}")
        else:
            print(f"Error: {result.get('error', 'Unknown') if result else 'No result'}")
    else:
        result = await refactorer.refactor(code, lang, args.instructions)
        if result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["refactored"], encoding="utf-8")
                print(f"Refactored code saved to {args.output}")
            else:
                print(result["refactored"])
        else:
            print(f"Error: {result.get('error', 'Unknown')}")


async def _cmd_test_gen(args):
    from fusion_code_modelization.test_gen.generator import UnitTestGenerator

    code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    lang = args.language or Path(args.file).suffix[1:] or "unknown"
    generator = UnitTestGenerator(mlx_url=args.mlx_url)
    print(f"Generating tests for {args.file}...")
    if getattr(args, "stream", False):
        result = None
        async for chunk in generator.generate_unit_tests_stream(code, lang):
            if chunk["type"] == "token":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "done":
                result = chunk["result"]
        print()
        if result and result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["tests"], encoding="utf-8")
                print(f"Tests saved to {args.output}")
        else:
            print(f"Error: {result.get('error', 'Unknown') if result else 'No result'}")
    else:
        result = await generator.generate_unit_tests(code, lang)
        if result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["tests"], encoding="utf-8")
                print(f"Tests saved to {args.output}")
            else:
                print(result["tests"])
        else:
            print(f"Error: {result.get('error', 'Unknown')}")


async def _cmd_security(args):
    from fusion_code_modelization.security.scanner import SecurityScanner

    code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    lang = args.language or Path(args.file).suffix[1:] or "unknown"
    scanner = SecurityScanner(mlx_url=args.mlx_url)
    print(f"Scanning {args.file} for vulnerabilities...")
    if getattr(args, "stream", False):
        result = None
        async for chunk in scanner.scan_stream(code, lang):
            if chunk["type"] == "token":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "findings":
                phase = chunk.get("phase", "unknown")
                for f in chunk["findings"]:
                    print(f"  [{phase}] [{f['severity']}] Line {f['line']}: {f['description']}")
            elif chunk["type"] == "done":
                result = chunk["result"]
        if result:
            print(f"\nTotal: {result['total_findings']} finding(s) [{result['scan_mode']}]")
            if args.output:
                Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    else:
        result = await scanner.scan(code, lang)
        print(f"Found {result['total_findings']} issue(s):")
        for f in result.get("findings", []):
            print(f"  [{f['severity']}] Line {f['line']}: {f['description']}")
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")


def _cmd_session(args):
    from fusion_code_modelization.session import SessionEngine

    engine = SessionEngine()
    if args.action == "create":
        session = engine.create_session(name=args.name or "unnamed")
        print(f"Created session: {session.id} ({session.name})")
    elif args.action == "list":
        for s in engine.list_sessions():
            print(f"  {s.id}  {s.name:20s}  {s.state.value}")
    elif args.action == "start":
        engine.start(args.session_id)
        print(f"Started session {args.session_id}")
    elif args.action == "pause":
        engine.pause(args.session_id)
        print(f"Paused session {args.session_id}")
    elif args.action == "resume":
        engine.resume(args.session_id)
        print(f"Resumed session {args.session_id}")
    elif args.action == "complete":
        engine.complete(args.session_id)
        print(f"Completed session {args.session_id}")
    elif args.action == "delete":
        engine.delete(args.session_id)
        print(f"Deleted session {args.session_id}")


def _cmd_snapshot(args):
    from fusion_code_modelization.snapshot import SnapshotManager

    mgr = SnapshotManager(project_dir=args.project_dir)
    if args.action == "create":
        snap = mgr.create_snapshot(label=args.label)
        print(f"Created snapshot: {snap.id}")
    elif args.action == "list":
        for s in mgr.list_snapshots():
            print(f"  {s['id']}  {s['created_at']}  {s.get('label', '')}")
    elif args.action == "restore":
        ok = mgr.restore_snapshot(args.snapshot_id)
        print(f"Restore {'succeeded' if ok else 'failed'}")
    elif args.action == "rewind":
        snap = mgr.rewind(steps=args.steps)
        print(f"Rewound to: {snap.id}" if snap else "No snapshot to rewind to")
    elif args.action == "delete":
        ok = mgr.delete_snapshot(args.snapshot_id)
        print(f"Delete {'succeeded' if ok else 'failed'}")


async def _cmd_workflow(args):
    from fusion_code_modelization.workflow import WORKFLOW_TEMPLATES, TaskDecomposer, WorkflowExecutor

    if args.action == "decompose":
        decomposer = TaskDecomposer()
        plan = await decomposer.decompose(args.description, template=args.template)
        print(f"Plan: {plan.name} ({len(plan.tasks)} tasks)")
        for t in plan.tasks:
            deps = ", ".join(t.dependencies) if t.dependencies else "none"
            print(f"  [{t.id}] {t.name} (deps: {deps})")
    elif args.action == "run":
        template = WORKFLOW_TEMPLATES.get(args.template, WORKFLOW_TEMPLATES["generic"])
        plan = template(args.description)
        executor = WorkflowExecutor(max_parallel=args.max_parallel)
        result = await executor.run_workflow(plan)
        print(f"Workflow: {result.success_count} succeeded, {result.failure_count} failed")


async def _cmd_memory(args):
    from fusion_code_modelization.memory import MemoryTierManager

    mgr = MemoryTierManager()
    if args.action == "init":
        mgr.init_project(args.project_dir)
        print(f"Initialized project memory in {args.project_dir}")
    elif args.action == "list":
        entries = mgr.list_directory_memories(args.project_dir)
        for e in entries:
            print(f"  {e.tier.value}: {e.path}")
    elif args.action == "load":
        context = mgr.load_all(args.project_dir)
        print(f"Loaded {len(context)} memory entries")
        for e in context:
            print(f"  [{e.tier.value}] {e.path}: {len(e.content)} chars")
    elif args.action == "query":
        from fusion_code_modelization.memory import MemoryContext

        ctx = MemoryContext(tier_manager=mgr)
        result = await ctx.query(args.query, project_dir=args.project_dir)
        print(result)


def _cmd_sandbox(args):
    from fusion_code_modelization.sandbox import SandboxGuard, SandboxPolicy

    policy = SandboxPolicy(mode=args.mode)
    guard = SandboxGuard(policy=policy)
    if args.action == "check":
        allowed, reason = guard.check_path(args.path)
        print(f"Path {'allowed' if allowed else 'denied'}: {reason}")
    elif args.action == "audit":
        entries = guard.get_audit_log()
        print(f"Audit log: {len(entries)} entries")
        for e in entries[-20:]:
            print(f"  {e}")


async def _cmd_decompose(args):
    from fusion_code_modelization.analyzer.dependency import DependencyAnalyzer
    from fusion_code_modelization.decompose import BoundaryDetector

    detector = BoundaryDetector(mlx_url=args.mlx_url)
    analyzer = DependencyAnalyzer()
    graph = analyzer.scan_directory(args.path)
    graph_dict = {"nodes": graph.nodes, "edges": graph.edges}
    if args.method == "static":
        suggestions = detector.detect_boundaries_static(graph_dict)
    else:
        suggestions = await detector.detect_boundaries_llm(graph_dict)
    print(f"Found {len(suggestions)} boundary suggestions:")
    for s in suggestions:
        print(f"  [{s.name}] modules={s.modules} score={s.coupling_score}")
    if args.output:
        data = [s.to_dict() for s in suggestions]
        Path(args.output).write_text(json.dumps(data, indent=2), encoding="utf-8")


async def _cmd_doc_gen(args):
    from fusion_code_modelization.doc_gen import DocumentationGenerator

    gen = DocumentationGenerator(mlx_url=args.mlx_url)
    code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    lang = args.language or Path(args.file).suffix[1:] or "unknown"
    if getattr(args, "stream", False):
        result = None
        async for chunk in gen.generate_docs_stream(code, lang, doc_type=args.doc_type):
            if chunk["type"] == "token":
                print(chunk["content"], end="", flush=True)
            elif chunk["type"] == "done":
                result = chunk["result"]
        print()
        if result and result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["documentation"], encoding="utf-8")
                print(f"Docs saved to {args.output}")
        else:
            print(f"Error: {result.get('error', 'Unknown') if result else 'No result'}")
    else:
        if args.doc_type == "api":
            result = await gen.generate_api_docs(code, lang)
        else:
            result = await gen.generate_docs(code, lang, doc_type=args.doc_type)
        if result["status"] == "completed":
            if args.output:
                Path(args.output).write_text(result["documentation"], encoding="utf-8")
                print(f"Docs saved to {args.output}")
            else:
                print(result["documentation"])
        else:
            print(f"Error: {result.get('error', 'Unknown')}")


async def _cmd_audit(args):
    from fusion_code_modelization.audit import AuditAction, AuditFilter, AuditLogger, AuditSeverity

    logger_inst = AuditLogger()
    if args.action == "log":
        action = AuditAction(args.action_type) if args.action_type else AuditAction.CUSTOM
        severity = AuditSeverity(args.severity) if args.severity else AuditSeverity.INFO
        entry = logger_inst.log_operation(action=action, target=args.output or "cli", severity=severity)
        print(f"Logged: {entry.entry_id}")
    elif args.action == "search":
        filters = AuditFilter(
            actor=args.actor,
            severity=AuditSeverity(args.severity) if args.severity else None,
            start_time=args.start_time,
            end_time=args.end_time,
        )
        results = logger_inst.search(filters=filters)
        print(f"Found {len(results)} entries:")
        for e in results:
            print(f"  [{e.severity.value}] {e.timestamp} {e.action.value} {e.target}")
    elif args.action == "export":
        filters = AuditFilter(
            actor=args.actor,
            severity=AuditSeverity(args.severity) if args.severity else None,
            start_time=args.start_time,
            end_time=args.end_time,
        )
        report = logger_inst.export_report(fmt=args.format, filters=filters)
        if args.output:
            text = json.dumps(report, indent=2) if isinstance(report, dict) else str(report)
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"Report saved to {args.output}")
        else:
            print(json.dumps(report, indent=2) if isinstance(report, dict) else report)
    elif args.action == "stats":
        stats = logger_inst.get_statistics(start_time=args.start_time, end_time=args.end_time)
        print(json.dumps(stats, indent=2))
    elif args.action == "cleanup":
        removed = logger_inst.cleanup(max_age_days=args.max_age_days)
        print(f"Cleaned up {removed} entries older than {args.max_age_days} days")


async def _cmd_cluster(args):
    from fusion_code_modelization.cluster import ClusterScheduler, NodeInfo

    scheduler = ClusterScheduler()
    if args.action == "discover":
        nodes = scheduler.discover_nodes()
        print(f"Discovered {len(nodes)} node(s):")
        for n in nodes:
            print(f"  {n.node_id} {n.host}:{n.port} [{n.status.value}] load={n.load_score:.1f}%")
    elif args.action == "register":
        node = NodeInfo(node_id=args.node_id, host=args.host, port=args.port)
        scheduler.register_node(node)
        print(f"Registered node: {node.node_id} ({node.host}:{node.port})")
    elif args.action == "status":
        nodes = await scheduler.get_node_status()
        for n in nodes:
            print(
                f"  {n.node_id} {n.host}:{n.port} [{n.status.value}] cpu={n.cpu_percent:.0f}% mem={n.memory_percent:.0f}%"
            )
    elif args.action == "dispatch":
        if not args.session_id or not args.node_id:
            print("Error: --session-id and --node-id required for dispatch")
            return
        task = await scheduler.dispatch_task(args.session_id, args.node_id, args.description)
        print(f"Dispatched: {task.task_id} -> {task.target_node} [{task.status.value}]")
    elif args.action == "schedule":
        if not args.session_id:
            print("Error: --session-id required for schedule")
            return
        task = await scheduler.auto_schedule(args.session_id, args.description, require_gpu=args.require_gpu)
        print(f"Scheduled: {task.task_id} -> {task.target_node} [{task.status.value}]")
    elif args.action == "migrate":
        if not args.session_id or not args.from_node or not args.to_node:
            print("Error: --session-id, --from-node, --to-node required for migrate")
            return
        task = await scheduler.migrate_session(args.session_id, args.from_node, args.to_node)
        print(f"Migrated: {task.task_id} {args.from_node} -> {args.to_node} [{task.status.value}]")
    elif args.action == "tasks":
        tasks = scheduler.list_tasks()
        print(f"Total tasks: {len(tasks)}")
        for t in tasks:
            print(f"  {t.task_id} {t.session_id} -> {t.target_node} [{t.status.value}]")


def _cmd_plugin(args):
    from fusion_code_modelization.plugin import PluginCategory, PluginManager, PluginRegistry

    registry = PluginRegistry()
    manager = PluginManager(registry=registry)
    if args.action == "list":
        cat = PluginCategory(args.category) if args.category else None
        plugins = manager.registry.list_plugins(category=cat)
        print(f"Plugins ({len(plugins)}):")
        for p in plugins:
            print(f"  {p.plugin_id} {p.name} v{p.version} [{p.status.value}]")
    elif args.action == "search":
        results = manager.registry.search_plugins(args.query)
        print(f"Found {len(results)} plugin(s):")
        for p in results:
            print(f"  {p.plugin_id} {p.name} - {p.description}")
    elif args.action == "install":
        result = manager.registry.install(args.plugin_id)
        if result:
            print(f"Installed: {result.plugin_id} v{result.version}")
        else:
            print(f"Plugin not found: {args.plugin_id}")
    elif args.action == "load":
        ok = manager.load(args.plugin_id)
        print(f"Load {'succeeded' if ok else 'failed'}: {args.plugin_id}")
    elif args.action == "unload":
        ok = manager.unload(args.plugin_id)
        print(f"Unload {'succeeded' if ok else 'failed'}: {args.plugin_id}")
    elif args.action == "execute":
        if not args.plugin_id or not args.action_name:
            print("Error: --plugin-id and --action-name required for execute")
            return
        result = manager.execute(args.plugin_id, args.action_name)
        print(json.dumps(result, indent=2))
    elif args.action == "status":
        status = manager.get_plugin_status()
        print(json.dumps(status, indent=2))


def _cmd_benchmark(args):
    from fusion_code_modelization.benchmark import BenchmarkRunner

    runner = BenchmarkRunner()
    if args.action == "list":
        for name in runner.list_suites():
            suite = runner.get_suite(name)
            if suite:
                print(f"  {name}: {len(suite.items)} items [{suite.category.value}]")
    elif args.action == "run":
        if not args.suite:
            print("Error: --suite required for run")
            return
        report = runner.run_suite(args.suite, score_fn={})
        print(f"Report: {report.report_id}")
        print(f"  Passed: {report.passed_count}, Failed: {report.failed_count}, Skipped: {report.skipped_count}")
        print(f"  Average score: {report.average_score:.1f}%")
        for r in report.results:
            print(f"    [{r.status.value}] {r.item_id}: {r.score:.1f}/{r.target_score:.1f}")
    elif args.action == "compare":
        if not args.report_a or not args.report_b:
            print("Error: --report-a and --report-b required for compare")
            return
        comparison = runner.compare_reports(args.report_a, args.report_b)
        print(f"Regressions: {len(comparison['regressions'])}")
        print(f"Improvements: {len(comparison['improvements'])}")
        print(f"Unchanged: {len(comparison['unchanged'])}")
    elif args.action == "history":
        if not args.suite:
            print("Error: --suite required for history")
            return
        trends = runner.get_historical_trends(args.suite, limit=args.limit)
        for t in trends:
            print(f"  {t['report_id']}: avg={t['average_score']:.1f}% passed={t['passed_count']}")


def _cmd_loadbalancer(args):
    from fusion_code_modelization.loadbalancer import BalancerConfig, LoadBalancer, LoadBalanceStrategy

    config = BalancerConfig(strategy=LoadBalanceStrategy(args.strategy))
    lb = LoadBalancer(config=config)
    if args.action == "overview":
        overview = lb.get_cluster_overview()
        print(json.dumps(overview, indent=2))
    elif args.action == "rebalance":
        suggestions = lb.rebalance()
        if suggestions:
            for s in suggestions:
                print(f"  Move {s['tasks_to_move']} tasks from {s['overloaded_node']} to {s['underloaded_node']}")
        else:
            print("No rebalance needed")
    elif args.action == "predict":
        prediction = lb.predict_capacity(duration_hours=args.duration_hours)
        print(json.dumps(prediction, indent=2))
    elif args.action == "select":
        if not args.session_id:
            print("Error: --session-id required for select")
            return
        decision = lb.select_node(session_id=args.session_id)
        if decision:
            print(f"Selected: {decision.selected_node} via {decision.strategy.value}")
            print(f"  Reason: {decision.reason}")
        else:
            print("No node available")


def _cmd_offline(args):
    from fusion_code_modelization.offline import OfflineManager

    mgr = OfflineManager()
    if args.action == "detect":
        mode = mgr.detect_mode()
        print(f"Detected mode: {mode.value}")
    elif args.action == "capabilities":
        caps = mgr.get_available_capabilities()
        print(f"Available capabilities ({len(caps)}):")
        for c in caps:
            print(f"  {c.value}")
    elif args.action == "prepare":
        from fusion_code_modelization.offline import OfflineMode

        mode = OfflineMode(args.mode) if args.mode else None
        model_ids = args.model_ids.split(",") if args.model_ids else []
        plugin_ids = args.plugin_ids.split(",") if args.plugin_ids else []
        package = mgr.prepare_offline_package(
            output_dir=args.package_dir or ".fusion/offline_packages",
            name=args.name,
            model_ids=model_ids,
            plugin_ids=plugin_ids,
        )
        print(f"Package prepared: {package.package_id}")
        print(f"  Mode: {package.mode.value}, Size: {package.size_mb:.1f} MB")
    elif args.action == "validate":
        if not args.package_dir:
            print("Error: --package-dir required for validate")
            return
        valid = mgr.validate_package(args.package_dir)
        print(f"Package valid: {valid}")
    elif args.action == "restore":
        if not args.package_dir:
            print("Error: --package-dir required for restore")
            return
        pkg = mgr.restore_from_package(args.package_dir)
        if pkg:
            print(f"Restored: {pkg.package_id} ({pkg.mode.value})")
        else:
            print("Restore failed")


def _cmd_trace(args):
    from fusion_code_modelization.trace import TraceTracker

    tracker = TraceTracker()
    if args.action == "create":
        if not args.artifact_type or not args.artifact_id:
            print("Error: --artifact-type and --artifact-id required")
            return
        node = tracker.create_node(
            artifact_type=args.artifact_type,
            artifact_id=args.artifact_id,
            name=args.name or args.artifact_id,
        )
        print(f"Created node: {node.node_id} ({node.artifact_type.value})")
    elif args.action == "link":
        if not args.source_id or not args.target_id or not args.relationship:
            print("Error: --source-id, --target-id, --relationship required")
            return
        edge = tracker.link_nodes(args.source_id, args.target_id, args.relationship)
        if edge:
            print(f"Linked: {args.source_id} -> {args.target_id} via {args.relationship}")
        else:
            print("Link failed — check node IDs")
    elif args.action == "forward":
        if not args.artifact_id:
            print("Error: --artifact-id required")
            return
        chain = tracker.trace_forward(args.artifact_id, max_depth=args.max_depth)
        if chain:
            print(f"Forward trace: {len(chain.nodes)} nodes, {len(chain.edges)} edges, depth={chain.depth}")
            for n in chain.nodes:
                print(f"  {n.node_id} [{n.artifact_type.value}] {n.name}")
        else:
            print("No forward trace found")
    elif args.action == "backward":
        if not args.artifact_id:
            print("Error: --artifact-id required")
            return
        chain = tracker.trace_backward(args.artifact_id, max_depth=args.max_depth)
        if chain:
            print(f"Backward trace: {len(chain.nodes)} nodes, {len(chain.edges)} edges, depth={chain.depth}")
            for n in chain.nodes:
                print(f"  {n.node_id} [{n.artifact_type.value}] {n.name}")
        else:
            print("No backward trace found")
    elif args.action == "report":
        report = tracker.generate_report()
        print(report.to_markdown())


def _cmd_agent_comm(args):
    from fusion_code_modelization.agent_comm import CollaborationCoordinator

    coordinator = CollaborationCoordinator()
    if args.action == "create":
        if not args.description or not args.agents:
            print("Error: --description and --agents required")
            return
        agent_ids = [a.strip() for a in args.agents.split(",") if a.strip()]
        task = coordinator.create_collaboration(args.description, agent_ids)
        print(f"Created collaboration: {task.collaboration_id}")
        print(f"  Channel: {task.channel_name}, Agents: {len(task.agent_ids)}")
    elif args.action == "submit":
        if not args.collab_id or not args.agent_id:
            print("Error: --collab-id and --agent-id required")
            return
        ok = coordinator.submit_result(args.collab_id, args.agent_id, {"submitted_via": "cli"})
        print(f"Submit {'succeeded' if ok else 'failed'}")
    elif args.action == "conflict":
        if not args.collab_id or not args.agent_id:
            print("Error: --collab-id and --agent-id required")
            return
        ok = coordinator.report_conflict(args.collab_id, args.agent_id, {"reported_via": "cli"})
        print(f"Conflict reported: {'succeeded' if ok else 'failed'}")
    elif args.action == "resolve":
        if not args.collab_id:
            print("Error: --collab-id required")
            return
        ok = coordinator.resolve_conflict(args.collab_id, {"resolution": args.resolution or "resolved"})
        print(f"Conflict resolved: {'succeeded' if ok else 'failed'}")
    elif args.action == "complete":
        if not args.collab_id:
            print("Error: --collab-id required")
            return
        ok = coordinator.complete_collaboration(args.collab_id)
        print(f"Completed: {'succeeded' if ok else 'failed'}")
    elif args.action == "list":
        tasks = coordinator.list_tasks()
        print(f"Collaborations ({len(tasks)}):")
        for t in tasks:
            print(f"  {t.collaboration_id} [{t.status.value}] {t.task_description[:50]}")
    elif args.action == "status":
        if not args.collab_id:
            print("Error: --collab-id required")
            return
        task = coordinator.get_task(args.collab_id)
        if task:
            print(f"  ID: {task.collaboration_id}")
            print(f"  Status: {task.status.value}")
            print(f"  Channel: {task.channel_name}")
            print(f"  Agents: {', '.join(task.agent_ids)}")
            print(f"  Results: {len(task.results)} submitted")
        else:
            print(f"Collaboration {args.collab_id} not found")
