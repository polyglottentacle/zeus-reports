#!/bin/bash
# ============================================================
#  ZEUS — Setup Script per VPS Linux (Ubuntu 22.04+)
#  Esegui come root o con sudo:
#    bash setup.sh
# ============================================================
set -e

ZEUS_DIR="/opt/zeus"
ZEUS_USER="zeus"
REPO_URL="https://github.com/polyglottentacle/zeus-reports.git"

echo "🔱 Zeus Cloud Setup — avvio..."

# ── 1. Sistema ───────────────────────────────────────────────
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git nginx curl cron

# ── 2. Utente dedicato (non root) ──────────────────────────
if ! id "$ZEUS_USER" &>/dev/null; then
  useradd -r -m -d "$ZEUS_DIR" -s /bin/bash "$ZEUS_USER"
  echo "  ✅ Utente '$ZEUS_USER' creato."
fi

# ── 3. Clone / pull repo ────────────────────────────────────
if [ -d "$ZEUS_DIR/.git" ]; then
  echo "  🔄 Aggiornamento repo..."
  cd "$ZEUS_DIR" && git pull
else
  echo "  📦 Clone repo..."
  git clone "$REPO_URL" "$ZEUS_DIR"
fi
chown -R "$ZEUS_USER:$ZEUS_USER" "$ZEUS_DIR"

# ── 4. Virtualenv + dipendenze ──────────────────────────────
cd "$ZEUS_DIR"
if [ ! -d "venv" ]; then
  sudo -u "$ZEUS_USER" python3 -m venv venv
fi
sudo -u "$ZEUS_USER" venv/bin/pip install --upgrade pip -q
sudo -u "$ZEUS_USER" venv/bin/pip install -r requirements.txt -q
# MiroFish dipendenze (se presenti)
if [ -f "MiroFish/requirements.txt" ]; then
  sudo -u "$ZEUS_USER" venv/bin/pip install -r MiroFish/requirements.txt -q
fi
echo "  ✅ Dipendenze installate."

# ── 5. Cartelle necessarie ──────────────────────────────────
sudo -u "$ZEUS_USER" mkdir -p "$ZEUS_DIR/output"
sudo -u "$ZEUS_USER" mkdir -p "$ZEUS_DIR/log"
sudo -u "$ZEUS_USER" mkdir -p "$ZEUS_DIR/mirofish_runner/forecast_history"
sudo -u "$ZEUS_USER" mkdir -p "$ZEUS_DIR/secrets"

# ── 6. .env dal template ────────────────────────────────────
if [ ! -f "$ZEUS_DIR/.env" ]; then
  cp "$ZEUS_DIR/deploy/zeus.env.template" "$ZEUS_DIR/.env"
  chown "$ZEUS_USER:$ZEUS_USER" "$ZEUS_DIR/.env"
  chmod 600 "$ZEUS_DIR/.env"
  echo ""
  echo "  ⚠️  IMPORTANTE: modifica $ZEUS_DIR/.env con le tue chiavi!"
  echo "      nano $ZEUS_DIR/.env"
  echo ""
fi

# ── 7. Git config per push automatico ──────────────────────
sudo -u "$ZEUS_USER" git -C "$ZEUS_DIR" config user.email "zeus@cloud"
sudo -u "$ZEUS_USER" git -C "$ZEUS_DIR" config user.name "Zeus Cloud"

# ── 8. Installa servizi systemd ─────────────────────────────
cp "$ZEUS_DIR/deploy/zeus-orchestrator.service" /etc/systemd/system/
cp "$ZEUS_DIR/deploy/zeus-orchestrator.timer"   /etc/systemd/system/
cp "$ZEUS_DIR/deploy/zeus-hermes.service"       /etc/systemd/system/
cp "$ZEUS_DIR/deploy/zeus-hermes.timer"         /etc/systemd/system/

systemctl daemon-reload
systemctl enable zeus-orchestrator.timer
systemctl enable zeus-hermes.timer
systemctl start  zeus-orchestrator.timer
systemctl start  zeus-hermes.timer

echo "  ✅ Timer systemd attivati."

# ── 9. Nginx per dashboard ──────────────────────────────────
cat > /etc/nginx/sites-available/zeus <<'NGINXEOF'
server {
    listen 80;
    server_name _;

    root /opt/zeus;
    index dashboard.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /output/ {
        alias /opt/zeus/output/;
        add_header Access-Control-Allow-Origin *;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/zeus /etc/nginx/sites-enabled/zeus
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
echo "  ✅ Nginx attivato — dashboard disponibile su http://IP_SERVER"

echo ""
echo "🔱 Setup completato!"
echo ""
echo "Prossimi passi:"
echo "  1. nano /opt/zeus/.env                    → inserisci le chiavi"
echo "  2. systemctl start zeus-orchestrator       → test primo run"
echo "  3. journalctl -u zeus-orchestrator -f      → vedi i log"
echo "  4. Apri http://IP_SERVER nel browser       → dashboard"
