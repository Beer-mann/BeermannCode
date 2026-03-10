#!/bin/bash
# 🦅 BeermannCode Orchestrator mit WhatsApp Notifications
# - Event-basiert: Fehler/Erfolg
# - Daily Summary: 18:00 Uhr

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRATOR="$SCRIPT_DIR/orchestrator_v3.py"
NOTIFIER="$SCRIPT_DIR/whatsapp_notifier.py"
LOG_FILE="/home/shares/beermann/logs/orchestrator-v3.log"

# Run orchestrator
python3 "$ORCHESTRATOR"

# After orchestrator completes, send event-based notification
if [ -f "$NOTIFIER" ]; then
    python3 "$NOTIFIER" event 2>/dev/null &
fi

# Check if it's 18:00 (daily summary time)
HOUR=$(date +%H)
if [ "$HOUR" = "18" ]; then
    sleep 2
    python3 "$NOTIFIER" summary 2>/dev/null &
fi

exit 0
