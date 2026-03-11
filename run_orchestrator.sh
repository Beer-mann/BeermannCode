#!/bin/bash
# BeermannCode Orchestrator Runner
# Wird via Cron alle 30 Minuten ausgeführt

set -euo pipefail

cd /home/shares/beermann/PROJECTS/BeermannCode

# Environment
export AUTO_PUSH=true
export AUTO_COMMIT=true
export NOTIFY_ENABLED=true
export WHATSAPP_TO="+4917643995085"

# Log file
LOG_FILE="/home/shares/beermann/logs/orchestrator-cron.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] Starting BeermannCode Orchestrator..." >> "$LOG_FILE"

# Run orchestrator
python3 orchestrator.py >> "$LOG_FILE" 2>&1

echo "[$(date)] Orchestrator run complete" >> "$LOG_FILE"
