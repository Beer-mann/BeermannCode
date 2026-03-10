#!/bin/bash
# 🦅 BeermannCode Cron Setup Script
# Configures 24/7 orchestration via OpenClaw crons

set -e

ORCHESTRATOR_PATH="/home/shares/beermann/PROJECTS/BeermannCode/orchestrator.py"
PROJECT_DIR="/home/shares/beermann/PROJECTS/BeermannCode"

echo "🦅 Setting up BeermannCode crons..."
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if orchestrator exists
if [ ! -f "$ORCHESTRATOR_PATH" ]; then
    echo -e "${RED}❌ Error: orchestrator.py not found at $ORCHESTRATOR_PATH${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Checking existing crons...${NC}"
openclaw cron list | grep -E "coding|beer" || echo "No existing BeermannCode crons"

echo ""
echo -e "${BLUE}➕ Adding new crons...${NC}"
echo ""

# Cron 1: Day-time (06:00-22:00, every 10 minutes)
echo -e "${BLUE}1️⃣  Daytime Cron (06:00-22:00, every 10 min)${NC}"
echo "   Command: python3 orchestrator.py"
echo "   Schedule: */10 6-22 * * *"
echo ""

openclaw cron new \
    --name "beermanncode-day" \
    --schedule "*/10 6-22 * * *" \
    --command "cd ${PROJECT_DIR} && python3 orchestrator.py" \
    2>&1 | grep -i "created\|error\|exists" || echo "   ✓ Configured"

echo ""

# Cron 2: Night-time Feature Agent (23:00-05:00, every 15 minutes)
echo -e "${BLUE}2️⃣  Night-time Cron (23:00-05:00, every 15 min, Feature Agent only)${NC}"
echo "   Command: python3 orchestrator.py --agent feature"
echo "   Schedule: */15 23-5 * * *"
echo ""

openclaw cron new \
    --name "beermanncode-night" \
    --schedule "*/15 23-5 * * *" \
    --command "cd ${PROJECT_DIR} && python3 orchestrator.py --agent feature" \
    2>&1 | grep -i "created\|error\|exists" || echo "   ✓ Configured"

echo ""

# Cron 3: Daily Summary Report (18:00)
echo -e "${BLUE}3️⃣  Daily Summary Report (18:00)${NC}"
echo "   Command: python3 orchestrator.py (full cycle)"
echo "   Schedule: 0 18 * * *"
echo ""

openclaw cron new \
    --name "beermanncode-report-18" \
    --schedule "0 18 * * *" \
    --command "cd ${PROJECT_DIR} && python3 orchestrator.py" \
    2>&1 | grep -i "created\|error\|exists" || echo "   ✓ Configured"

echo ""
echo -e "${GREEN}✅ Cron setup complete!${NC}"
echo ""

# List all crons
echo -e "${BLUE}📋 Active BeermannCode Crons:${NC}"
echo ""
openclaw cron list | grep -E "beermanncode|coding" || echo "No crons found (check OpenClaw setup)"

echo ""
echo -e "${BLUE}ℹ️  What happens now:${NC}"
echo ""
echo "  🕕 06:00-22:00  → Every 10 minutes"
echo "     Architecture + Backend + Frontend + Database + Feature + Review"
echo ""
echo "  🌙 23:00-05:00  → Every 15 minutes"
echo "     Feature Agent only (low-priority continuous proposals)"
echo ""
echo "  📊 18:00        → Daily"
echo "     Full cycle + WhatsApp summary"
echo ""
echo -e "${GREEN}🚀 BeermannCode is now 24/7 automated!${NC}"
echo ""
echo "Logs: /home/shares/beermann/logs/orchestrator-v2.log"
echo "Tasks: /home/shares/beermann/tasks/pending.jsonl"
