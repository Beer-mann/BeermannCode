#!/usr/bin/env python3
"""
Simple Project Agent Runner - spawns Claude/Codex/Copilot for all projects
No legacy Aider code, just direct CLI calls
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (
    PROJECTS_DIR,
    log,
    spawn_project_agent,
    send_whatsapp
)

def main():
    log("🦅 BeermannCode - Project Agents")
    log("=" * 60)
    
    # Find all GitHub projects
    projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir() or not (project_dir / ".git").exists():
            continue
        if project_dir.name == "BeermannCode":
            continue  # Don't work on self
        projects.append(project_dir.name)
    
    log(f"Found {len(projects)} projects: {', '.join(projects)}")
    
    # Determine task for each project
    for project_name in projects:
        project_dir = PROJECTS_DIR / project_name
        
        # Check if has UI
        has_ui = False
        ui_patterns = ["**/index.html", "**/templates/*.html", "**/static/*.html", 
                      "**/public/*.html", "**/frontend/**/*.html", "**/ui/**/*.html"]
        for pattern in ui_patterns:
            if any(project_dir.glob(pattern)):
                has_ui = True
                break
        
        # Check if has tests
        has_tests = (project_dir / "tests").exists() or (project_dir / "test").exists()
        
        # Determine task type
        if not has_ui:
            task_type = "ui"
        elif not has_tests:
            task_type = "tests"
        else:
            task_type = "improve"
        
        log(f"\n[{project_name}] Task: {task_type}")
        
        # Spawn agent
        success, output = spawn_project_agent(project_name, task_type)
        
        if success:
            log(f"✅ [{project_name}] Agent completed")
        else:
            log(f"❌ [{project_name}] Agent failed: {output[:200]}")
    
    # Summary
    send_whatsapp("🦅 BeermannCode Project Agents completed!\n\nCheck GitHub for PRs.")
    log("\n✅ All project agents completed")

if __name__ == "__main__":
    main()
