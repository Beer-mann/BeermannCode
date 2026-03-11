#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator v3.0

Native CLI Agents (kein OpenClaw)
- Claude CLI für Strategy/Architecture/Review
- Codex CLI für Code Generation
- Copilot CLI für Frontend
- Aider für Quick Fixes

Auto-Commit + Auto-Push integriert
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIG
# ============================================================================

WORKSPACE = Path("/home/shares/beermann")
PROJECTS_DIR = WORKSPACE / "PROJECTS"
BEERMANNCODE_DIR = PROJECTS_DIR / "BeermannCode"
LOG_DIR = WORKSPACE / "logs"
LOG_FILE = LOG_DIR / "orchestrator-v3.log"

AUTO_PUSH = os.getenv("AUTO_PUSH", "true").lower() == "true"
AUTO_COMMIT = os.getenv("AUTO_COMMIT", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# CLI Agents verfügbar
CLAUDE_CLI = "claude"
CODEX_CLI = "codex"
COPILOT_CLI = "copilot"
AIDER_CLI = "aider"

# ============================================================================
# LOGGING
# ============================================================================

def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)

# ============================================================================
# CLI AGENT RUNNERS
# ============================================================================

def run_claude(task: str, project_dir: Path, timeout: int = 300) -> tuple[bool, str]:
    """Run Claude CLI on task"""
    try:
        result = subprocess.run(
            [CLAUDE_CLI, "code", "--message", task],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout[-200:]
    except Exception as e:
        return False, str(e)[:200]


def run_codex(task: str, project_dir: Path, files: list[str] = None, timeout: int = 300) -> tuple[bool, str]:
    """Run Codex CLI on task"""
    try:
        cmd = [CODEX_CLI, "--message", task]
        if files:
            cmd.extend(files)
        
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout[-200:]
    except Exception as e:
        return False, str(e)[:200]


def run_copilot(prompt: str, project_dir: Path, timeout: int = 300) -> tuple[bool, str]:
    """Run GitHub Copilot CLI"""
    try:
        # copilot suggest "task description"
        result = subprocess.run(
            [COPILOT_CLI, "suggest", prompt],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout[-200:]
    except Exception as e:
        return False, str(e)[:200]


def run_aider(task: str, project_dir: Path, files: list[str] = None, timeout: int = 600) -> tuple[bool, str]:
    """Run Aider CLI"""
    try:
        env = os.environ.copy()
        env["OLLAMA_API_BASE"] = "http://192.168.0.213:11434"
        
        cmd = [
            AIDER_CLI,
            "--model", "ollama/qwen2.5-coder:7b",
            "--env-file", "/home/beermann/.aider.env",
            "--yes-always",
            "--auto-commits",
            "--no-show-model-warnings",
            "--message", task
        ]
        
        if files:
            cmd.extend(files)
        
        result = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout[-200:]
    except Exception as e:
        return False, str(e)[:200]

# ============================================================================
# AGENT TASKS
# ============================================================================

def task_creator_agent() -> tuple[bool, str]:
    """Scannt improvements.md und erstellt neue Tasks"""
    log("📝 Task Creator Agent (Claude CLI)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would analyze improvements.md")
        return True, "dry-run"
    
    task = """Analyze improvements.md and identify the next TODO item to work on.
Output just the task description in one sentence."""
    
    return run_claude(task, BEERMANNCODE_DIR, timeout=60)


def architecture_agent() -> tuple[bool, str]:
    """Claude analysiert Architektur"""
    log("🏗️ Architecture Agent (Claude CLI)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would analyze architecture")
        return True, "dry-run"
    
    task = """Review the current codebase architecture.
Suggest one improvement for better modularity or code organization."""
    
    return run_claude(task, BEERMANNCODE_DIR, timeout=180)


def backend_agent() -> tuple[bool, str]:
    """Codex für Backend-Code"""
    log("⚙️ Backend Agent (Codex CLI)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would work on backend")
        return True, "dry-run"
    
    task = """Improve error handling in app.py.
Add try-except blocks where appropriate."""
    
    files = ["app.py"]
    return run_codex(task, BEERMANNCODE_DIR, files, timeout=300)


def frontend_agent() -> tuple[bool, str]:
    """Copilot für Frontend"""
    log("🎨 Frontend Agent (Copilot CLI)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would work on frontend")
        return True, "dry-run"
    
    prompt = "Improve the dashboard UI in templates/orchestrator_dashboard.html"
    return run_copilot(prompt, BEERMANNCODE_DIR, timeout=300)


def database_agent() -> tuple[bool, str]:
    """Aider für Datenbank-Code"""
    log("💾 Database Agent (Aider)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would work on database")
        return True, "dry-run"
    
    task = "Add database connection pooling if not already present"
    return run_aider(task, BEERMANNCODE_DIR, timeout=300)


def feature_agent() -> tuple[bool, str]:
    """Claude schlägt Features vor"""
    log("💡 Feature Agent (Claude CLI)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would propose features")
        return True, "dry-run"
    
    task = """Analyze the codebase and suggest one new feature that would add value.
Keep it small and implementable."""
    
    return run_claude(task, BEERMANNCODE_DIR, timeout=120)


def review_agent() -> tuple[bool, str]:
    """Claude reviewed Code"""
    log("✅ Review Agent (Claude CLI)")
    
    if DRY_RUN:
        log("   [DRY-RUN] Would review code")
        return True, "dry-run"
    
    # Review letzte 3 Commits
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-3"],
            cwd=str(BEERMANNCODE_DIR),
            capture_output=True,
            text=True,
            timeout=10
        )
        commits = result.stdout.strip()
        
        task = f"""Review these recent commits:
{commits}

Check if the changes are good quality. Reply with brief feedback."""
        
        return run_claude(task, BEERMANNCODE_DIR, timeout=180)
    except Exception as e:
        return False, str(e)[:200]

# ============================================================================
# AUTO-COMMIT & AUTO-PUSH
# ============================================================================

def auto_commit_push() -> None:
    """Auto-commit and push all projects"""
    log("📤 Auto-Commit & Auto-Push")
    
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir() or not (project_dir / ".git").exists():
            continue
        
        try:
            # Check for changes
            result = subprocess.run(
                ["git", "-C", str(project_dir), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if not result.stdout.strip():
                continue
            
            if DRY_RUN:
                log(f"   [DRY-RUN] Would commit & push {project_dir.name}")
                continue
            
            # Auto-commit
            if AUTO_COMMIT:
                subprocess.run(["git", "-C", str(project_dir), "add", "-A"], timeout=10)
                subprocess.run(
                    ["git", "-C", str(project_dir), "commit", "-m",
                     f"🤖 Auto-commit @ {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                    timeout=10
                )
                log(f"   ✅ Committed: {project_dir.name}")
            
            # Auto-push
            if AUTO_PUSH:
                push_result = subprocess.run(
                    ["git", "-C", str(project_dir), "push"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if push_result.returncode == 0:
                    log(f"   📤 Pushed: {project_dir.name}")
                else:
                    log(f"   ⚠️  Push failed: {project_dir.name}")
        
        except Exception as e:
            log(f"   ❌ Error ({project_dir.name}): {str(e)[:100]}")

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def run_cycle() -> None:
    log("="*80)
    log("🦅 BeermannCode Orchestrator v3.0 (Native CLIs)")
    log("="*80)
    
    start = time.time()
    results = {}
    
    # Run agents
    agents = [
        ("task_creator", task_creator_agent),
        ("architecture", architecture_agent),
        ("backend_agent", backend_agent),
        ("frontend_agent", frontend_agent),
        ("database_agent", database_agent),
        ("feature", feature_agent),
        ("review", review_agent),
    ]
    
    for name, agent_func in agents:
        try:
            success, output = agent_func()
            results[name] = "✅" if success else "❌"
        except Exception as e:
            log(f"   ❌ {name} crashed: {str(e)[:100]}")
            results[name] = "❌"
    
    # Auto-commit & push
    auto_commit_push()
    
    # Summary
    duration = time.time() - start
    log("="*80)
    log(f"📊 Cycle Complete ({duration:.1f}s)")
    for name, status in results.items():
        log(f"   • {name}: {status}")
    log("="*80)


def main():
    parser = argparse.ArgumentParser(description="BeermannCode Orchestrator v3")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    args = parser.parse_args()
    
    global DRY_RUN
    DRY_RUN = args.dry_run or DRY_RUN
    
    try:
        run_cycle()
    except KeyboardInterrupt:
        log("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
