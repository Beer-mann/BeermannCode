import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, render_template

from codeai_platform import CodeAIConfig, CodeAnalyzer, CodeReviewer, CodeGenerator
from codeai_platform.modules.generator import GenerationRequest

app = Flask(__name__)

# Orchestrator paths
WORKSPACE = Path("/home/shares/beermann")
LOG_FILE = WORKSPACE / "logs" / "orchestrator-v4.log"
LOG_FILE_V3 = WORKSPACE / "logs" / "orchestrator-v3.log"  # legacy
STATE_FILE = WORKSPACE / "logs" / "orchestrator-state.json"
TASK_QUEUE = WORKSPACE / "tasks" / "pending.jsonl"


LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "java": ".java",
    "cpp": ".cpp",
    "c": ".c",
    "csharp": ".cs",
    "go": ".go",
    "rust": ".rs",
}

config = CodeAIConfig(
    project_name="BeermannCode",
    supported_languages=list(LANGUAGE_EXTENSIONS.keys()),
)

analyzer = CodeAnalyzer(config)
reviewer = CodeReviewer(config)
generator = CodeGenerator(config)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """BeermannCode Orchestrator Dashboard"""
    return render_template("orchestrator_dashboard.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "BeermannCode"})


# ============================================================================
# ORCHESTRATOR DASHBOARD API
# ============================================================================

@app.route("/api/orchestrator/status")
def orchestrator_status():
    """Get current orchestrator status"""
    try:
        state = {}
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text())
        
        # Get last log lines
        logs = []
        if LOG_FILE.exists():
            logs = LOG_FILE.read_text().split('\n')[-20:]
        
        # Count tasks
        task_stats = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0
        }
        
        if TASK_QUEUE.exists():
            for line in TASK_QUEUE.read_text().split('\n'):
                if line.strip():
                    try:
                        task = json.loads(line)
                        status = task.get('status', 'unknown')
                        if status in task_stats:
                            task_stats[status] += 1
                    except:
                        pass
        
        return jsonify({
            "status": "ok",
            "last_cycle": state.get("last_cycle", {}),
            "last_run": state.get("last_run"),
            "logs": logs[-10:],  # Last 10 lines
            "tasks": task_stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orchestrator/logs")
def orchestrator_logs():
    """Get orchestrator logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        if LOG_FILE.exists():
            logs = LOG_FILE.read_text().split('\n')[-limit:]
            return jsonify({"logs": logs})
        return jsonify({"logs": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orchestrator/tasks")
def orchestrator_tasks():
    """Get task queue"""
    try:
        tasks = []
        # Check both old and new task files
        for task_file in [TASK_QUEUE, WORKSPACE / "tasks" / "done.jsonl"]:
            if task_file.exists():
                for line in task_file.read_text().split('\n'):
                    if line.strip():
                        try:
                            tasks.append(json.loads(line))
                        except:
                            pass
        
        # Group by status
        grouped = {}
        for task in tasks:
            status = task.get('status', 'completed')
            if status not in grouped:
                grouped[status] = []
            grouped[status].append(task)
        
        return jsonify({
            "total": len(tasks),
            "by_status": {k: len(v) for k, v in grouped.items()},
            "tasks": tasks[-30:]  # Last 30
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/orchestrator/ollama")
def orchestrator_ollama():
    """Check Ollama status"""
    try:
        import requests
        resp = requests.get("http://192.168.0.213:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            return jsonify({
                "status": "online",
                "models_count": len(models),
                "host": "192.168.0.213:11434"
            })
        return jsonify({"status": "error", "message": "Unexpected response"}), 500
    except Exception as e:
        return jsonify({"status": "offline", "error": str(e)}), 503


@app.route("/api/orchestrator/agents")
def orchestrator_agents():
    """Get CLI agent status (Aider, Codex, Claude, GitHub Copilot)"""
    import subprocess
    import shutil
    
    agents = {}
    
    # Aider
    aider_path = shutil.which("aider")
    if aider_path:
        try:
            version = subprocess.check_output(["aider", "--version"], stderr=subprocess.STDOUT, timeout=3, text=True).strip()
            agents["aider"] = {"status": "installed", "version": version, "path": aider_path}
        except:
            agents["aider"] = {"status": "installed", "version": "unknown", "path": aider_path}
    else:
        agents["aider"] = {"status": "not_installed"}
    
    # Codex CLI
    codex_path = shutil.which("codex")
    if codex_path:
        try:
            version = subprocess.check_output(["codex", "--version"], timeout=3, text=True).strip()
            agents["codex"] = {"status": "installed", "version": version, "path": codex_path}
        except:
            agents["codex"] = {"status": "installed", "version": "unknown", "path": codex_path}
    else:
        agents["codex"] = {"status": "not_installed"}
    
    # Claude CLI
    claude_path = shutil.which("claude")
    if claude_path:
        try:
            version = subprocess.check_output(["claude", "--version"], timeout=3, text=True).strip()
            agents["claude"] = {"status": "installed", "version": version, "path": claude_path}
        except:
            agents["claude"] = {"status": "installed", "version": "unknown", "path": claude_path}
    else:
        agents["claude"] = {"status": "not_installed"}
    
    # GitHub Copilot CLI (standalone)
    copilot_path = shutil.which("copilot")
    if copilot_path:
        try:
            version = subprocess.check_output(["copilot", "--version"], stderr=subprocess.STDOUT, timeout=3, text=True).strip()
            agents["copilot"] = {"status": "installed", "version": version, "path": copilot_path}
        except:
            agents["copilot"] = {"status": "installed", "version": "unknown", "path": copilot_path}
    else:
        agents["copilot"] = {"status": "not_installed"}
    
    return jsonify({"agents": agents, "total": len([a for a in agents.values() if a.get("status") == "installed"])})


@app.route("/api/orchestrator/v4/status")
def orchestrator_v4_status():
    """Get comprehensive v4 orchestrator status for dashboard."""
    try:
        sys.path.insert(0, str(WORKSPACE / "PROJECTS" / "BeermannCode"))
        from orchestrator_v4 import get_status_json
        return jsonify(get_status_json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/languages")
def languages():
    return jsonify({"languages": list(LANGUAGE_EXTENSIONS.keys())})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field"}), 400

    code = data["code"]
    language = data.get("language", "python")

    if language not in LANGUAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported language '{language}'. See /languages."}), 400

    ext = LANGUAGE_EXTENSIONS[language]

    with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = analyzer.analyze_file(tmp_path)
        if result is None:
            return jsonify({"error": "Could not analyze code for this language"}), 422
        d = result.to_dict()
        d.pop("file_path", None)
        return jsonify(d)
    finally:
        os.unlink(tmp_path)


@app.route("/review", methods=["POST"])
def review():
    data = request.get_json()
    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field"}), 400

    code = data["code"]
    language = data.get("language", "python")

    if language not in LANGUAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported language '{language}'. See /languages."}), 400

    result = reviewer.review_code(code, language)
    d = result.to_dict()
    d.pop("file_path", None)
    return jsonify(d)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data or "description" not in data:
        return jsonify({"error": "Missing 'description' field"}), 400

    language = data.get("language", "python")
    description = data["description"]
    function_name = data.get("function_name")
    args = data.get("args", [])
    include_comments = data.get("include_comments", True)
    include_tests = data.get("include_tests", False)

    if language not in LANGUAGE_EXTENSIONS:
        return jsonify({"error": f"Unsupported language '{language}'. See /languages."}), 400

    if function_name:
        code = generator.generate_function(function_name, args, "None", language)
        return jsonify({"code": code, "language": language, "description": description})

    req = GenerationRequest(
        language=language,
        description=description,
        style=config.generation_style,
        include_comments=include_comments,
        include_tests=include_tests,
    )
    result = generator.generate(req)
    return jsonify(result.to_dict())


if __name__ == "__main__":
    port = int(os.getenv("BEERMANNCODE_PORT", "5004"))
    app.run(host="0.0.0.0", port=port, debug=False)
