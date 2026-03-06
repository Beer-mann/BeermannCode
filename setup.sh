#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .venv/bin/activate ]; then python3 -m venv .venv; fi
. .venv/bin/activate
python -m pip install -U pip >/dev/null
if [ -f "requirements.txt" ]; then
  pip install -r "requirements.txt"
else
  pip install flask flask-cors requests python-dotenv
fi
