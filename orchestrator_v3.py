#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator v3.0

24/7 Agent Ecosystem Manager (CLI-Based)
- Task Creator Agent (AIDER + Ollama)
- Architecture Agent (Claude CLI)
- Backend Agent (Claude CLI → Codex → Copilot)
- Frontend Agent (Claude CLI → Copilot → Codex)
- Database Agent (Claude CLI → Codex)
- Feature Agent (Claude CLI → Codex)
- Review Agent (Claude CLI → Codex, via REVIEW_AGENT.md)

All agents use native CLIs + MD-File configurations
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


# ============================================================================
# CONFIG & PATHS
# ============================================================================

WORKSPACE = Path("/home/shares/beermann")
PROJECTS_DIR = WORKSPACE / "PROJECTS"
BEERMANNCODE_DIR = PROJECTS_DIR / "BeermannCode"
AGENTS_CONFIG = BEERMANNCODE_DIR / "agents.json"
MODEL_ROUTING_CONFIG = BEERMANNCODE_DIR / "model_routing.json"
AGENTS_DIR = BEERMANNCODE_DIR / "agents"
TASK_QUEUE = WORKSPACE / "tasks" / "pending.jsonl"
LOG_DIR = WORKSPACE / "logs"
LOG_FILE = LOG_DIR / "orchestrator-v3.log"
STATE_FILE = LOG_DIR / "orchestrator-state.json"
LOCK_FILE = Path("/tmp/beermanncode-orchestrator.lock")

# Environment
WHATSAPP_TO = os.getenv("WHATSAPP_TO", "+4917643995085")
NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Timeouts
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "1800"))  # 30 min default


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
    msg = f"[AGENT] {agent_name:25} | {status:15} | {duration_sec:6.2f}s"
    if result:
        msg += f" | {result[:100]}"
    log(msg)


# ============================================================================
# LOCK MANAGEMENT
# ============================================================================

def acquire_lock() -> bool:
    """Prevent concurrent runs"""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)
            log(f"[SKIP] Already running (PID {pid})")
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
# CONFIG LOADING
# ============================================================================

def load_agents_config() -> dict[str, Any]:
    """Load agents.json"""
    if not AGENTS_CONFIG.exists():
        log(f"[ERROR] agents.json not found")
        return {}
    try:
        return json.loads(AGENTS_CONFIG.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[ERROR] Failed to load agents.json: {e}")
        return {}


def load_model_routing() -> dict[str, Any]:
    """Load model_routing.json"""
    if not MODEL_ROUTING_CONFIG.exists():
        log(f"[ERROR] model_routing.json not found")
        return {}
    try:
        return json.loads(MODEL_ROUTING_CONFIG.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[ERROR] Failed to load model_routing.json: {e}")
        return {}


def load_agent_md(agent_name: str) -> str:
    """Load agent MD file"""
    md_file = AGENTS_DIR / f"{agent_name.upper()}_AGENT.md"
    if not md_file.exists():
        log(f"[WARN] MD file not found: {md_file}")
        return ""
    try:
        return md_file.read_text(encoding="utf-8")
    except Exception as e:
        log(f"[WARN] Failed to load {agent_name}.md: {e}")
        return ""


# ============================================================================
# CLI EXECUTION
# ============================================================================

def get_model_cli(model: str) -> str:
    """Map model to CLI command"""
    if "ollama" in model:
        return f"aider --model {model}"
    elif "claude" in model.lower():
        return "claude"
    elif "codex" in model.lower():
        return "codex exec"
    elif "copilot" in model.lower():
        return "gh copilot suggest"
    else:
        return "claude"  # Default


def run_agent(agent_name: str, task_prompt: str, model_routing: dict, timeout_sec: int = 1800) -> tuple[bool, str]:
    """
    Run agent via CLI with model fallback
    
    Returns: (success, output)
    """
    start = time.time()
    
    # Normalize agent name: "Task Creator" → "task_creator"
    agent_key = agent_name.lower().replace(" ", "_")
    
    # Get model routing for this agent
    agent_routing = model_routing.get("agents", {}).get(agent_key, {})
    if not agent_routing:
        log(f"[WARN] No routing config for {agent_name}")
        return False, "no_config"
    
    # Try models in priority order
    for priority in ["primary", "secondary", "tertiary", "quaternary"]:
        model_config = agent_routing.get(priority)
        if not model_config:
            continue
        
        model = model_config.get("model", "claude")
        model_timeout = model_config.get("timeout_sec", 600)
        
        try:
            # Build CLI command
            cli_base = get_model_cli(model)
            
            if "aider" in cli_base:
                # AIDER for Ollama
                cmd = f"{cli_base} --ask '{task_prompt}'"
            else:
                # Other CLIs
                cmd = f"{cli_base} '{task_prompt}'"
            
            if DRY_RUN:
                log(f"[DRY-RUN] {agent_name}: Would run: {cmd[:80]}")
                return True, "dry_run"
            
            log(f"[EXEC] {agent_name} with {model}: {cmd[:80]}")
            
            # Run command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=min(model_timeout, timeout_sec)
            )
            
            duration = time.time() - start
            
            if result.returncode == 0:
                log_agent_run(agent_name, f"✅ {model}", duration, result.stdout[:50])
                return True, result.stdout[:200]
            else:
                log_agent_run(agent_name, f"⚠️ {model} failed", duration, result.stderr[:50])
                continue  # Try next model
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            log_agent_run(agent_name, f"⏱️ {model} timeout", duration, f">{model_timeout}s")
            continue  # Try next model
        
        except Exception as e:
            duration = time.time() - start
            log_agent_run(agent_name, f"💥 {model} error", duration, str(e)[:50])
            continue  # Try next model
    
    duration = time.time() - start
    log_agent_run(agent_name, "❌ ALL MODELS FAILED", duration, "all_timeouts_or_errors")
    return False, "all_models_failed"


# ============================================================================
# ORCHESTRATION CYCLE
# ============================================================================

def run_orchestration_cycle() -> dict[str, Any]:
    """
    Execute one complete orchestration cycle
    """
    log("\n" + "="*80)
    log("🦅 BeermannCode Orchestration Cycle v3.0")
    log("="*80)
    
    cycle_start = time.time()
    
    # Load configs
    agents_config = load_agents_config()
    model_routing = load_model_routing()
    
    if not agents_config.get("agents"):
        log("[ERROR] No agents configured")
        return {"success": False}
    
    results = {
        "cycle_start": datetime.now().isoformat(),
        "agents_run": {},
    }
    
    # ========== Step 0: Task Creator Agent ==========
    log("\n📝 Step 0: Task Creator Agent")
    log("-" * 60)
    
    task_creator_config = agents_config["agents"].get("task_creator", {})
    task_creator_md = load_agent_md("task_creator")
    
    if task_creator_config and task_creator_md:
        prompt = f"""Based on these rules from TASK_CREATOR_AGENT.md:
{task_creator_md[:500]}

Scan all projects in {PROJECTS_DIR} for:
- Test gaps (functions without tests)
- Doc gaps (missing docstrings)
- Code quality issues (duplication, magic numbers)
- Security issues
- Dependency updates
- Performance issues
- Logging gaps

Create TODOs in {TASK_QUEUE}"""
        
        success, output = run_agent("task_creator", prompt, model_routing, timeout_sec=600)
        results["agents_run"]["task_creator"] = {"success": success, "output": output[:100]}
    
    # ========== Step 1: Architecture Agent ==========
    log("\n📋 Step 1: Architecture Agent")
    log("-" * 60)
    
    architecture_config = agents_config["agents"].get("architecture", {})
    architecture_md = load_agent_md("architecture")
    
    if architecture_config and architecture_md:
        prompt = f"""Based on ARCHITECTURE_AGENT.md rules:
{architecture_md[:500]}

Analyze {TASK_QUEUE}:
- Discover pending tasks
- Assign priorities (Critical/High/Medium/Low)
- Detect conflicts & dependencies
- Load balance across agents

Return: Updated task queue with priorities"""
        
        success, output = run_agent("architecture", prompt, model_routing, timeout_sec=600)
        results["agents_run"]["architecture"] = {"success": success, "output": output[:100]}
    
    # ========== Step 2: Implementation Agents (Parallel) ==========
    log("\n🔧 Step 2: Implementation Agents (Backend, Frontend, Database)")
    log("-" * 60)
    
    impl_agents = [
        ("backend", "backend", "BACKEND_AGENT.md"),
        ("frontend", "frontend", "FRONTEND_AGENT.md"),
        ("database", "database", "DATABASE_AGENT.md"),
    ]
    
    for agent_key, agent_name, md_file in impl_agents:
        config = agents_config["agents"].get(agent_key, {})
        md_content = load_agent_md(agent_key)
        
        if config and md_content:
            prompt = f"""Based on {md_file} rules:
{md_content[:500]}

Read pending tasks from {TASK_QUEUE}
Find tasks assigned to {agent_name}
Implement the code changes:
- Write code
- Write tests (>80% coverage)
- Write docstrings
- Commit to git

Return: Status + changed files"""
            
            success, output = run_agent(agent_key, prompt, model_routing, timeout_sec=1800)
            results["agents_run"][agent_key] = {"success": success, "output": output[:100]}
    
    # ========== Step 3: Feature Agent ==========
    log("\n💡 Step 3: Feature Agent")
    log("-" * 60)
    
    feature_config = agents_config["agents"].get("feature", {})
    feature_md = load_agent_md("feature")
    
    if feature_config and feature_md:
        prompt = f"""Based on FEATURE_AGENT.md rules:
{feature_md[:500]}

Scan all projects for:
- Feature opportunities
- Code-smell improvements
- Refactoring ideas
- Strategic insights

Create NEW TODOs with ROI + effort estimates"""
        
        success, output = run_agent("feature", prompt, model_routing, timeout_sec=600)
        results["agents_run"]["feature"] = {"success": success, "output": output[:100]}
    
    # ========== Step 4: Review Agent ==========
    log("\n✅ Step 4: Review Agent")
    log("-" * 60)
    
    review_config = agents_config["agents"].get("review", {})
    review_md = load_agent_md("review")
    
    if review_config and review_md:
        prompt = f"""Based on REVIEW_AGENT.md rules:
{review_md[:500]}

Review recent code changes:
- Code quality check
- Test coverage validation (>80% required)
- Security audit
- Performance analysis
- Issue resolution validation

Approve or reject with feedback"""
        
        success, output = run_agent("review", prompt, model_routing, timeout_sec=900)
        results["agents_run"]["review"] = {"success": success, "output": output[:100]}
    
    # ========== SUMMARY ==========
    cycle_duration = time.time() - cycle_start
    
    log("\n" + "="*80)
    log("📊 Orchestration Cycle Summary")
    log("="*80)
    log(f"Duration: {cycle_duration:.2f}s")
    log(f"Agents Run: {len(results['agents_run'])}")
    
    success_count = sum(1 for r in results["agents_run"].values() if r.get("success"))
    log(f"Successful: {success_count}/{len(results['agents_run'])}")
    
    results["cycle_duration"] = cycle_duration
    results["cycle_end"] = datetime.now().isoformat()
    results["success"] = success_count > 0
    
    return results


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="🦅 BeermannCode Orchestrator v3.0 (CLI-Based)")
    ap.add_argument("--dry-run", action="store_true", help="Simulate without executing")
    ap.add_argument("--no-notify", action="store_true", help="Disable WhatsApp")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = ap.parse_args()
    
    global DRY_RUN, NOTIFY_ENABLED
    if args.dry_run:
        DRY_RUN = True
    if args.no_notify:
        NOTIFY_ENABLED = False
    
    log("🦅 BeermannCode Orchestrator v3.0 (CLI-Based)")
    log(f"Workspace: {WORKSPACE}")
    log(f"Dry-Run: {DRY_RUN}")
    log(f"Notifications: {NOTIFY_ENABLED}")
    
    if not acquire_lock():
        return 1
    
    try:
        results = run_orchestration_cycle()
        
        log("\n✅ Orchestration cycle completed")
        log(f"Result: {json.dumps(results, indent=2)[:200]}")
        
        return 0 if results.get("success") else 1
    
    except Exception as e:
        log(f"\n💥 Orchestration failed: {e}")
        import traceback
        log(traceback.format_exc())
        return 1
    
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
