# Zeus — Intelligenza di Trading + MiroFish

> Sistema locale di analisi quantitativa, backtesting e simulazione sociale dei mercati.
> PC: Zeus (Windows 11) | Python: `C:\Users\docum\.cache\codex-runtimes\...`

---

## gstack

gstack è il toolkit di engineering installato in `~/.Codex/skills/gstack`.

### Navigazione web
- **Usa sempre `/browse`** per qualsiasi navigazione web, ricerca o scraping.
- **Non usare mai** gli strumenti `mcp__claude-in-chrome__*`.

### Skill disponibili
`/office-hours` `/plan-ceo-review` `/plan-eng-review` `/plan-design-review`
`/design-consultation` `/design-shotgun` `/design-html` `/review` `/ship`
`/land-and-deploy` `/canary` `/benchmark` `/browse` `/connect-chrome`
`/qa` `/qa-only` `/design-review` `/setup-browser-cookies` `/setup-deploy`
`/setup-gbrain` `/retro` `/investigate` `/document-release` `/document-generate`
`/codex` `/cso` `/autoplan` `/plan-devex-review` `/devex-review` `/careful`
`/freeze` `/guard` `/unfreeze` `/gstack-upgrade` `/learn`

---

## Struttura del Progetto

```
zeus/                           ← root progetto (git repo)
├── .env                        ← chiavi API (LLM Groq + ZEP)
├── scheduler.py                ← cron notturno → orchestrator → git push
├── agents/
│   ├── orchestrator.py         ← coordina tutti gli agenti → daily_report.json
│   ├── agent2_dsr.py           ← Deflated Sharpe Ratio (López de Prado)
│   ├── agent3_kelly.py         ← Kelly fraction sizing
│   └── agent4_costs.py         ← commissioni + slippage + tasse Box3/Box1
├── freqtrade/
│   └── user_data/
│       ├── config.json
│       ├── data/binance/BTC_USDT-1h.feather   ← 21035 candele reali
│       └── backtest_results/   ← *.meta.json + *.zip
├── MiroFish/                   ← simulatore sociale (OASIS + camel-ai)
│   ├── .env                    ← PYTHON_EXECUTABLE + LLM_API_KEY + ZEP
│   └── backend/
│       ├── run.py              ← Flask API :5001
│       ├── app/
│       │   ├── config.py       ← PYTHON_EXECUTABLE configurato
│       │   └── services/
│       │       └── simulation_runner.py  ← usa Config.PYTHON_EXECUTABLE
│       └── scripts/
│           ├── run_parallel_simulation.py
│           ├── run_twitter_simulation.py
│           └── run_reddit_simulation.py
├── mirofish_runner/
│   ├── run_daily.py            ← integrazione Zeus↔MiroFish (usa PYTHON_EXECUTABLE)
│   └── forecast_history/       ← JSON giornalieri delle previsioni
├── output/
│   ├── daily_report.json       ← report finale (dsr + kelly + costs + mirofish)
│   └── strategy_status.json
└── tests/
    ├── test_agent2_dsr.py
    ├── test_agent3_kelly.py
    └── test_agent4_costs.py
```

---

## Python — Regola d'Oro

**Unico Python disponibile su Zeus:**
```
C:\Users\docum\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```
- Versione: 3.12.13
- NON è nel PATH di sistema (`python` nel terminale → Microsoft Store stub)
- Ha installato: camel-ai, camel-oasis, oasis, flask, flask-cors, pydantic, zep-cloud, PyMuPDF, ecc.

**Come avviare qualsiasi script:**
```powershell
& "C:\Users\docum\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" <script.py>
```

**Come avviare il backend MiroFish:**
```powershell
cd C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\zeus\MiroFish\backend
& "C:\Users\docum\.cache\...\python.exe" run.py
# Flask gira su http://127.0.0.1:5001
```

---

## Flusso del Sistema

```
ogni notte (scheduler.py)
    ↓
orchestrator.py
    ├── legge ultimo backtest Freqtrade (*.meta.json + *.zip)
    ├── agent2_dsr.py        → Deflated Sharpe Ratio
    ├── agent3_kelly.py      → Kelly fraction + max_position_usdt
    ├── agent4_costs.py      → commissioni + tasse
    └── mirofish_runner/run_daily.py
            → avvia run_parallel_simulation.py con PYTHON_EXECUTABLE
            → simula 100 agenti × 40 round su Twitter+Reddit
            → genera scenari BTC/USDT 30gg
    ↓
output/daily_report.json
    ↓
git commit + push → github.com/polyglottentacle/zeus-reports
    ↓
Hermes (VPS) cron 08:00 → Telegram briefing
```

---

## Strategie Freqtrade (stato attuale)

| Strategia | Sharpe | Note |
|-----------|--------|------|
| EmaCross | -1.33 | scartata |
| EmaRsiTrend | -0.81 | scartata |
| EmaRsiAdxVolume | -0.20 | **migliore finora** |
| EmaRsiAdxVolumePlus | -0.64 | regressione |

Backtest: BTC/USDT 1h, 2024-01-02 → 2026-05-26, 196 trade, capitale 1000 USDT.
**Obiettivo:** portare Sharpe > 0.5 con FreqAI + segnali ML.

---

## Variabili d'Ambiente (.env)

```bash
# zeus/.env
LLM_API_KEY=gsk_...            # Groq (llama3-8b-8192) — compatibile OpenAI
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_NAME=llama3-8b-8192
ZEP_API_KEY=z_...              # Zep Cloud (memoria agenti)

# MiroFish/.env (specchio + aggiunta)
PYTHON_EXECUTABLE=C:\Users\docum\.cache\...\python.exe
+ tutte le sopra
```

---

## Fix Applicati (2026-05-27)

1. `MiroFish/backend/app/config.py` — aggiunto `PYTHON_EXECUTABLE`
2. `MiroFish/backend/app/services/simulation_runner.py` — usa `Config.PYTHON_EXECUTABLE` invece di `sys.executable`
3. `mirofish_runner/run_daily.py` — aggiunto `PYTHON_EXECUTABLE` costante, sostituito `sys.executable`
4. `scheduler.py` — aggiunto `PYTHON_EXECUTABLE` costante, sostituito `sys.executable`
5. Installato `camel-oasis==0.2.5` (force su Python 3.12), `flask-cors`, `PyMuPDF`, `zep-cloud`
6. Risolto conflitto `pydantic==2.13.4` + `pydantic-core==2.46.4`

---

## Obiettivi Prossime Settimane

- [ ] FreqAI: integrare ML nelle strategie (predittori su features OHLCV + indicatori)
- [ ] MiroFish attivo: verificare primo run reale con Groq API
- [ ] Dashboard UI: visualizzare metriche + scenari MiroFish + storia previsioni
- [ ] Calibrare agenti: aumentare da 100 a 500-1000 agenti nelle simulazioni
- [ ] Hermes: verificare ricezione briefing Telegram alle 08:00

---

## Comandi Utili

```powershell
# Test completo del sistema (run once)
& "C:\Users\docum\.cache\...\python.exe" scheduler.py --once

# Test solo MiroFish
& "C:\Users\docum\.cache\...\python.exe" -m mirofish_runner.run_daily

# Avvia MiroFish backend (Flask)
& "C:\Users\docum\.cache\...\python.exe" MiroFish\backend\run.py

# Test import tutto OK
& "C:\Users\docum\.cache\...\python.exe" -c "from camel.models import ModelFactory; import oasis; print('OK')"
```
