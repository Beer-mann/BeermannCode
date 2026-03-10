#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator — OAuth (REAL)
Nutzt CLIs die du SCHON authentifiziert hast.
Keine API Keys, keine Fake-Outputs.
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/shares/beermann")
LOG_FILE = WORKSPACE / "logs" / "orchestrator-oauth.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")

def run_agent(agent_name: str, cli: str, prompt: str) -> tuple[bool, str]:
    """Run agent via OAuth-authenticated CLI"""
    try:
        if cli == "claude":
            cmd = ["claude", "--print", prompt]
        elif cli == "codex":
            cmd = ["codex", "exec", prompt]
        elif cli == "gh":
            cmd = ["gh", "copilot", "suggest", "--target", "shell", prompt]
        else:
            return False, f"Unknown CLI: {cli}"
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Real check: Did it produce output?
        if result.stdout.strip():
            return True, result.stdout[:300]
        elif result.returncode == 0:
            return True, "(executed successfully)"
        else:
            return False, result.stderr[:100]
    
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except FileNotFoundError:
        return False, f"{cli} not found"
    except Exception as e:
        return False, str(e)[:50]

def main():
    log("=" * 80)
    log("🦅 BeermannCode Orchestrator — OAuth Mode")
    log("=" * 80)
    log("")
    
    agents = [
        ("Task Creator", "claude", "Scan all Python files in /home/shares/beermann/PROJECTS for TODOs and FIXMEs. List top 5."),
        ("Architecture", "claude", "Design system architecture improvements for a multi-project coding platform. Be concise."),
        ("Backend", "codex", "Write FastAPI backend code for a REST API with auth and database"),
        ("Frontend", "claude", "Write React component for a project management dashboard. Show code."),
        ("Database", "codex", "Write SQLAlchemy models and migrations for a coding platform"),
        ("Feature", "claude", "Brainstorm 3 new features for a 24/7 coding orchestrator. Be specific."),
        ("Review", "codex", "Review code quality, security issues and test coverage in Python projects"),
    ]
    
    success = 0
    
    for agent_name, cli, prompt in agents:
        log(f"🤖 {agent_name} ({cli})")
        
        ok, output = run_agent(agent_name, cli, prompt)
        
        if ok:
            log(f"   ✅ SUCCESS: {output}")
            success += 1
        else:
            log(f"   ❌ FAILED: {output}")
    
    log("")
    log(f"📊 RESULTS: {success}/{len(agents)} successful")
    log("=" * 80)

if __name__ == "__main__":
    main()
