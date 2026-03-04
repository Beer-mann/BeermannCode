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


def choose_ollama_model(task_type: str) -> str:
    t = (task_type or "").lower()
    if t in {"review", "bugfix"}:
        return "deepseek-coder:6.7b"
    return "qwen2.5-coder:7b"


def ollama_generate_edit(model: str, project: Path, spec: str) -> dict[str, Any] | None:
    # Small context only: file list + first matching file content.
    files = [str(p.relative_to(project)) for p in project.rglob("*") if p.is_file() and p.suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".sh"} and ".git" not in str(p)]
    files = files[:80]
    target = files[0] if files else None
    content = ""
    if target:
        try:
            content = (project / target).read_text(encoding="utf-8", errors="ignore")[:12000]
        except Exception:
            content = ""

    system = (
        "Du bist ein Coding-Agent. Gib NUR valides JSON zurück: "
        "{\"summary\":\"...\",\"edits\":[{\"path\":\"rel/path\",\"content\":\"full file content\"}]}. "
        "Maximal 2 Dateien bearbeiten. Keine Markdown-Ausgabe."
    )
    user = f"Projekt: {project.name}\nTask: {spec}\nDateien (Auszug): {files[:30]}\nZieldatei: {target}\nAktueller Inhalt:\n{content}"

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
    run(["openclaw", "message", "action=send", "channel=whatsapp", f"target={WHATSAPP_TO}", f"message={msg}"])


def mark_done(task_id: str, model: str, status: str = "done") -> None:
    rows = read_all_rows()
    now = datetime.now().isoformat()
    for r in rows:
        if r.get("id") == task_id:
            r["status"] = status
            r["completed"] = now
            r["model"] = model
    save_tasks(rows)


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
        tasks = load_tasks()
        if args.project:
            tasks = [t for t in tasks if t.get("repo") == args.project]

        for t in tasks:
            task_id = t.get("id", "?")
            repo = t.get("repo", "")
            spec = t.get("spec", "")
            task_type = t.get("type", "implement")
            project = PROJECTS_DIR / repo
            if not project.exists():
                mark_done(task_id, "none", status="skipped")
                continue

            model = choose_ollama_model(task_type)
            log(f"[TASK] {task_id} {repo} -> {model}")
            if args.dry_run:
                mark_done(task_id, model)
                processed += 1
                continue

            result = ollama_generate_edit(model, project, spec)
            changed_files: list[str] = []
            if result:
                changed_files = apply_edits(project, result.get("edits", []))
                if changed_files:
                    ok, _ = commit_changes(project, task_id, result.get("summary", "implement"))
                    if ok:
                        mark_done(task_id, model)
                        changed_summary.append(f"{repo}: {', '.join(changed_files[:3])}")
                        processed += 1
                        continue

            # fallback to codex only if nothing changed
            ok, _ = run_codex_fallback(project, spec)
            if ok:
                mark_done(task_id, "codex/gpt-5.2-codex")
                changed_summary.append(f"{repo}: codex fallback changes")
                processed += 1
            else:
                log(f"[WARN] task {task_id} produced no changes")

        if changed_summary:
            send_whatsapp("🦅 BeermannCode Run fertig:\n" + "\n".join(f"• {x}" for x in changed_summary))
        else:
            send_whatsapp("🦅 BeermannCode Run fertig: Keine Änderungen in diesem Run.")

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
