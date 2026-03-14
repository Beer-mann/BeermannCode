#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator v4.0

Multi-Project Orchestrator — nutzt agents.json Config.
Scannt ALLE Projekte, findet echte Tasks, fixt sie mit verfügbaren CLIs.

CLIs (Fallback-Kette):
  1. Claude CLI (claude -p) — bestes Ergebnis
  2. Copilot CLI (copilot -p) — kostenlos via GitHub
  3. Codex CLI — schnell, gut für Code-Gen
  4. Aider + Ollama — kostenlos, wenn Ollama online
  5. Aider + OpenAI — Fallback

Features:
  - Multi-project mit Priority (TradingBot, VoiceOpsAI first)
  - Echte Task-Discovery (TODO/FIXME, bare except, missing tests, etc.)
  - Lockfile, Skip-Liste, Timeout
  - Auto-commit + Auto-push
  - WhatsApp summary via whatsapp_notifier.py
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ============================================================================
# CONFIG
# ============================================================================

WORKSPACE = Path("/home/shares/beermann")
PROJECTS_DIR = WORKSPACE / "PROJECTS"
BEERMANNCODE_DIR = PROJECTS_DIR / "BeermannCode"
CONFIG_FILE = BEERMANNCODE_DIR / "agents.json"
LOG_DIR = WORKSPACE / "logs"
LOG_FILE = LOG_DIR / "orchestrator-v4.log"
TASKS_DIR = WORKSPACE / "tasks"
DONE_FILE = TASKS_DIR / "done.jsonl"
SKIP_FILE = TASKS_DIR / "skip.jsonl"
LOCKFILE = Path("/tmp/beermanncode-v4.lock")

# Defaults
MAX_TASKS = int(os.getenv("MAX_TASKS", "5"))
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "300"))  # 5 min per task
AUTO_PUSH = os.getenv("AUTO_PUSH", "true").lower() == "true"
AUTO_COMMIT = os.getenv("AUTO_COMMIT", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

OLLAMA_URL = os.getenv("OLLAMA_API_BASE", "http://192.168.0.213:11434")

# Priority projects (first in queue)
PRIORITY_PROJECTS = ["TradingBot", "VoiceOpsAI", "BCN"]

# Dirs to exclude from scanning
EXCLUDE_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build",
    "flask", "werkzeug", "jinja2", "itsdangerous", "markupsafe", "blinker",
    "click", "flask_cors", ".aider.tags.cache.v4", "static", "templates",
}

# File extensions to scan
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}

# ============================================================================
# LOGGING
# ============================================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


# ============================================================================
# LOCKFILE
# ============================================================================

def acquire_lock() -> bool:
    if LOCKFILE.exists():
        try:
            pid = int(LOCKFILE.read_text().strip())
            os.kill(pid, 0)  # Check if process alive
            return False  # Still running
        except (ValueError, ProcessLookupError, PermissionError):
            pass  # Stale lock
    LOCKFILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    LOCKFILE.unlink(missing_ok=True)


# ============================================================================
# SKIP LIST
# ============================================================================

def is_skipped(project: str, filepath: str) -> bool:
    if not SKIP_FILE.exists():
        return False
    try:
        cutoff = datetime.now() - timedelta(hours=24)
        for line in SKIP_FILE.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("project") == project and entry.get("file") == filepath:
                ts = datetime.fromisoformat(entry.get("ts", "2000-01-01"))
                if ts > cutoff:
                    return True
    except Exception:
        pass
    return False


def mark_skipped(project: str, filepath: str, reason: str) -> None:
    entry = {"ts": datetime.now().isoformat(), "project": project, "file": filepath, "reason": reason}
    with SKIP_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def mark_done(project: str, filepath: str, task_type: str) -> None:
    entry = {"ts": datetime.now().isoformat(), "project": project, "file": filepath, "type": task_type, "status": "done"}
    with DONE_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ============================================================================
# CLI DETECTION
# ============================================================================

def check_cli(name: str) -> bool:
    try:
        subprocess.run(["which", name], capture_output=True, timeout=5)
        return subprocess.run(["which", name], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


def check_ollama() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception:
        return False


AVAILABLE_CLIS: dict[str, bool] = {}


def detect_clis() -> dict[str, bool]:
    global AVAILABLE_CLIS
    AVAILABLE_CLIS = {
        "claude": check_cli("claude"),
        "copilot": check_cli("copilot"),
        "codex": check_cli("codex"),
        "aider": check_cli("aider"),
        "ollama": check_ollama(),
    }
    log(f"🔧 CLIs: {', '.join(f'{k} ✅' if v else f'{k} ❌' for k, v in AVAILABLE_CLIS.items())}")
    return AVAILABLE_CLIS


# ============================================================================
# CLI RUNNERS (Fallback Chain)
# ============================================================================

def run_with_claude(task: str, project_dir: Path, files: list[str] | None = None) -> tuple[bool, str]:
    """Run task with Claude Code CLI."""
    try:
        cmd = ["claude", "-p", "--output-format", "text", task]
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
        )
        return result.returncode == 0, (result.stdout or result.stderr)[-300:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def run_with_copilot(task: str, project_dir: Path, files: list[str] | None = None) -> tuple[bool, str]:
    """Run task with GitHub Copilot CLI (free via GitHub subscription)."""
    try:
        cmd = ["copilot", "-p", "--output-format", "text", task]
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
        )
        return result.returncode == 0, (result.stdout or result.stderr)[-300:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def run_with_codex(task: str, project_dir: Path, files: list[str] | None = None) -> tuple[bool, str]:
    """Run task with Codex CLI."""
    try:
        cmd = ["codex", "--approval-mode", "full-auto", "-q", task]
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=TASK_TIMEOUT,
        )
        return result.returncode == 0, (result.stdout or result.stderr)[-300:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def run_with_aider(task: str, project_dir: Path, files: list[str] | None = None) -> tuple[bool, str]:
    """Run task with Aider (Ollama or OpenAI fallback)."""
    try:
        env = os.environ.copy()

        if AVAILABLE_CLIS.get("ollama"):
            env["OLLAMA_API_BASE"] = OLLAMA_URL
            model_args = [
                "--model", "ollama/qwen2.5-coder:7b",
                "--env-file", "/home/beermann/.aider.env",
            ]
        elif os.getenv("OPENAI_API_KEY"):
            model_args = ["--model", "gpt-4o-mini"]
        else:
            return False, "no model available for aider"

        cmd = [
            "aider",
            *model_args,
            "--yes-always",
            "--auto-commits",
            "--no-show-model-warnings",
            "--no-pretty",
            "--message", task,
        ]
        if files:
            cmd.extend(files)

        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            env=env,
            timeout=TASK_TIMEOUT,
        )
        return result.returncode == 0, (result.stdout or result.stderr)[-300:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def run_task_with_fallback(task: str, project_dir: Path, files: list[str] | None = None) -> tuple[bool, str]:
    """Try CLIs in order: claude → codex → aider."""
    runners = []
    if AVAILABLE_CLIS.get("claude"):
        runners.append(("claude", run_with_claude))
    if AVAILABLE_CLIS.get("copilot"):
        runners.append(("copilot", run_with_copilot))
    if AVAILABLE_CLIS.get("codex"):
        runners.append(("codex", run_with_codex))
    if AVAILABLE_CLIS.get("aider"):
        runners.append(("aider", run_with_aider))

    if not runners:
        return False, "no CLI available"

    for name, runner in runners:
        log(f"   🤖 Trying {name}...")
        success, output = runner(task, project_dir, files)
        if success:
            log(f"   ✅ {name} succeeded")
            return True, output
        log(f"   ⚠️  {name} failed: {output[:100]}")

    return False, "all CLIs failed"


# ============================================================================
# TASK DISCOVERY
# ============================================================================

def should_scan(path: Path) -> bool:
    """Check if path should be scanned (not in excluded dirs)."""
    parts = set(path.parts)
    return not parts.intersection(EXCLUDE_DIRS)


def find_code_files(project_dir: Path) -> list[Path]:
    """Find all scannable code files in project."""
    files = []
    for ext in CODE_EXTENSIONS:
        for f in project_dir.rglob(f"*{ext}"):
            if should_scan(f.relative_to(project_dir)):
                files.append(f)
    return files


def discover_tasks(project_dir: Path) -> list[dict]:
    """Discover actionable tasks in a project."""
    project = project_dir.name
    tasks = []
    code_files = find_code_files(project_dir)

    for f in code_files:
        rel = str(f.relative_to(project_dir))

        if is_skipped(project, rel):
            continue

        try:
            content = f.read_text(errors="ignore")
        except Exception:
            continue

        # 1. TODO/FIXME
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if "TODO" in stripped or "FIXME" in stripped:
                # Skip test files mentioning TODO in assertions/strings
                if "/test" in rel or "test_" in rel:
                    continue
                tasks.append({
                    "file": rel,
                    "type": "todo",
                    "line": i,
                    "task": f"Fix the TODO/FIXME on line {i}: {stripped[:120]}",
                    "priority": 1,
                })
                break  # One task per file

        # 2. Bare except (Python only)
        if f.suffix == ".py" and "except:" in content:
            tasks.append({
                "file": rel,
                "type": "quality",
                "task": f"In {rel}: Replace bare 'except:' with specific exception types. Use 'except Exception:' at minimum, or more specific types where appropriate.",
                "priority": 2,
            })

        # 3. Missing docstrings on classes (Python)
        if f.suffix == ".py":
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("class ") and line.strip().endswith(":"):
                    # Check next non-empty line for docstring
                    for j in range(i + 1, min(i + 3, len(lines))):
                        next_line = lines[j].strip()
                        if next_line and not next_line.startswith('"""') and not next_line.startswith("'''"):
                            tasks.append({
                                "file": rel,
                                "type": "docs",
                                "task": f"In {rel}: Add a docstring to the class defined around line {i+1}.",
                                "priority": 3,
                            })
                            break
                        elif next_line:
                            break

    # Sort by priority
    tasks.sort(key=lambda t: t["priority"])
    return tasks


# ============================================================================
# AUTO COMMIT & PUSH
# ============================================================================

def auto_commit_push(project_dir: Path) -> None:
    """Commit and push changes for a project."""
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_dir), capture_output=True, text=True, timeout=10,
        )
        if not status.stdout.strip():
            return

        if AUTO_COMMIT:
            subprocess.run(["git", "add", "-A"], cwd=str(project_dir), timeout=10)
            subprocess.run(
                ["git", "commit", "-m", f"🤖 Auto-commit @ {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                cwd=str(project_dir), capture_output=True, timeout=10,
            )

        if AUTO_PUSH:
            result = subprocess.run(
                ["git", "push"], cwd=str(project_dir), capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                log(f"   📤 Pushed {project_dir.name}")
            else:
                log(f"   ⚠️  Push failed for {project_dir.name}")
    except Exception as e:
        log(f"   ❌ Git error ({project_dir.name}): {str(e)[:100]}")


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def load_config() -> dict:
    """Load agents.json config."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"projects": []}


def get_project_order(config: dict) -> list[str]:
    """Get ordered project list (priority first, then config, then filesystem)."""
    all_projects = set()

    # From config
    for p in config.get("projects", []):
        all_projects.add(p)

    # From filesystem
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir() and (d / ".git").exists():
            name = d.name
            if name not in ("test-project", "test-project-clean", "test-project-pr"):
                all_projects.add(name)

    # Order: priority first, then rest alphabetically
    ordered = []
    for p in PRIORITY_PROJECTS:
        if p in all_projects:
            ordered.append(p)
            all_projects.discard(p)
    ordered.extend(sorted(all_projects))

    return ordered


def run_cycle() -> dict:
    """Run one orchestration cycle."""
    log("=" * 70)
    log("🦅 BeermannCode Orchestrator v4.0 (Multi-Project)")
    log("=" * 70)

    start = time.time()
    config = load_config()
    detect_clis()

    projects = get_project_order(config)
    log(f"📂 Projects: {', '.join(projects)}")

    tasks_done = 0
    results = {}

    for project_name in projects:
        if tasks_done >= MAX_TASKS:
            break

        project_dir = PROJECTS_DIR / project_name
        if not project_dir.is_dir():
            continue

        tasks = discover_tasks(project_dir)
        if not tasks:
            continue

        log(f"\n📦 [{project_name}] — {len(tasks)} tasks found")

        for task_info in tasks:
            if tasks_done >= MAX_TASKS:
                break

            rel_file = task_info["file"]
            task_type = task_info["type"]
            task_msg = task_info["task"]

            log(f"🚀 [{project_name}] {rel_file} [{task_type}]")
            log(f"   📝 {task_msg[:100]}")

            if DRY_RUN:
                log(f"   [DRY] would fix")
                tasks_done += 1
                results[f"{project_name}/{rel_file}"] = "🔵 dry"
                continue

            success, output = run_task_with_fallback(task_msg, project_dir, [rel_file])

            if success:
                mark_done(project_name, rel_file, task_type)
                auto_commit_push(project_dir)
                results[f"{project_name}/{rel_file}"] = "✅"
                tasks_done += 1
            else:
                mark_skipped(project_name, rel_file, output[:100])
                results[f"{project_name}/{rel_file}"] = "❌"

    # Final auto-commit sweep for any remaining changes
    if not DRY_RUN:
        for project_name in projects:
            project_dir = PROJECTS_DIR / project_name
            if project_dir.is_dir() and (project_dir / ".git").exists():
                auto_commit_push(project_dir)

    duration = time.time() - start
    log("\n" + "=" * 70)
    log(f"📊 Cycle Complete ({duration:.1f}s) — {tasks_done} tasks done")
    for key, status in results.items():
        log(f"   • {key}: {status}")
    log("=" * 70)

    return results


def get_status_json() -> dict:
    """Generate status JSON for the web dashboard."""
    config = load_config()
    projects = get_project_order(config)

    # Recent done tasks
    recent_done = []
    if DONE_FILE.exists():
        try:
            lines = DONE_FILE.read_text().strip().splitlines()
            for line in lines[-20:]:
                recent_done.append(json.loads(line))
        except Exception:
            pass

    # Recent skips
    recent_skips = []
    if SKIP_FILE.exists():
        try:
            lines = SKIP_FILE.read_text().strip().splitlines()
            for line in lines[-10:]:
                recent_skips.append(json.loads(line))
        except Exception:
            pass

    # CLI status
    clis = {
        "claude": check_cli("claude"),
        "copilot": check_cli("copilot"),
        "codex": check_cli("codex"),
        "aider": check_cli("aider"),
        "ollama": check_ollama(),
    }

    # Task counts per project
    project_stats = {}
    for name in projects:
        d = PROJECTS_DIR / name
        if d.is_dir():
            tasks = discover_tasks(d)
            project_stats[name] = {"pending_tasks": len(tasks), "task_types": {}}
            for t in tasks:
                tt = t["type"]
                project_stats[name]["task_types"][tt] = project_stats[name]["task_types"].get(tt, 0) + 1

    return {
        "timestamp": datetime.now().isoformat(),
        "clis": clis,
        "projects": project_stats,
        "priority_projects": PRIORITY_PROJECTS,
        "max_tasks_per_run": MAX_TASKS,
        "recent_done": recent_done,
        "recent_skips": recent_skips,
        "auto_push": AUTO_PUSH,
        "auto_commit": AUTO_COMMIT,
    }


def main():
    parser = argparse.ArgumentParser(description="BeermannCode Orchestrator v4")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--project", type=str, default=None, help="Single project to process")
    args = parser.parse_args()

    global DRY_RUN, MAX_TASKS, PRIORITY_PROJECTS
    if args.dry_run:
        DRY_RUN = True
    if args.max_tasks:
        MAX_TASKS = args.max_tasks
    if args.project:
        PRIORITY_PROJECTS = [args.project]

    if not acquire_lock():
        log("⏳ Already running, skipping")
        sys.exit(0)

    try:
        run_cycle()
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted")
        sys.exit(1)
    except Exception as e:
        log(f"💥 Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
