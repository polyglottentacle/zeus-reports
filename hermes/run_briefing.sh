#!/usr/bin/env bash
# Wrapper per cron — carica .env e lancia briefing.py
# Posizionato su Hermes in /opt/zeus/hermes/run_briefing.sh
set -a
source "$(dirname "$0")/.env"
set +a
exec "$(dirname "$0")/../.venv/bin/python3" "$(dirname "$0")/briefing.py"
