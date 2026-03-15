#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator v2.0

24/7 Agent Ecosystem Manager (7 Specialized Agents)
- Task Creator Agent (TODO/Issue Generation)
- Architecture Agent (Discovery & Prioritization)
- Backend/Frontend/Database Agents (Parallel Implementation)
- Feature Agent (Continuous Proposals)
- Review Agent (Quality Gate)

All agents run as OpenClaw sub-agents.
Task flow: Task Creator → Architecture → Implementation Agents → Review → Auto-Push → WhatsApp
"""

from __future__ import annotations
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request


# ============================================================================
# CONFIG & PATHS
# ============================================================================

WORKSPACE = Path("/home/shares/beermann")
PROJECTS_DIR = WORKSPACE / "PROJECTS"
BEERMANNCODE_DIR = PROJECTS_DIR / "BeermannCode"
AGENTS_CONFIG = BEERMANNCODE_DIR / "agents.json"
AGENTS_OVERVIEW = BEERMANNCODE_DIR / "AGENTS_OVERVIEW.md"
TASK_QUEUE = WORKSPACE / "tasks" / "pending.jsonl"
REVIEW_QUEUE = WORKSPACE / "tasks" / "pending-review.jsonl"
LOG_DIR = WORKSPACE / "logs"
LOG_FILE = LOG_DIR / "orchestrator-v2.log"
STATE_FILE = LOG_DIR / "orchestrator-state.json"
LOCK_FILE = Path("/tmp/beermanncode-orchestrator.lock")

# Environment
WHATSAPP_TO = os.getenv("WHATSAPP_TO", "+4917643995085")
NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
AUTO_PUSH = os.getenv("AUTO_PUSH", "true").lower() == "true"  # Auto-push to GitHub
AUTO_COMMIT = os.getenv("AUTO_COMMIT", "true").lower() == "true"  # Auto-commit changes

# Agent timeouts (seconds)
AGENT_TIMEOUT_ARCHITECTURE = int(os.getenv("AGENT_TIMEOUT_ARCHITECTURE", "600"))  # 10 min
AGENT_TIMEOUT_IMPLEMENTATION = int(os.getenv("AGENT_TIMEOUT_IMPLEMENTATION", "1800"))  # 30 min
AGENT_TIMEOUT_REVIEW = int(os.getenv("AGENT_TIMEOUT_REVIEW", "900"))  # 15 min


# ============================================================================
# LOGGING
# ============================================================================

def log(msg: str) -> None:
    """Log to file and stdout"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def log_agent_run(agent_name: str, status: str, duration_sec: float, result: str = "") -> None:
    """Log individual agent run"""
    msg = f"[AGENT] {agent_name:20} | Status: {status:10} | Duration: {duration_sec:6.2f}s"
    if result:
        msg += f" | {result}"
    log(msg)


# ============================================================================
# LOCK MANAGEMENT
# ============================================================================

def acquire_lock() -> bool:
    """Prevent concurrent runs"""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            log(f"[SKIP] Orchestrator already running (PID {pid})")
            return False
        except (ValueError, ProcessLookupError):
            pass
    
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    """Release lock"""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ============================================================================
# STATE MANAGEMENT
# ============================================================================

def save_state(state: dict[str, Any]) -> None:
    """Save orchestrator state atomically to prevent corruption on crash."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    tmp_file = STATE_FILE.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp_file.replace(STATE_FILE)  # atomic on POSIX


def load_state() -> dict[str, Any]:
    """Load orchestrator state"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_run": None, "agent_runs": {}}


def load_agents_config() -> dict[str, Any]:
    """Load agents.json configuration"""
    if not AGENTS_CONFIG.exists():
        log(f"[ERROR] agents.json not found at {AGENTS_CONFIG}")
        return {}
    
    try:
        return json.loads(AGENTS_CONFIG.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[ERROR] Failed to load agents.json: {e}")
        return {}


# ============================================================================
# TASK QUEUE MANAGEMENT
# ============================================================================

def load_tasks(status: str = "pending") -> list[dict[str, Any]]:
    """Load tasks from queue"""
    if not TASK_QUEUE.exists():
        return []
    
    tasks = []
    try:
        for line in TASK_QUEUE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                task = json.loads(line)
                if task.get("status") == status:
                    tasks.append(task)
            except json.JSONDecodeError:
                continue
    except Exception as e:
        log(f"[WARN] Failed to load tasks: {e}")
    
    return tasks


def save_task(task: dict[str, Any]) -> None:
    """Append/update task in queue"""
    TASK_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    
    # Read all tasks
    all_tasks = []
    if TASK_QUEUE.exists():
        for line in TASK_QUEUE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    all_tasks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    # Update or add
    found = False
    for t in all_tasks:
        if t.get("id") == task.get("id"):
            t.update(task)
            found = True
            break
    
    if not found:
        all_tasks.append(task)
    
    # Write back
    with TASK_QUEUE.open("w", encoding="utf-8") as f:
        for t in all_tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")


# ============================================================================
# WHATSAPP NOTIFICATIONS
# ============================================================================

def send_whatsapp(msg: str) -> bool:
    """Send WhatsApp notification"""
    if not NOTIFY_ENABLED:
        log("[NOTIFY] disabled")
        return True
    
    try:
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", "whatsapp",
                "--target", WHATSAPP_TO,
                "--message", msg,
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            log(f"[NOTIFY] WhatsApp sent")
            return True
        else:
            log(f"[WARN] WhatsApp send failed: {result.stderr}")
            return False
    except Exception as e:
        log(f"[WARN] WhatsApp error: {e}")
        return False


# ============================================================================
# GITHUB PR MANAGEMENT
# ============================================================================

def create_github_pr(project_dir: Path, branch: str, title: str, body: str) -> tuple[bool, str]:
    """
    Create GitHub PR via gh CLI
    
    Returns: (success, pr_url)
    """
    if DRY_RUN:
        log(f"[DRY-RUN] Would create PR for {project_dir.name}/{branch}")
        return True, f"https://github.com/Beer-mann/{project_dir.name}/pull/123"
    
    try:
        # Ensure branch is pushed
        push_result = subprocess.run(
            ["git", "-C", str(project_dir), "push", "-u", "origin", branch],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if push_result.returncode != 0:
            log(f"[ERROR] Failed to push branch {branch}: {push_result.stderr[:200]}")
            return False, ""
        
        # Find main branch
        main_branch_result = subprocess.run(
            ["git", "-C", str(project_dir), "symbolic-ref", "refs/remotes/origin/HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        main_branch = "main"
        if main_branch_result.returncode == 0:
            main_branch = main_branch_result.stdout.strip().split("/")[-1]
        
        # Create PR via gh CLI
        pr_result = subprocess.run(
            [
                "gh", "pr", "create",
                "--repo", f"Beer-mann/{project_dir.name}",
                "--base", main_branch,
                "--head", branch,
                "--title", title,
                "--body", body,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_dir)
        )
        
        if pr_result.returncode == 0:
            # Extract PR URL from output
            pr_url = pr_result.stdout.strip().split()[-1]  # URL is typically last
            log(f"✅ PR created: {pr_url}")
            
            # Send WhatsApp notification
            msg = f"🦅 *BeermannCode PR Created*\n\n📦 *{project_dir.name}*\n🔧 {title}\n\n🔗 {pr_url}"
            send_whatsapp(msg)
            
            return True, pr_url
        else:
            log(f"[ERROR] gh pr create failed: {pr_result.stderr[:200]}")
            return False, ""
    
    except Exception as e:
        log(f"[ERROR] create_github_pr failed: {e}")
        return False, ""


# ============================================================================
# AGENT SPAWNING
# ============================================================================

def spawn_project_agent(
    project_name: str,
    task_type: str = "improve",
    branch_name: str | None = None
) -> tuple[bool, str]:
    """
    Spawn sub-agent for a GitHub project via sessions_spawn
    
    Args:
        project_name: Name of project in PROJECTS/
        task_type: "ui" | "todo" | "tests" | "docs" | "improve"
        branch_name: Optional branch name (auto-generated if None)
    
    Returns: (success, output_summary)
    """
    if DRY_RUN:
        log(f"[DRY-RUN] Would spawn agent for {project_name} ({task_type})")
        return True, "dry-run"
    
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists() or not (project_dir / ".git").exists():
        log(f"[ERROR] Project {project_name} not found or not a git repo")
        return False, "project_not_found"
    
    # Get repo URL
    try:
        url_result = subprocess.run(
            ["git", "-C", str(project_dir), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5
        )
        repo_url = url_result.stdout.strip() if url_result.returncode == 0 else f"github.com/Beer-mann/{project_name}"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        repo_url = f"github.com/Beer-mann/{project_name}"
    
    # Generate branch name if not provided
    if not branch_name:
        branch_name = f"beermanncode/{task_type}-{int(time.time())}"
    
    # Build task prompt based on type
    task_prompts = {
        "ui": f"Analyze {repo_url} and create a modern web UI if none exists. Use React or plain HTML/CSS/JS. Create PR when done.",
        "todo": f"Find and fix all TODO/FIXME comments in {repo_url}. Create PR for fixes.",
        "tests": f"Add missing tests to {repo_url}. Use pytest/jest as appropriate. Create PR.",
        "docs": f"Improve documentation for {repo_url}. Add/update README, docstrings, comments. Create PR.",
        "improve": f"Analyze {repo_url} and make improvements: fix bugs, optimize code, add features. Create PR.",
    }
    
    task_prompt = task_prompts.get(task_type, task_prompts["improve"])
    task_prompt += f"\n\nAfter creating PR, report back with: 'PR created: [URL]'"
    
    # Try agents in order: claude → codex → copilot
    # All use their direct CLI (no OpenClaw, no API keys)
    # IMPORTANT: Short timeouts per agent to prevent one project blocking others
    agents = [
        ("claude", ["claude", "-p", task_prompt, "--dangerously-skip-permissions"], 300),  # 5 min
        ("codex", ["codex", "exec", "--yolo", task_prompt], 600),  # 10 min
        ("copilot", ["copilot", "-p", task_prompt, "--yolo", "--add-dir", str(project_dir)], 300),  # 5 min
    ]
    
    for agent_name, cmd, timeout_sec in agents:
        try:
            log(f"[SPAWN] Trying {agent_name} for {project_name} (timeout: {timeout_sec}s)...")
            
            spawn_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(project_dir)
            )
            
            if spawn_result.returncode == 0:
                log(f"✅ {agent_name} completed for {project_name}")
                
                # Check if PR was created (look for "PR created" or GitHub URL in output)
                output = spawn_result.stdout + spawn_result.stderr
                if "github.com" in output.lower() and "/pull/" in output.lower():
                    # Extract PR URL
                    import re
                    pr_match = re.search(r'https://github\.com/[^\s]+/pull/\d+', output)
                    if pr_match:
                        pr_url = pr_match.group(0)
                        log(f"🔗 PR detected: {pr_url}")
                        
                        # Get detailed commit info
                        try:
                            commit_result = subprocess.run(
                                ["git", "-C", str(project_dir), "log", "-1", "--pretty=format:%B"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            commit_msg = commit_result.stdout.strip()[:200]  # First 200 chars
                            
                            # Get changed files count
                            files_result = subprocess.run(
                                ["git", "-C", str(project_dir), "log", "-1", "--name-status"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            files_info = files_result.stdout.strip().split('\n')[1:]  # Skip commit hash
                            changed_files = len(files_info)
                            
                            msg = f"🦅 *{project_name}* PR\n\n"
                            msg += f"🔧 {task_type.upper()}\n"
                            msg += f"📝 {commit_msg}\n"
                            msg += f"📁 {changed_files} files changed\n"
                            msg += f"🔗 {pr_url}"
                        except Exception as e:
                            # Fallback if git info fails
                            msg = f"🦅 *{project_name}* PR\n\n🔧 {task_type}\n🔗 {pr_url}"
                        
                        send_whatsapp(msg)
                
                return True, output[:500]
            else:
                log(f"[WARN] {agent_name} failed: {spawn_result.stderr[:200]}")
                continue  # Try next agent
        
        except FileNotFoundError:
            log(f"[SKIP] {agent_name} CLI not found")
            continue
        except Exception as e:
            log(f"[ERROR] {agent_name} error: {e}")
            continue
    
    log(f"[ERROR] All agents failed for {project_name}")
    return False, "all_agents_failed"


def spawn_agent(
    agent_name: str,
    agent_config: dict[str, Any],
    timeout_sec: int = 300
) -> tuple[bool, str]:
    """
    LEGACY: Spawn agent using Aider CLI (kept for backward compat)
    
    Returns: (success, result_summary)
    """
    if DRY_RUN:
        log(f"[DRY-RUN] Would spawn {agent_name}")
        return True, "dry-run"
    
    start_time = time.time()
    
    try:
        # Get agent domain and tasks
        agent_domain = agent_config.get("domain", "all")
        agent_desc = agent_config.get("description", "")
        
        # Find project to work on based on domain
        target_project = None
        for project in PROJECTS_DIR.iterdir():
            if not project.is_dir() or not (project / ".git").exists():
                continue
            
            # Check if project has work for this agent
            if agent_domain == "backend" and any(p.suffix == ".py" for p in project.rglob("*.py")):
                target_project = project
                break
            elif agent_domain == "frontend" and any(p.suffix in [".js", ".jsx", ".tsx"] for p in project.rglob("*")):
                target_project = project
                break
            elif agent_domain == "all":
                target_project = project
                break
        
        if not target_project:
            log(f"[SKIP] {agent_name}: No suitable project found for domain {agent_domain}")
            return True, "no_work"
        
        # Build Aider task from agent config
        task_message = agent_desc or f"Analyze and improve code in this project. {agent_name} focus."
        
        # Run Aider
        env = os.environ.copy()
        env["OLLAMA_API_BASE"] = os.getenv("OLLAMA_HOST", "http://192.168.0.213:11434")
        
        result = subprocess.run(
            [
                "aider",
                "--model", "ollama/qwen2.5-coder:7b",
                "--env-file", "/home/beermann/.aider.env",
                "--yes-always",
                "--auto-commits",
                "--no-show-model-warnings",
                "--message", task_message
            ],
            cwd=str(target_project),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_sec
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            log_agent_run(agent_name, "✅ SUCCESS", duration, f"worked on {target_project.name}")
            return True, result.stdout[-200:]
        else:
            log_agent_run(agent_name, "❌ FAILED", duration, result.stderr[:100])
            return False, result.stderr[:200]
    
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        log_agent_run(agent_name, "⏱️ TIMEOUT", duration, f">{timeout_sec}s")
        return False, f"Timeout after {timeout_sec}s"
    except Exception as e:
        duration = time.time() - start_time
        log_agent_run(agent_name, "💥 ERROR", duration, str(e)[:50])
        return False, str(e)


# ============================================================================
# ORCHESTRATION WORKFLOW
# ============================================================================

def run_orchestration_cycle() -> dict[str, Any]:
    """
    Execute one complete orchestration cycle:
    
    1. Run Architecture Agent (Discovery & Prioritization)
    2. Run Implementation Agents in parallel (Backend, Frontend, Database)
    3. Run Feature Agent (Continuous)
    4. Wait for Review Agent (triggered when PR created)
    5. Auto-Push if approved
    6. Send WhatsApp summary
    """
    
    log("\n" + "="*80)
    log("🦅 BeermannCode Orchestration Cycle")
    log("="*80)
    
    cycle_start = time.time()
    agents_config = load_agents_config()
    
    if not agents_config.get("agents"):
        log("[ERROR] No agents configured in agents.json")
        return {"success": False, "error": "no_agents_configured"}
    
    results = {
        "cycle_start": datetime.now().isoformat(),
        "agents_run": {},
        "tasks_discovered": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
    }
    
    # ========== Step 0: Task Creator Agent ==========
    log("\n📝 Step 0: Task Creator Agent (TODO/Issue Generation)")
    log("-" * 60)
    
    task_creator_config = agents_config["agents"].get("task_creator", {})
    if task_creator_config:
        success, output = spawn_agent(
            "Task Creator Agent",
            task_creator_config,
            timeout_sec=600  # 10 min for thorough scanning
        )
        results["agents_run"]["task_creator"] = {
            "success": success,
            "output": output[:200]
        }
        
        if success:
            pending_tasks = load_tasks("pending")
            log(f"[TASK_CREATOR] Generated new TODOs and Issues")
    
    # ========== Step 1: Architecture Agent ==========
    log("\n📋 Step 1: Architecture Agent (Discovery & Prioritization)")
    log("-" * 60)
    
    arch_config = agents_config["agents"].get("architecture", {})
    if arch_config:
        success, output = spawn_agent(
            "Architecture Agent",
            arch_config,
            timeout_sec=AGENT_TIMEOUT_ARCHITECTURE
        )
        results["agents_run"]["architecture"] = {
            "success": success,
            "output": output[:200]
        }
        
        if success:
            # Architecture Agent should have populated task queue
            pending_tasks = load_tasks("pending")
            results["tasks_discovered"] = len(pending_tasks)
            log(f"[ARCH] Discovered {len(pending_tasks)} pending tasks")
    
    # ========== Step 2: Spawn Agents for All Projects ==========
    log("\n🔧 Step 2: Spawn Coding Agents for GitHub Projects")
    log("-" * 60)
    
    # Scan all GitHub projects (exclude only test projects)
    exclude_patterns = ["test-project", "test-project-clean", "test-project-pr"]
    projects_to_improve = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir() or not (project_dir / ".git").exists():
            continue
        if project_dir.name in exclude_patterns:
            continue  # Skip test projects only
        projects_to_improve.append(project_dir.name)
    
    log(f"Found {len(projects_to_improve)} projects: {', '.join(projects_to_improve)}")
    
    # ========== PARALLEL SPAWNING ==========
    # Spawn agents for all projects in parallel (max 4 concurrent)
    # This prevents one hanging project from blocking others
    
    impl_results = {}
    
    # Pre-calculate task types for all projects
    project_tasks = {}
    for project_name in projects_to_improve:
        project_dir = PROJECTS_DIR / project_name
        
        # Priority: ui → tests → improve
        # Check for UI in common locations
        has_ui = False
        ui_patterns = ["**/index.html", "**/templates/*.html", "**/static/*.html", "**/public/*.html", 
                      "**/frontend/**/*.html", "**/ui/**/*.html", "**/*.jsx", "**/*.vue"]
        for pattern in ui_patterns:
            if any(project_dir.glob(pattern)):
                has_ui = True
                break
        
        has_tests = (project_dir / "tests").exists() or (project_dir / "test").exists()
        
        if not has_ui:
            task_type = "ui"
        elif not has_tests:
            task_type = "tests"
        else:
            task_type = "improve"  # General improvements
        
        project_tasks[project_name] = task_type
        log(f"[QUEUE] {project_name}: {task_type}")
    
    # Spawn in parallel (max 4 at a time)
    log("\n[PARALLEL] Spawning agents (max 4 concurrent)...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(spawn_project_agent, project_name, project_tasks[project_name]): project_name
            for project_name in projects_to_improve
        }
        
        for future in as_completed(futures):
            project_name = futures[future]
            try:
                success, output = future.result(timeout=1200)  # 20 min max per task
                impl_results[project_name] = {
                    "success": success,
                    "output": output[:200],
                    "task_type": project_tasks[project_name]
                }
                results["agents_run"][project_name] = impl_results[project_name]
                status = "✅" if success else "❌"
                log(f"[DONE] {status} {project_name}")
            except TimeoutError:
                log(f"[TIMEOUT] {project_name} exceeded 20 min limit")
                impl_results[project_name] = {
                    "success": False,
                    "output": "timeout",
                    "task_type": project_tasks[project_name]
                }
                results["agents_run"][project_name] = impl_results[project_name]
            except Exception as e:
                log(f"[ERROR] {project_name}: {str(e)[:100]}")
                impl_results[project_name] = {
                    "success": False,
                    "output": str(e)[:200],
                    "task_type": project_tasks[project_name]
                }
                results["agents_run"][project_name] = impl_results[project_name]
    
    # ========== Step 3: Feature Agent (Continuous) ==========
    log("\n💡 Step 3: Feature Agent (Feature Proposals & Strategic Ideas)")
    log("-" * 60)
    
    feature_config = agents_config["agents"].get("feature", {})
    if feature_config:
        # Feature Agent runs continuously, just trigger a check
        success, output = spawn_agent(
            "Feature Agent",
            feature_config,
            timeout_sec=600  # 10 min for continuous scanning
        )
        results["agents_run"]["feature"] = {
            "success": success,
            "output": output[:200]
        }
    
    # ========== Step 4: Review Agent (Reactive) ==========
    log("\n✅ Step 4: Review Agent (Quality Gate & Validation)")
    log("-" * 60)
    
    # Review Agent is triggered when PRs exist
    # (would be via webhook in production)
    log("[REVIEW] Checking for pending reviews...")
    
    review_config = agents_config["agents"].get("review", {})
    if review_config:
        # Only spawn if there are items to review
        pending_reviews = load_tasks("waiting_review")  # or similar
        
        if pending_reviews:
            success, output = spawn_agent(
                "Review Agent",
                review_config,
                timeout_sec=AGENT_TIMEOUT_REVIEW
            )
            results["agents_run"]["review"] = {
                "success": success,
                "output": output[:200]
            }
        else:
            log("[REVIEW] No pending reviews")
            results["agents_run"]["review"] = {"success": True, "output": "no_pending"}
    
    # ========== Step 5: GitHub Project Agents (NEW!) ==========
    log("\n🐙 Step 5: GitHub Project Agents (Spawn for each repo)")
    log("-" * 60)
    
    # Scan all GitHub projects and spawn agents (exclude only test projects)
    exclude_patterns = ["test-project", "test-project-clean", "test-project-pr"]
    github_projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir() or not (project_dir / ".git").exists():
            continue
        if project_dir.name in exclude_patterns:
            continue  # Skip test projects only
        
        # Check if has GitHub remote
        try:
            remote_result = subprocess.run(
                ["git", "-C", str(project_dir), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if remote_result.returncode == 0 and "github.com" in remote_result.stdout:
                github_projects.append(project_dir.name)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    
    log(f"Found {len(github_projects)} GitHub projects: {', '.join(github_projects)}")
    
    # ========== PARALLEL SPAWNING FOR GITHUB PROJECTS ==========
    # Pre-calculate task types
    github_project_tasks = {}
    for project_name in github_projects:
        project_dir = PROJECTS_DIR / project_name
        
        # Determine what work is needed
        needs_ui = not any((project_dir / d).exists() for d in ["frontend", "ui", "public"])
        has_todos = False
        
        try:
            # Quick TODO check
            result = subprocess.run(
                ["grep", "-r", "TODO\\|FIXME", str(project_dir), "--include=*.py", "--include=*.js"],
                capture_output=True,
                timeout=10
            )
            has_todos = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        
        # Decide task type
        if needs_ui:
            task_type = "ui"
        elif has_todos:
            task_type = "todo"
        else:
            task_type = "improve"
        
        github_project_tasks[project_name] = task_type
        log(f"[GITHUB-QUEUE] {project_name}: {task_type}")
    
    # Spawn in parallel (max 4 at a time)
    log("\n[GITHUB-PARALLEL] Spawning GitHub agents (max 4 concurrent)...")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(spawn_project_agent, project_name, github_project_tasks[project_name]): project_name
            for project_name in github_projects
        }
        
        for future in as_completed(futures):
            project_name = futures[future]
            try:
                success, output = future.result(timeout=1200)  # 20 min max per task
                results["agents_run"][f"github_{project_name}"] = {
                    "success": success,
                    "output": output[:200],
                    "task_type": github_project_tasks[project_name]
                }
                status = "✅" if success else "❌"
                log(f"[GITHUB-DONE] {status} {project_name}")
            except TimeoutError:
                log(f"[GITHUB-TIMEOUT] {project_name} exceeded 20 min limit")
                results["agents_run"][f"github_{project_name}"] = {
                    "success": False,
                    "output": "timeout",
                    "task_type": github_project_tasks[project_name]
                }
            except Exception as e:
                log(f"[GITHUB-ERROR] {project_name}: {str(e)[:100]}")
                results["agents_run"][f"github_{project_name}"] = {
                    "success": False,
                    "output": str(e)[:200],
                    "task_type": github_project_tasks[project_name]
                }
    
    # ========== Step 6: Auto-Commit & Auto-Push ==========
    if AUTO_COMMIT or AUTO_PUSH:
        log("\n📤 Step 6: Auto-Commit & Auto-Push")
        log("-" * 60)
        
        # Scan all projects for uncommitted changes
        projects_with_changes = []
        
        for project_dir in PROJECTS_DIR.iterdir():
            if not project_dir.is_dir() or not (project_dir / ".git").exists():
                continue
            
            try:
                # Check if there are uncommitted changes
                result = subprocess.run(
                    ["git", "-C", str(project_dir), "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.stdout.strip():
                    projects_with_changes.append(project_dir.name)
                    
                    if DRY_RUN:
                        log(f"[DRY-RUN] Would commit & push {project_dir.name}")
                        continue
                    
                    # Auto-commit
                    if AUTO_COMMIT:
                        subprocess.run(
                            ["git", "-C", str(project_dir), "add", "-A"],
                            timeout=10
                        )
                        subprocess.run(
                            ["git", "-C", str(project_dir), "commit", "-m", 
                             f"🤖 Auto-commit by BeermannCode Orchestrator @ {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                            timeout=10
                        )
                        log(f"✅ Auto-committed: {project_dir.name}")
                    
                    # Auto-push
                    if AUTO_PUSH:
                        push_result = subprocess.run(
                            ["git", "-C", str(project_dir), "push"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if push_result.returncode == 0:
                            log(f"📤 Auto-pushed: {project_dir.name}")
                        else:
                            log(f"⚠️  Push failed for {project_dir.name}: {push_result.stderr[:100]}")
            
            except Exception as e:
                log(f"❌ Error processing {project_dir.name}: {str(e)[:100]}")
        
        if projects_with_changes:
            log(f"📋 Projects with changes: {', '.join(projects_with_changes)}")
        else:
            log("✨ No uncommitted changes across projects")
    
    # ========== SUMMARY ==========
    cycle_duration = time.time() - cycle_start
    
    log("\n" + "="*80)
    log("📊 Orchestration Cycle Summary")
    log("="*80)
    log(f"Duration: {cycle_duration:.2f}s")
    log(f"Tasks Discovered: {results['tasks_discovered']}")
    log(f"Agents Run: {len(results['agents_run'])}")
    
    success_count = sum(1 for r in results["agents_run"].values() if r.get("success"))
    log(f"Successful: {success_count}/{len(results['agents_run'])}")
    
    results["cycle_duration"] = cycle_duration
    results["cycle_end"] = datetime.now().isoformat()
    
    return results


# ============================================================================
# WHATSAPP SUMMARY
# ============================================================================

def send_cycle_summary(results: dict[str, Any]) -> None:
    """Send WhatsApp summary of orchestration cycle"""
    if not results:
        return
    
    agents_summary = []
    for agent_name, agent_result in results.get("agents_run", {}).items():
        status = "✅" if agent_result.get("success") else "❌"
        agents_summary.append(f"• {agent_name}: {status}")
    
    msg = "🦅 *BeermannCode Cycle*\n\n"
    msg += f"📋 *Tasks:* {results.get('tasks_discovered', 0)} discovered\n"
    msg += f"⏱️ *Duration:* {results.get('cycle_duration', 0):.1f}s\n"
    msg += "\n*Agents:*\n" + "\n".join(agents_summary)
    
    send_whatsapp(msg)


# ============================================================================
# CRON SUPPORT
# ============================================================================

def is_time_in_range(hour_start: int, hour_end: int) -> bool:
    """Check if current time is within range (e.g., 6-22 for daytime)"""
    current_hour = datetime.now().hour
    if hour_start <= hour_end:
        return hour_start <= current_hour < hour_end
    else:  # e.g., 22-6 (night)
        return current_hour >= hour_start or current_hour < hour_end


def should_run_agent(agent_name: str) -> bool:
    """Check if agent should run based on time constraints"""
    cron_schedule = {
        "architecture": {"always": True},
        "backend": {"always": True},
        "frontend": {"always": True},
        "database": {"always": True},
        "feature": {"always": True},
        "review": {"always": True},
    }
    
    config = cron_schedule.get(agent_name.lower(), {})
    
    if config.get("always"):
        return True
    
    hour_start = config.get("hour_start", 6)
    hour_end = config.get("hour_end", 22)
    
    return is_time_in_range(hour_start, hour_end)


# ============================================================================
# MAIN
# ============================================================================

def _handle_shutdown(signum: int, frame: object) -> None:
    """Handle SIGTERM/SIGINT gracefully by releasing the lock before exit."""
    log(f"[SIGNAL] Received signal {signum}, shutting down gracefully...")
    release_lock()
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="🦅 BeermannCode Orchestrator v2.0")
    ap.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    ap.add_argument("--agent", type=str, help="Run specific agent only")
    ap.add_argument("--no-notify", action="store_true", help="Disable WhatsApp notifications")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = ap.parse_args()

    # Override globals from args
    global NOTIFY_ENABLED, DRY_RUN
    if args.no_notify:
        NOTIFY_ENABLED = False
    if args.dry_run:
        DRY_RUN = True

    # Register shutdown handlers so the lock is released on SIGTERM/SIGINT
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    log("🦅 BeermannCode Orchestrator v2.0 starting...")
    log(f"Workspace: {WORKSPACE}")
    log(f"Config: {AGENTS_CONFIG}")
    log(f"Notifications: {'enabled' if NOTIFY_ENABLED else 'disabled'}")
    log(f"Dry-Run: {DRY_RUN}")

    # Acquire lock
    if not acquire_lock():
        return 1

    try:
        # Run orchestration cycle
        results = run_orchestration_cycle()

        # Save state
        state = load_state()
        state["last_cycle"] = results
        save_state(state)

        # Send summary
        if NOTIFY_ENABLED:
            send_cycle_summary(results)

        log("\n✅ Orchestration cycle completed")
        return 0

    except Exception as e:
        log(f"\n💥 Orchestration failed: {e}")
        import traceback
        log(traceback.format_exc())
        return 1

    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
