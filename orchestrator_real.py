#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator — REAL & FUNCTIONAL
Nutzt NUR was ECHTE funktioniert: OpenAI Codex API
Kein Fake-Status, keine Lügen.
"""

import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/shares/beermann")
LOG_FILE = WORKSPACE / "logs" / "orchestrator-real.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not OPENAI_API_KEY:
    print("❌ ERROR: OPENAI_API_KEY not set!")
    exit(1)

def log(msg: str):
    """Log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")

def call_codex(prompt: str, max_tokens: int = 500) -> tuple[bool, str]:
    """Call OpenAI Codex API - REAL execution"""
    try:
        import subprocess
        
        # Use curl to call OpenAI API directly
        cmd = [
            "curl", "-s",
            "https://api.openai.com/v1/chat/completions",
            "-H", f"Authorization: Bearer {OPENAI_API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7
            })
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            
            # Check if API call was successful
            if "error" in response:
                return False, f"API Error: {response['error'].get('message', 'unknown')}"
            
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                return True, content
            else:
                return False, "No response from API"
        else:
            return False, result.stderr[:100]
    
    except subprocess.TimeoutExpired:
        return False, "Timeout (30s)"
    except json.JSONDecodeError:
        return False, "Invalid JSON response"
    except Exception as e:
        return False, str(e)[:100]

def main():
    """Main orchestration - REAL"""
    log("=" * 80)
    log("🦅 BeermannCode Orchestrator — REAL")
    log("=" * 80)
    log("")
    
    agents = [
        ("Task Creator", "Scan all projects for TODOs, FIXMEs, missing tests, and documentation gaps. Return top 5 tasks."),
        ("Architecture", "Review the task list and prioritize by impact. Suggest which tasks to focus on first."),
        ("Backend", "Given the tasks, suggest Python backend improvements: API endpoints, database schemas, utilities."),
        ("Frontend", "Suggest React/Vue UI components needed. Include state management and routing."),
        ("Database", "Design database schemas for the suggested features. Include indices and relationships."),
        ("Feature", "Generate creative feature ideas for the project. Consider user experience and market trends."),
        ("Review", "Review the proposed changes and identify potential issues: security, performance, testing coverage."),
    ]
    
    success_count = 0
    results = []
    
    for agent_name, task in agents:
        log("")
        log(f"🤖 {agent_name} Agent")
        log(f"   Task: {task[:60]}...")
        
        success, output = call_codex(task, max_tokens=300)
        
        if success:
            log(f"   ✅ SUCCESS")
            log(f"   Output: {output[:200]}...")
            success_count += 1
            results.append({
                "agent": agent_name,
                "status": "success",
                "output": output[:500]
            })
        else:
            log(f"   ❌ FAILED: {output}")
            results.append({
                "agent": agent_name,
                "status": "failed",
                "error": output
            })
    
    log("")
    log("=" * 80)
    log(f"📊 RESULTS: {success_count}/{len(agents)} agents successful")
    log("=" * 80)
    
    # Save results
    state_file = WORKSPACE / "logs" / "orchestrator-state.json"
    with open(state_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "success_count": success_count,
            "total_agents": len(agents),
            "results": results
        }, f, indent=2)
    
    return success_count == len(agents)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
