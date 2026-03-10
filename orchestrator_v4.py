#!/usr/bin/env python3
"""
🦅 BeermannCode Orchestrator v4 — WIRKLICH CODEND
- Findet echte TODOs/FIXMEs in Projekten
- Lässt Claude/Codex den Fix schreiben (direkt in Dateien)
- Committed automatisch zu Git
"""

import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/shares/beermann")
PROJECTS_DIR = WORKSPACE / "PROJECTS"
LOG_FILE = WORKSPACE / "logs" / "orchestrator-v4.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full = f"[{timestamp}] {msg}"
    print(full)
    with open(LOG_FILE, "a") as f:
        f.write(full + "\n")

def run(cmd: list, cwd=None, timeout=120) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out[:500]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:100]

def find_todos(project_path: Path) -> list[dict]:
    """Finde echte TODOs/FIXMEs in einem Projekt"""
    todos = []
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py",
             "--exclude-dir=.venv", "--exclude-dir=venv",
             "--exclude-dir=node_modules", "--exclude-dir=__pycache__",
             "-E", "TODO|FIXME|HACK|XXX", str(project_path)],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n")[:5]:  # Max 5 pro Projekt
            if ":" in line and line.strip():
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    todos.append({
                        "file": parts[0],
                        "line": parts[1],
                        "content": parts[2].strip()
                    })
    except:
        pass
    return todos

def claude_fix_file(filepath: str, todo_content: str, project_path: Path) -> tuple[bool, str]:
    """Lass Claude eine Datei direkt fixen"""
    prompt = f"""Fix this TODO/FIXME in {filepath}:
{todo_content}

Write the fix directly. Be concise."""
    
    ok, out = run(
        ["claude", "--print", "--dangerously-skip-permissions", prompt],
        cwd=str(project_path)
    )
    return ok, out

def codex_fix_file(filepath: str, todo_content: str, project_path: Path) -> tuple[bool, str]:
    """Lass Codex eine Datei direkt fixen"""
    prompt = f"In {filepath}, fix this TODO: {todo_content}. Write and apply the fix directly to the file."
    
    ok, out = run(
        ["codex", "exec", prompt],
        cwd=str(project_path),
        timeout=60
    )
    return ok, out

def git_commit(project_path: Path, message: str) -> bool:
    """Commit Änderungen"""
    run(["git", "add", "-A"], cwd=str(project_path))
    ok, out = run(["git", "commit", "-m", message], cwd=str(project_path))
    if ok:
        log(f"   📦 Committed: {message}")
    return ok

def process_project(project_path: Path, agent_turn: int) -> int:
    """Verarbeite ein Projekt — gibt Anzahl gelöster Tasks zurück"""
    project_name = project_path.name
    todos = find_todos(project_path)
    
    if not todos:
        log(f"   ✅ {project_name}: Keine TODOs gefunden")
        return 0
    
    log(f"   📋 {project_name}: {len(todos)} TODOs gefunden")
    fixed = 0
    
    for todo in todos[:2]:  # Max 2 Fixes pro Projekt pro Run
        log(f"   🔧 Fix: {todo['file']}:{todo['line']} — {todo['content'][:60]}")
        
        # Abwechselnd Claude und Codex
        if agent_turn % 2 == 0:
            ok, out = claude_fix_file(todo["file"], todo["content"], project_path)
            agent_used = "Claude"
        else:
            ok, out = codex_fix_file(todo["file"], todo["content"], project_path)
            agent_used = "Codex"
        
        if ok:
            log(f"   ✅ {agent_used} hat gefixt")
            fixed += 1
        else:
            log(f"   ⚠️ {agent_used} fehlgeschlagen: {out[:80]}")
    
    if fixed > 0:
        git_commit(project_path, f"🦅 BeermannCode: {fixed} TODOs gefixt in {project_name}")
    
    return fixed

def main():
    log("=" * 70)
    log("🦅 BeermannCode Orchestrator v4 — Echte Code-Änderungen")
    log("=" * 70)
    
    projects = sorted([p for p in PROJECTS_DIR.iterdir() if p.is_dir() and (p / ".git").exists()])
    
    if not projects:
        log("❌ Keine Projekte gefunden!")
        return
    
    log(f"📁 {len(projects)} Projekte gefunden")
    
    total_fixed = 0
    
    for i, project in enumerate(projects):
        log(f"\n🔍 Projekt: {project.name}")
        fixed = process_project(project, agent_turn=i)
        total_fixed += fixed
    
    log("")
    log("=" * 70)
    log(f"📊 GESAMT: {total_fixed} TODOs gefixt und committed!")
    log("=" * 70)

if __name__ == "__main__":
    main()
