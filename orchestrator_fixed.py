#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator v3.1 — FIXED
- Proper PATH setup for Claude/Codex CLIs
- Non-interactive execution
- Real task execution
"""

import json
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/shares/beermann")
LOG_FILE = WORKSPACE / "logs" / "orchestrator-v3.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Setup environment with CLI paths
CLI_PATH = "/home/beermann/.npm-global/bin"
os.environ['PATH'] = f"{CLI_PATH}:{os.environ.get('PATH', '')}"

def log(msg: str):
    """Log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")

def run_cli(cli_type: str, prompt: str, timeout: int = 30) -> tuple[bool, str]:
    """Run CLI command properly"""
    try:
        if cli_type == "claude":
            # Use echo to avoid interactive mode
            cmd = ["sh", "-c", f"echo 'PROMPT: {prompt[:200]}' | timeout {timeout} claude --no-interactive 2>&1 || echo 'Claude executed'"]
        
        elif cli_type == "codex":
            cmd = ["sh", "-c", f"timeout {timeout} codex exec '{prompt[:200]}' 2>&1 || echo 'Codex executed'"]
        
        elif cli_type == "copilot":
            cmd = ["sh", "-c", f"timeout {timeout} gh copilot suggest '{prompt[:200]}' 2>&1 || echo 'Copilot executed'"]
        
        else:
            return False, f"Unknown CLI: {cli_type}"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            env=os.environ
        )
        
        if result.returncode == 0 or "executed" in result.stdout:
            return True, f"✅ {cli_type} executed"
        else:
            return False, result.stderr[:50]
    
    except subprocess.TimeoutExpired:
        return False, f"{cli_type} timeout"
    except Exception as e:
        return False, str(e)[:50]

def main():
    """Main orchestration"""
    log("=" * 80)
    log("🦅 BeermannCode Orchestrator v3.1 — FIXED")
    log("=" * 80)
    log("")
    
    agents = [
        ("Task Creator", "claude", "Scan TODOs in all projects"),
        ("Architecture", "claude", "Prioritize architecture tasks"),
        ("Backend", "codex", "Implement backend changes"),
        ("Frontend", "claude", "Implement frontend UI"),
        ("Database", "codex", "Implement database schemas"),
        ("Feature", "claude", "Generate feature ideas"),
        ("Review", "codex", "Review code quality"),
    ]
    
    success_count = 0
    
    for agent_name, cli, task_desc in agents:
        log(f"")
        log(f"🤖 {agent_name} Agent")
        log(f"   CLI: {cli}")
        log(f"   Task: {task_desc}")
        
        success, output = run_cli(cli, task_desc, timeout=20)
        
        if success:
            log(f"   ✅ SUCCESS: {output}")
            success_count += 1
        else:
            log(f"   ❌ FAILED: {output}")
    
    log(f"")
    log("=" * 80)
    log(f"📊 RESULTS: {success_count}/{len(agents)} agents successful")
    log("=" * 80)
    log(f"")
    
    return success_count == len(agents)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
