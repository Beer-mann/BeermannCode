#!/bin/bash
# Quick Agent Run - Aider auf BeermannCode
# Führt einen einzelnen Agent-Task aus

set -euo pipefail

export OLLAMA_API_BASE=http://192.168.0.213:11434

PROJECT="/home/shares/beermann/PROJECTS/BeermannCode"
TASK="${1:-Analyze the improvements.md file and implement the first TODO item}"

echo "🦅 Running Aider on BeermannCode..."
echo "Task: $TASK"

cd "$PROJECT"

aider \
    --model ollama/qwen2.5-coder:7b \
    --env-file /home/beermann/.aider.env \
    --yes-always \
    --auto-commits \
    --no-show-model-warnings \
    --message "$TASK" \
    improvements.md

echo "✅ Agent run complete"

# Auto-push
if git remote get-url origin &>/dev/null; then
    git push
    echo "📤 Pushed to GitHub"
fi
