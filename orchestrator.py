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
import subprocess
import sys
import time
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
    """Save orchestrator state"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


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
# AGENT SPAWNING
# ============================================================================

def spawn_agent(
    agent_name: str,
    agent_config: dict[str, Any],
    timeout_sec: int = 300
) -> tuple[bool, str]:
    """
    Spawn agent as OpenClaw sub-agent
    
    Returns: (success, result_summary)
    """
    if DRY_RUN:
        log(f"[DRY-RUN] Would spawn {agent_name}")
        return True, "dry-run"
    
    start_time = time.time()
    
    try:
        # Build agent task description
        agent_type = agent_config.get("type", "unknown")
        agent_domain = agent_config.get("domain", "all")
        agent_mode = agent_config.get("mode", "continuous_loop")
        
        task_desc = f"""
Run {agent_name} agent:
- Type: {agent_type}
- Domain: {agent_domain}
- Mode: {agent_mode}

Config: {json.dumps(agent_config, indent=2)}

Load tasks from: {TASK_QUEUE}
Update task status based on completion.
Send WhatsApp updates per agent config.
"""
        
        # Spawn as OpenClaw sub-agent
        result = subprocess.run(
            [
                "sessions_spawn",
                "--mode", "run",
                "--runtime", "subagent",
                "--task", task_desc,
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            log_agent_run(agent_name, "✅ SUCCESS", duration, "completed")
            return True, result.stdout[:200]
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
    
    # ========== Step 2: Implementation Agents (Parallel) ==========
    log("\n🔧 Step 2: Implementation Agents (Parallel: Backend, Frontend, Database)")
    log("-" * 60)
    
    impl_agents = [
        ("Backend Agent", agents_config["agents"].get("backend", {})),
        ("Frontend Agent", agents_config["agents"].get("frontend", {})),
        ("Database Agent", agents_config["agents"].get("database", {})),
    ]
    
    impl_results = {}
    for agent_name, agent_config in impl_agents:
        if agent_config:
            success, output = spawn_agent(
                agent_name,
                agent_config,
                timeout_sec=AGENT_TIMEOUT_IMPLEMENTATION
            )
            impl_results[agent_name] = {"success": success, "output": output[:200]}
            results["agents_run"][agent_name.lower().replace(" ", "_")] = impl_results[agent_name]
    
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
