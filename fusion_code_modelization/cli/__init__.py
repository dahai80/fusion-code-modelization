"""Fusion-Code-Modelization CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

VERSION = "0.3.0"


def main():
    parser = argparse.ArgumentParser(description="Fusion-Code-Modelization — Legacy code modernization")
    parser.add_argument("--mlx-url", default="http://localhost:11434/v1", help="fusion-mlx URL")

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

    # refactor
    r = sub.add_parser("refactor", help="Refactor code incrementally")
    r.add_argument("file", help="File to refactor")
    r.add_argument("--instructions", default="", help="Refactoring instructions")
    r.add_argument("--output", default="", help="Output file path")

    # test-gen
    tg = sub.add_parser("test-gen", help="Generate unit tests")
    tg.add_argument("file", help="Source file")
    tg.add_argument("--language", default="", help="Programming language")
    tg.add_argument("--output", default="", help="Output file path")

    # security
    s = sub.add_parser("security", help="Scan for security vulnerabilities")
    s.add_argument("file", help="File to scan")
    s.add_argument("--language", default="", help="Programming language")
    s.add_argument("--output", default="", help="Output file path")

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

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

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
    }
    dispatch[args.command]()


def _cmd_version():
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
    print(f"Refactoring {args.file}...")
    result = await refactorer.refactor(code, Path(args.file).suffix[1:] or "unknown", args.instructions)
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
