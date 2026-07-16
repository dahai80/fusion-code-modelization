"""Fusion-Code-Modelization CLI."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


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

    # version
    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "version":
        print("Fusion-Code-Modelization v0.1.0")
        print("Base: fusion-mlx")

    elif args.command == "analyze":
        asyncio.run(_cmd_analyze(args))

    elif args.command == "transpile":
        asyncio.run(_cmd_transpile(args))

    elif args.command == "refactor":
        asyncio.run(_cmd_refactor(args))

    elif args.command == "test-gen":
        asyncio.run(_cmd_test_gen(args))

    elif args.command == "security":
        asyncio.run(_cmd_security(args))


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
    from fusion_code_modelization.test_gen.generator import TestGenerator
    code = Path(args.file).read_text(encoding="utf-8", errors="replace")
    lang = args.language or Path(args.file).suffix[1:] or "unknown"
    generator = TestGenerator(mlx_url=args.mlx_url)
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
        import json
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")