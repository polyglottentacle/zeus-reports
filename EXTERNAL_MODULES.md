# Zeus — Moduli Esterni: Valutazione e Stato

Questo file traccia i repo esterni clonati/studiati e la loro destinazione in Zeus.
Aggiornato manualmente dopo ogni valutazione tecnica.

---

## Tassonomia

```
Zeus = cervello principale (orchestrator)
MiroFish = simulazione sociale (agenti LLM che twittano/postano)
ochi / TradingAgents = occhio analitico LLM (decide Buy/Hold/Sell)
occhio_ai_trader / AI-Trader = arena esterna (segnali, copy-trading, leaderboard)
```

---

## ochi — TradingAgents (TauricResearch/TradingAgents)

**Stato: INTEGRATO (setup_required)**
**Percorso:** `C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\zeus\ochi`
**Modulo Zeus:** `agents/agent_occhi.py`

**Ruolo:** Occhio analitico — analisti LLM (market + social + news) che producono
una decisione direzionale su BTC-USD: Buy / Overweight / Hold / Underweight / Sell.

**Come attivare:**
```bash
cd ochi && bash setup_venv.sh
```

**Isolamento:** venv separato (`ochi/venv/`) per evitare conflitto openai 1.x vs 2.x.
**Provider LLM:** DeepSeek (riusa la chiave Zeus: LLM_API_KEY / LLM_BASE_URL).
**Analisti attivi:** market, social, news (no fundamentals — non supportato per crypto).
**Timeout:** 180s (configurabile via OCCHI_TIMEOUT).

---

## occhio_ai_trader — AI-Trader (HKUDS/AI-Trader)

**Stato: IN VALUTAZIONE — non integrato**
**Percorso:** `C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\zeus\occhio_ai_trader`
**Modulo Zeus:** nessuno (ancora)

**Ruolo:** Arena di trading per agenti — non un cervello decisionale.
Funzionalità: pubblicazione segnali, copy trading, leaderboard, paper trading, API REST, frontend.

**Perché NON ancora in Zeus:**
- Non produce un verdetto interno (non è un "senso")
- E' infrastruttura esterna: utile quando Zeus vorrà confrontarsi con altri agenti
  o pubblicare i suoi segnali su una piattaforma condivisa
- Va isolato (dipendenze FastAPI mancanti nel runtime Zeus)

**Test fatto:**
```powershell
python -m pytest service/server/tests -q
# → ModuleNotFoundError: No module named 'fastapi'
```

**Quando torna utile:**
- Fase 3 di Zeus: confronto con agenti esterni, leaderboard, copy-trading paper
- Non prima che occhi (TradingAgents) sia stabile e testato in produzione

**Prossimo passo (quando pronti):**
- Creare venv isolato `occhio_ai_trader/venv/`
- Studiare l'API di pubblicazione segnali
- Progettare un `bridge_ai_trader.py` che legge `daily_report.json` e pubblica su AI-Trader

---

## Regola generale

> Nessun modulo esterno entra in Zeus senza:
> 1. Venv isolato (nessuna dipendenza nel runtime principale)
> 2. Adattatore con try/except (non può mai crashare l'orchestrator)
> 3. Valutazione tecnica documentata qui
> 4. Test di graceful degradation (status="error" non = crash)
