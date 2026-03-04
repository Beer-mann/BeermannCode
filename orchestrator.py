#!/usr/bin/env python3
"""
BeermannCode Primary Orchestrator (stable wrapper)

Primary engine entrypoint for autonomous coding runs.
This wrapper keeps the project-local orchestrator as the canonical binary
and delegates execution to the global runner script.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

GLOBAL_RUNNER = Path("/home/shares/beermann/scripts/coding-orchestrator.sh")


def build_cmd(args: argparse.Namespace) -> list[str]:
    cmd = ["bash", str(GLOBAL_RUNNER)]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.project:
        cmd.extend(["--project", args.project])
    if args.tier:
        cmd.extend(["--tier", str(args.tier)])
    if args.with_docs:
        cmd.append("--with-docs")
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="BeermannCode Primary Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Run without applying changes")
    parser.add_argument("--project", help="Run for a single project")
    parser.add_argument("--tier", type=int, default=3, help="Max routing tier (1-4)")
    parser.add_argument("--with-docs", action="store_true", help="Include docs/tests/readme tasks")
    parser.add_argument("--list-models", action="store_true", help="Show available Ollama models")
    args = parser.parse_args()

    if args.list_models:
        return subprocess.call(
            "curl -s http://192.168.0.213:11434/api/tags | python3 -c 'import json,sys; d=json.load(sys.stdin); [print(m.get(""name"")) for m in d.get(""models"",[])]'",
            shell=True,
        )

    if not GLOBAL_RUNNER.exists():
        print(f"[ERROR] Runner not found: {GLOBAL_RUNNER}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env.setdefault("DYNAMIC_CHAIN", "true")
    env.setdefault("CHAIN_COOLDOWN_SEC", "45")
    env.setdefault("PROJECT_SCAN_LIMIT", "3")

    cmd = build_cmd(args)
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
