#!/bin/bash
# ============================================================
#  Zeus — Push automatico del daily_report su GitHub
#  Chiamato dall'orchestrator dopo ogni run.
#  Richiede GITHUB_TOKEN nel .env
# ============================================================

set -e
cd /opt/zeus

# Carica le variabili d'ambiente
source .env 2>/dev/null || true

if [ -z "$GITHUB_TOKEN" ]; then
  echo "[push_report] GITHUB_TOKEN non configurato — skip push."
  exit 0
fi

# Configura remote con token
git remote set-url origin \
  "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"

# Stage solo il report (non secrets, non .env)
git add output/daily_report.json
git add output/strategy_status.json 2>/dev/null || true

# Commit solo se ci sono cambiamenti
if git diff --cached --quiet; then
  echo "[push_report] Nessun cambiamento nel report — skip."
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
git commit -m "auto: daily_report aggiornato ${TIMESTAMP}"
git push origin main

echo "[push_report] ✅ Report pushato su GitHub."
