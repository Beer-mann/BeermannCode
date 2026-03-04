#!/usr/bin/env python3
"""
BeermannCode Python Orchestrator (24/7)
- Queue-first
- Local Ollama first
- Codex fallback (optional)
- Git commit per successful task
- WhatsApp summary after each run
"""

from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request

WORKSPACE = Path("/home/shares/beermann")
PROJECTS_DIR = WORKSPACE / "PROJECTS"
TASK_FILE = WORKSPACE / "tasks" / "pending.jsonl"
LOG_FILE = WORKSPACE / "logs" / "coding-orchestrator.log"
LOCK_FILE = Path("/tmp/beermanncode-py.lock")
OLLAMA_BASE = os.getenv("OLLAMA_URL", "http://192.168.0.213:11434")
WHATSAPP_TO = os.getenv("WHATSAPP_TO", "+4917643995085")
CODEX_FALLBACK = os.getenv("CODEX_FALLBACK", "true").lower() == "true"
CHAIN_COOLDOWN_SEC = int(os.getenv("CHAIN_COOLDOWN_SEC", "45"))
DYNAMIC_CHAIN = os.getenv("DYNAMIC_CHAIN", "true").lower() == "true"
TASK_TIMEOUT_SEC = int(os.getenv("TASK_TIMEOUT_SEC", "120"))
MAX_LOCAL_ATTEMPTS = int(os.getenv("MAX_LOCAL_ATTEMPTS", "2"))
MAX_TASKS_PER_RUN = int(os.getenv("MAX_TASKS_PER_RUN", "4"))
AUTO_REFILL = os.getenv("AUTO_REFILL", "true").lower() == "true"
MIN_PENDING_TASKS = int(os.getenv("MIN_PENDING_TASKS", "8"))
LARGE_REPO_TIMEOUT_SEC = int(os.getenv("LARGE_REPO_TIMEOUT_SEC", "180"))


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    return p.returncode, out.strip()


def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)
            log(f"[SKIP] already running pid={pid}")
            return False
        except Exception:
            pass
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def load_tasks() -> list[dict[str, Any]]:
    if not TASK_FILE.exists():
        return []
    tasks = []
    for raw in TASK_FILE.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
            if d.get("status") == "pending":
                tasks.append(d)
        except Exception:
            continue
    pri = {"implement": 0, "todo_fix": 1, "bugfix": 2}
    tasks.sort(key=lambda t: pri.get((t.get("type") or "").lower(), 9))
    return tasks


def save_tasks(rows: list[dict[str, Any]]) -> None:
    TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASK_FILE.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n", encoding="utf-8")


def read_all_rows() -> list[dict[str, Any]]:
    if not TASK_FILE.exists():
        return []
    rows = []
    for raw in TASK_FILE.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except Exception:
            pass
    return rows


def choose_ollama_models(task_type: str) -> list[str]:
    t = (task_type or "").lower()
    if t in {"review", "bugfix"}:
        return ["deepseek-coder:6.7b", "qwen2.5-coder:7b"]
    return ["qwen2.5-coder:7b", "deepseek-coder:6.7b"]


def ollama_generate_edit(model: str, project: Path, spec: str, target_file: str = "", acceptance: str = "") -> dict[str, Any] | None:
    # Small context only: file list + first matching file content.
    files = [str(p.relative_to(project)) for p in project.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".sh"} and ".git" not in str(p)]
    files = files[:80]
    target = target_file or (files[0] if files else None)
    content = ""
    if target:
        try:
            content = (project / target).read_text(encoding="utf-8", errors="ignore")[:12000]
        except Exception:
            content = ""

    system = (
        "Du bist ein Coding-Agent. Gib NUR valides JSON zurück: "
        "{\"summary\":\"...\",\"edits\":[{\"path\":\"rel/path\",\"content\":\"full file content\"}]}. "
        "Maximal 2 Dateien bearbeiten. Mindestens 1 echte Änderung liefern. Keine Markdown-Ausgabe."
    )
    user = (
        f"Projekt: {project.name}\n"
        f"Task: {spec}\n"
        f"Akzeptanzkriterium: {acceptance or 'Mindestens eine funktionale Code-Änderung'}\n"
        f"Dateien (Auszug): {files[:30]}\n"
        f"Zieldatei (bevorzugt): {target}\n"
        f"Aktueller Inhalt:\n{content}"
    )

    # OpenAI-compatible endpoint first
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
        "max_tokens": 4000,
    }
    endpoints = [f"{OLLAMA_BASE}/v1/chat/completions", f"{OLLAMA_BASE}/api/chat"]

    for ep in endpoints:
        try:
            data = json.dumps(body if ep.endswith("completions") else {
                "model": model,
                "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            }).encode("utf-8")
            req = request.Request(ep, data=data, headers={"Content-Type": "application/json"})
            with request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read().decode("utf-8"))
            text = resp.get("choices", [{}])[0].get("message", {}).get("content") if ep.endswith("completions") else resp.get("message", {}).get("content", "")
            if not text:
                continue
            m = re.search(r"\{.*\}", text, re.S)
            raw = m.group(0) if m else text
            obj = json.loads(raw)
            if isinstance(obj, dict) and isinstance(obj.get("edits"), list):
                return obj
        except Exception:
            continue
    return None


def apply_edits(project: Path, edits: list[dict[str, str]]) -> list[str]:
    changed: list[str] = []
    for e in edits[:2]:
        rel = (e.get("path") or "").strip().lstrip("/")
        if not rel or ".." in rel:
            continue
        tgt = project / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        content = e.get("content") or ""
        if not isinstance(content, str) or not content.strip():
            continue
        prev = tgt.read_text(encoding="utf-8", errors="ignore") if tgt.exists() else None
        if prev == content:
            continue
        tgt.write_text(content, encoding="utf-8")
        changed.append(rel)
    return changed


def commit_changes(project: Path, task_id: str, summary: str) -> tuple[bool, str]:
    run(["git", "add", "-A"], cwd=project)
    code, out = run(["git", "commit", "-m", f"🦅 BeermannCode[{task_id}]: {summary[:80]}"], cwd=project)
    return code == 0, out


def run_codex_fallback(project: Path, spec: str) -> tuple[bool, str]:
    if not CODEX_FALLBACK:
        return False, "codex fallback disabled"
    code, out = run(["codex", "exec", "--full-auto", spec], cwd=project, timeout=600)
    if code != 0:
        return False, out
    ok, commit_out = commit_changes(project, "fallback", "codex fallback")
    return ok, commit_out


def send_whatsapp(msg: str) -> None:
    # Use supported CLI syntax
    run([
        "openclaw", "message", "send",
        "--channel", "whatsapp",
        "--target", WHATSAPP_TO,
        "--message", msg,
    ])


def mark_done(task_id: str, model: str, status: str = "done", reason: str = "") -> None:
    rows = read_all_rows()
    now = datetime.now().isoformat()
    for r in rows:
        if r.get("id") == task_id:
            r["status"] = status
            r["completed"] = now
            r["model"] = model
            if reason:
                r["reason"] = reason
    save_tasks(rows)


REPO_DEFAULTS = {
    "BCN": ("app.py", "CLI health check implementiert, Exit-Code 0/1 korrekt"),
    "BeermannAI": ("app.py", "Timeout+Retry aktiv und Fehler sauber behandelt"),
    "BeermannBot": ("app.py", "Command-Registry + unknown-command fallback vorhanden"),
    "BeermannCode": ("orchestrator.py", "Task-Metriken werden pro Run geschrieben"),
    "BeermannHN": ("app.py", "Duplikat-Filter verhindert doppelte News-Einträge"),
    "BeermannHub": ("app.py", "/health liefert valides JSON mit uptime/version"),
    "MegaRAG": ("rag_engine.py", "Chunking nutzt min/max + overlap konfigurierbar"),
    "Routenplaner": ("server.js", "Fallback-Route wird bei OSRM-Fehler genutzt"),
    "TradingBot": ("main.py", "Risk-Guard limitiert daily loss + open positions"),
    "VoiceOpsAI": ("src/pipeline.js", "Audio-Validation prüft format/duration/size"),
}


def enrich_task_defaults(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure each task has concrete target_file + acceptance criteria."""
    changed = False
    for t in tasks:
        repo = t.get("repo", "")
        d_target, d_acc = REPO_DEFAULTS.get(repo, ("app.py", "Mindestens 1 funktionale Code-Änderung"))
        if not t.get("target_file"):
            t["target_file"] = d_target
            changed = True
        if not t.get("acceptance"):
            t["acceptance"] = d_acc
            changed = True
    if changed:
        # persist enriched metadata back to queue file
        rows = read_all_rows()
        by_id = {t.get("id"): t for t in tasks}
        for r in rows:
            tid = r.get("id")
            if tid in by_id and r.get("status") == "pending":
                r["target_file"] = by_id[tid].get("target_file")
                r["acceptance"] = by_id[tid].get("acceptance")
        save_tasks(rows)
    return tasks


def task_timeout_for_repo(repo: str) -> int:
    # Heavier repos get slightly more runtime budget
    if repo in {"TradingBot", "VoiceOpsAI", "Routenplaner", "MegaRAG", "BeermannAI"}:
        return LARGE_REPO_TIMEOUT_SEC
    return TASK_TIMEOUT_SEC


def split_failed_task(task: dict[str, Any]) -> int:
    """Create two smaller follow-up tasks for a failed broad task."""
    if task.get("split_generated"):
        return 0
    rows = read_all_rows()
    now = datetime.now().isoformat()
    base_repo = task.get("repo", "")
    base_target = task.get("target_file", "app.py")
    base_spec = task.get("spec", "Implementiere die Aufgabe")
    base_acc = task.get("acceptance", "Mindestens 1 funktionale Änderung")

    subtasks = [
        {
            "id": os.urandom(4).hex(),
            "status": "pending",
            "type": "implement",
            "repo": base_repo,
            "spec": f"Teil 1/2: Refactor vorbereiten für {base_spec}",
            "target_file": base_target,
            "acceptance": f"Teil 1 erfüllt: {base_acc}",
            "created": now,
            "parent_task": task.get("id"),
        },
        {
            "id": os.urandom(4).hex(),
            "status": "pending",
            "type": "implement",
            "repo": base_repo,
            "spec": f"Teil 2/2: Feature abschließen für {base_spec}",
            "target_file": base_target,
            "acceptance": f"Teil 2 erfüllt: {base_acc}",
            "created": now,
            "parent_task": task.get("id"),
        },
    ]

    # mark parent to avoid repeated splitting
    for r in rows:
        if r.get("id") == task.get("id"):
            r["split_generated"] = True
    rows.extend(subtasks)
    save_tasks(rows)
    return len(subtasks)


def auto_refill_queue(min_pending: int = MIN_PENDING_TASKS) -> int:
    rows = read_all_rows()
    pending = [r for r in rows if r.get("status") == "pending"]
    missing = max(0, min_pending - len(pending))
    if missing == 0:
        return 0

    now = datetime.now().isoformat()
    seeded = 0
    for repo, (target, acceptance) in REPO_DEFAULTS.items():
        if seeded >= missing:
            break
        rows.append({
            "id": os.urandom(4).hex(),
            "status": "pending",
            "type": "implement",
            "repo": repo,
            "spec": f"Implementiere eine kleine, produktive Verbesserung in {target} gemäß Akzeptanzkriterium.",
            "target_file": target,
            "acceptance": acceptance,
            "created": now,
        })
        seeded += 1

    save_tasks(rows)
    return seeded


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, default=3)
    ap.add_argument("--project", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not acquire_lock():
        return 0

    changed_summary: list[str] = []
    processed = 0
    try:
        if AUTO_REFILL:
            seeded = auto_refill_queue(MIN_PENDING_TASKS)
            if seeded:
                log(f"[REFILL] added {seeded} new tasks to queue")

        tasks = load_tasks()
        if args.project:
            tasks = [t for t in tasks if t.get("repo") == args.project]
        tasks = enrich_task_defaults(tasks)

        failed_summary: list[str] = []
        for idx, t in enumerate(tasks, start=1):
            if idx > MAX_TASKS_PER_RUN:
                log(f"[LIMIT] reached MAX_TASKS_PER_RUN={MAX_TASKS_PER_RUN}, remaining queued")
                break
            task_started = time.time()
            task_id = t.get("id", "?")
            repo = t.get("repo", "")
            spec = t.get("spec", "")
            task_type = t.get("type", "implement")
            target_file = t.get("target_file", "")
            acceptance = t.get("acceptance", "")
            project = PROJECTS_DIR / repo
            if not project.exists():
                mark_done(task_id, "none", status="skipped", reason="project_not_found")
                continue

            models = choose_ollama_models(task_type)
            log(f"[TASK] {task_id} {repo} -> {models[0]} (alt: {models[1]}) target={target_file or '-'}")
            if args.dry_run:
                mark_done(task_id, models[0])
                processed += 1
                continue

            changed_files: list[str] = []
            used_model = None
            attempts = 0
            task_timeout = task_timeout_for_repo(repo)
            for model in models:
                if attempts >= MAX_LOCAL_ATTEMPTS:
                    break
                if time.time() - task_started > task_timeout:
                    log(f"[TIMEOUT] task {task_id} exceeded {task_timeout}s")
                    break
                attempts += 1
                result = ollama_generate_edit(model, project, spec, target_file=target_file, acceptance=acceptance)
                if not result:
                    continue
                changed_files = apply_edits(project, result.get("edits", []))
                if changed_files:
                    ok, _ = commit_changes(project, task_id, result.get("summary", "implement"))
                    if ok:
                        used_model = model
                        break

            if used_model:
                mark_done(task_id, used_model)
                changed_summary.append(f"{repo}: {', '.join(changed_files[:3])}")
                processed += 1
                continue

            # fallback to codex only if local attempts produced no changes
            ok, _ = run_codex_fallback(project, spec)
            if ok:
                mark_done(task_id, "codex/gpt-5.2-codex")
                changed_summary.append(f"{repo}: codex fallback changes")
                processed += 1
            else:
                mark_done(task_id, "none", status="failed", reason="no_changes_after_local_and_fallback")
                spawned = split_failed_task(t)
                failed_summary.append(f"{repo} ({task_id})")
                log(f"[WARN] task {task_id} failed: no changes after local+fallback")
                if spawned:
                    log(f"[SPLIT] task {task_id} -> {spawned} subtasks")

        if changed_summary:
            msg = "🦅 BeermannCode Run fertig:\n" + "\n".join(f"• {x}" for x in changed_summary)
            if failed_summary:
                msg += "\n⚠️ Ohne Änderungen: " + ", ".join(failed_summary[:5])
            send_whatsapp(msg)
        else:
            msg = "🦅 BeermannCode Run fertig: Keine Änderungen in diesem Run."
            if failed_summary:
                msg += "\n⚠️ Fehlgeschlagen: " + ", ".join(failed_summary[:5])
            send_whatsapp(msg)

        # dynamic chain
        if DYNAMIC_CHAIN:
            pending_left = len(load_tasks())
            if pending_left > 0:
                log(f"[CHAIN] pending={pending_left}, next run in {CHAIN_COOLDOWN_SEC}s")
                subprocess.Popen([
                    "bash", "-lc",
                    f"sleep {CHAIN_COOLDOWN_SEC}; python3 /home/shares/beermann/PROJECTS/BeermannCode/orchestrator.py --tier {args.tier} >/dev/null 2>&1"
                ])

        log(f"[DONE] processed={processed}")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
