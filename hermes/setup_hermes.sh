#!/usr/bin/env bash
# ============================================================
# Zeus — Hermes VPS Setup Script
# Esegui come root o con sudo sul VPS Hermes
# ============================================================
set -euo pipefail

ZEUS_DIR="/opt/zeus"
VENV_DIR="$ZEUS_DIR/.venv"
BRIEFING_SCRIPT="$ZEUS_DIR/hermes/briefing.py"
ENV_FILE="$ZEUS_DIR/hermes/.env"
LOG_FILE="/var/log/zeus_briefing.log"
CRON_TIME="5 8 * * *"   # 08:05 UTC ogni giorno

echo "=== Zeus Hermes Setup ==="

# 1. Crea directory
mkdir -p "$ZEUS_DIR/hermes"
mkdir -p "$(dirname $LOG_FILE)"
touch "$LOG_FILE"
chmod 666 "$LOG_FILE"

# 2. Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/5] Creazione virtualenv Python..."
    python3 -m venv "$VENV_DIR"
fi
echo "[1/5] Virtualenv: OK"

# 3. Installa dipendenze
echo "[2/5] Installazione dipendenze..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet requests
echo "[2/5] Dipendenze: OK"

# 4. Copia lo script briefing.py
# (Assumiamo che il file sia già presente in $ZEUS_DIR/hermes/briefing.py)
# Se stai eseguendo il setup dopo git clone:
# git clone https://github.com/polyglottentacle/zeus-reports.git $ZEUS_DIR
echo "[3/5] Script briefing.py: controllato"

# 5. File .env con le credenziali
if [ ! -f "$ENV_FILE" ]; then
    echo "[4/5] Creazione .env (DEVI compilare le credenziali!)..."
    cat > "$ENV_FILE" << 'EOF'
# Zeus Hermes — Credenziali (NON committare questo file)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
ZEUS_REPORT_URL=https://raw.githubusercontent.com/polyglottentacle/zeus-reports/main/output/daily_report.json
EOF
    chmod 600 "$ENV_FILE"
    echo "[4/5] .env creato — MODIFICA $ENV_FILE con le credenziali reali prima di procedere."
else
    echo "[4/5] .env già presente: OK"
fi

# 6. Cron job
CRON_CMD="$CRON_TIME source $ENV_FILE && $VENV_DIR/bin/python3 $BRIEFING_SCRIPT >> $LOG_FILE 2>&1"
# Usa wrapper script per caricare .env (cron non ha shell environment)
WRAPPER="$ZEUS_DIR/hermes/run_briefing.sh"
cat > "$WRAPPER" << WRAPPER_EOF
#!/usr/bin/env bash
set -a
source "$ENV_FILE"
set +a
exec "$VENV_DIR/bin/python3" "$BRIEFING_SCRIPT"
WRAPPER_EOF
chmod +x "$WRAPPER"

# Aggiungi a crontab solo se non già presente
CRON_LINE="$CRON_TIME $WRAPPER >> $LOG_FILE 2>&1"
if crontab -l 2>/dev/null | grep -qF "$BRIEFING_SCRIPT"; then
    echo "[5/5] Cron già configurato: OK"
else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    echo "[5/5] Cron aggiunto: $CRON_LINE"
fi

echo ""
echo "=== Setup completato ==="
echo ""
echo "PROSSIMI PASSI:"
echo "  1. Modifica $ENV_FILE con le credenziali Telegram reali"
echo "  2. Testa manualmente: bash $WRAPPER"
echo "  3. Controlla il log: tail -f $LOG_FILE"
echo ""
