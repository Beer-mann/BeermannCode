#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip >/dev/null
if [ -f "requirements.txt" ]; then
  pip install -r "requirements.txt"
else
  pip install flask flask-cors requests python-dotenv
fi
