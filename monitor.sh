#!/bin/bash
# 🦅 BeermannCode Live Monitor
# Zeigt Logs, Prozesse und Status

echo "🦅 BeermannCode Orchestrator — Live Monitor"
echo "==========================================="
echo ""

echo "⏱️  Zeit:"
date

echo ""
echo "📊 Prozess Status:"
ps aux | grep orchestrator_v3.py | grep -v grep || echo "❌ Nicht aktiv"

echo ""
echo "📋 Letzte 30 Log-Einträge:"
tail -30 /home/shares/beermann/logs/orchestrator-v3.log 2>/dev/null | head -30

echo ""
echo "📈 Statistische Zusammenfassung (Log):"
echo "  Erfolgreiche Runs: $(grep -c "✅" /home/shares/beermann/logs/orchestrator-v3.log 2>/dev/null || echo "0")"
echo "  Fehler: $(grep -c "ERROR\|FAILED" /home/shares/beermann/logs/orchestrator-v3.log 2>/dev/null || echo "0")"
echo "  Timeouts: $(grep -c "TIMEOUT" /home/shares/beermann/logs/orchestrator-v3.log 2>/dev/null || echo "0")"

echo ""
echo "📅 Crons (aktiviert):"
crontab -l 2>/dev/null | grep -A 3 "BeermannCode"

echo ""
echo "💾 Speicher & CPU:"
free -h | grep Mem | awk '{printf "  Memory: %s / %s\n", $3, $2}'
uptime | awk '{print "  Load: " $10 ", " $11 ", " $12}'

echo ""
echo "🔍 Nächste geplante Runs:"
echo "  (Automatisch via cron)"
echo "  - Daytime: */10 6-22 * * *"
echo "  - Nighttime: */15 23-5 * * *"
echo "  - Daily Report: 0 18 * * *"

echo ""
echo "✅ Alles läuft! 🚀"
