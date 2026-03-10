#!/usr/bin/env python3
"""
WhatsApp Notifier für BeermannCode Orchestrator
- Event-basiert: Nur wichtige Events (Fehler/Erfolg)
- Täglicher Summary: 18:00 Uhr
"""

import json
import sys
from pathlib import Path
from datetime import datetime

WORKSPACE = Path("/home/shares/beermann")
LOG_FILE = WORKSPACE / "logs" / "orchestrator-v3.log"
STATE_FILE = WORKSPACE / "logs" / "orchestrator-state.json"
TASK_QUEUE = WORKSPACE / "tasks" / "pending.jsonl"
NOTIFICATION_LOG = WORKSPACE / "logs" / "whatsapp-notifications.log"

# WhatsApp-Nummer
WHATSAPP_TO = "+4917643995085"


def log_notification(event_type: str, message: str):
    """Log notification"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    NOTIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFICATION_LOG, "a") as f:
        f.write(f"[{timestamp}] [{event_type}] {message[:100]}\n")


def parse_last_cycle():
    """Get last orchestrator cycle data"""
    if not STATE_FILE.exists():
        return None
    
    try:
        return json.loads(STATE_FILE.read_text())
    except:
        return None


def extract_events_from_logs():
    """Extract important events from logs"""
    events = {"errors": [], "successes": [], "timeouts": []}
    
    if not LOG_FILE.exists():
        return events
    
    last_lines = LOG_FILE.read_text().split('\n')[-30:]  # Last 30 lines
    
    for line in last_lines:
        if "❌ ALL MODELS FAILED" in line:
            # Extract agent name
            parts = line.split('|')
            if len(parts) >= 2:
                agent = parts[0].replace('[AGENT]', '').strip()
                events["errors"].append(agent)
        
        elif "✅" in line and "[AGENT]" in line:
            parts = line.split('|')
            if len(parts) >= 2:
                agent = parts[0].replace('[AGENT]', '').strip()
                events["successes"].append(agent)
        
        elif "TIMEOUT" in line:
            parts = line.split('|')
            if len(parts) >= 2:
                agent = parts[0].replace('[AGENT]', '').strip()
                events["timeouts"].append(agent)
    
    return events


def send_event_notification():
    """Send WhatsApp notification for important events"""
    events = extract_events_from_logs()
    
    if not events["errors"] and not events["timeouts"]:
        return  # No important events
    
    message = "🚨 *BeermannCode Alert*\n\n"
    
    if events["errors"]:
        message += "❌ *Failed Agents:*\n"
        for agent in set(events["errors"]):
            message += f"  • {agent}\n"
    
    if events["timeouts"]:
        message += "\n⏱️ *Timeouts:*\n"
        for agent in set(events["timeouts"]):
            message += f"  • {agent}\n"
    
    message += "\nℹ️ Check dashboard: http://localhost:5004/dashboard"
    
    # Send via message tool
    import subprocess
    cmd = [
        "python3", "-m", "openclaw.tools.message",
        "--action", "send",
        "--channel", "whatsapp",
        "--to", WHATSAPP_TO,
        "--message", message
    ]
    
    try:
        subprocess.run(cmd, timeout=10)
        log_notification("EVENT", f"Sent: {len(events['errors'])} errors, {len(events['timeouts'])} timeouts")
    except Exception as e:
        log_notification("ERROR", str(e)[:100])


def send_daily_summary():
    """Send WhatsApp daily summary at 18:00"""
    cycle = parse_last_cycle()
    
    if not cycle:
        return
    
    # Count stats from logs
    log_content = LOG_FILE.read_text() if LOG_FILE.exists() else ""
    success_count = log_content.count("✅")
    error_count = log_content.count("❌")
    
    # Count tasks
    pending = 0
    completed = 0
    failed = 0
    
    if TASK_QUEUE.exists():
        for line in TASK_QUEUE.read_text().split('\n'):
            if line.strip():
                try:
                    task = json.loads(line)
                    status = task.get('status', 'unknown')
                    if status == 'completed':
                        completed += 1
                    elif status == 'failed':
                        failed += 1
                    elif status == 'pending':
                        pending += 1
                except:
                    pass
    
    # Build message
    message = "📋 *BeermannCode — Tagesbericht*\n\n"
    message += f"✅ *Erfolg:* {success_count} Operationen\n"
    message += f"❌ *Fehler:* {error_count}\n"
    message += f"⏱️ *Timeouts:* {cycle.get('timeouts', 0)}\n\n"
    message += f"📊 *Tasks:*\n"
    message += f"  • Abgeschlossen: {completed}\n"
    message += f"  • Offen: {pending}\n"
    message += f"  • Fehlgeschlagen: {failed}\n\n"
    
    agents_run = cycle.get('agents_run', {})
    if agents_run:
        success_agents = sum(1 for a in agents_run.values() if a.get('success'))
        message += f"🤖 *Agenten:* {success_agents}/{len(agents_run)} erfolgreich\n"
    
    message += f"\n🌐 Dashboard: http://localhost:5004/dashboard"
    
    # Send via message tool
    import subprocess
    cmd = [
        "python3", "-m", "openclaw.tools.message",
        "--action", "send",
        "--channel", "whatsapp",
        "--to", WHATSAPP_TO,
        "--message", message
    ]
    
    try:
        subprocess.run(cmd, timeout=10)
        log_notification("SUMMARY", "Daily summary sent")
    except Exception as e:
        log_notification("ERROR", str(e)[:100])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 whatsapp_notifier.py [event|summary]")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "event":
        send_event_notification()
    elif mode == "summary":
        send_daily_summary()
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
