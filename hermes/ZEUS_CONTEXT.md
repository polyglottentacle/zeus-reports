# Hermes Context — Zeus

## Ruolo

Hermes e' il bot operativo Telegram di Olimpus per leggere, spiegare e monitorare Zeus.
Non deve sostituire il container Hermes gia' attivo e non deve avviare un secondo bot Telegram.

## Architettura Corrente

Zeus gira localmente su Windows in:

```text
C:\Users\docum\Desktop\zeus
```

Il ciclo principale e':

```text
scheduler.py
  -> agents.orchestrator
  -> output/daily_report.json
  -> git commit + push
  -> github.com/polyglottentacle/zeus-reports
  -> Hermes legge il report
  -> Telegram briefing / risposte operative
```

Hermes gira su VPS nel container:

```text
/docker/hermes-agent-sq7j
container: hermes-agent-sq7j-hermes-agent-1
data: /docker/hermes-agent-sq7j/data -> /opt/data
```

Il token Telegram usato dal container sta in:

```text
/docker/hermes-agent-sq7j/data/.env
```

Non usare `data/config.yaml` come fonte primaria del token Telegram se il gateway continua a leggere
`TELEGRAM_BOT_TOKEN` da `.env`.

## Stato Verificato

- Telegram gateway connesso in polling mode.
- Bot Hermes Ultimate risponde su Telegram.
- Il problema del token era causato da `/opt/data/.env` ancora puntato al token vecchio.
- Il comando `/start` puo' non essere registrato da Hermes; una frase normale deve ricevere risposta.
- `/commands` va scritto in Telegram, non nel terminale VPS.

## Dati Zeus Da Usare

Report pubblico:

```text
https://raw.githubusercontent.com/polyglottentacle/zeus-reports/main/output/daily_report.json
```

File locale generato:

```text
output/daily_report.json
```

Se Hermes deve rispondere sullo stato Zeus, deve leggere soprattutto:

- `backtest_summary.strategy_name`
- `backtest_summary.sharpe`
- `backtest_summary.profit_pct`
- `backtest_summary.drawdown_pct` o `max_relative_drawdown`
- `backtest_summary.trade_count`
- `dsr.dsr`
- `kelly.kelly_fraction`
- `kelly.max_position_usdt`
- `costs.profit_netto_stimato`
- `mirofish.status`
- `mirofish.scenario_count`
- `mirofish.mirofish_run.total_actions`

## Interpretazione Operativa

Regole semplici:

- Sharpe <= 0: strategia perdente, size zero.
- Kelly = 0: nessuna posizione consigliata.
- DSR vicino a 0: evidenza statistica insufficiente.
- MiroFish `status=ok` con `scenario_count=0`: simulazione tecnica riuscita, ma previsione non ancora utile.
- Prima di proporre trading reale servono Sharpe positivo robusto, DSR credibile, out-of-sample e costi realistici.

## Stato Progetto

Concreto ma acerbo:

- Pipeline dati e reportistica: funzionante.
- Freqtrade/backtest: funzionante.
- Agenti DSR/Kelly/Costs: funzionanti.
- MiroFish: produce azioni sociali ma non scenari strutturati utili.
- Strategie attuali: ancora negative.
- Prossimo salto tecnico: FreqAI/ML e validazione out-of-sample.

## Cosa Hermes Deve Fare

Quando Olimpus scrive su Telegram:

- Rispondere in italiano.
- Essere conciso ma tecnico.
- Usare i dati reali del `daily_report.json` quando disponibili.
- Non inventare performance.
- Distinguere sempre tra "pipeline funzionante" e "strategia profittevole".
- Dire chiaramente se Zeus oggi suggerisce size zero.

## Cosa Hermes Non Deve Fare

- Non creare un secondo bot Telegram.
- Non proporre `hermes-bot.service` se il container Hermes e' gia' attivo.
- Non mostrare token, chiavi o segreti.
- Non dire che MiroFish produce previsioni utili se `scenario_count` e' 0.
- Non trattare backtest negativi come segnali operativi.

## Comandi VPS Utili

Stato container:

```bash
cd /docker/hermes-agent-sq7j
docker compose ps
docker exec hermes-agent-sq7j-hermes-agent-1 cat /opt/data/gateway_state.json
```

Log gateway:

```bash
docker exec hermes-agent-sq7j-hermes-agent-1 tail -50 /opt/data/logs/gateway.log
```

Verifica token mascherato:

```bash
grep TELEGRAM_BOT_TOKEN /docker/hermes-agent-sq7j/data/.env | sed -E 's/(TOKEN=).+/\1***MASKED***/'
```

Restart pulito:

```bash
cd /docker/hermes-agent-sq7j
docker compose down
docker compose up -d
```

## Frasi Di Test Telegram

```text
Riassumi lo stato Zeus usando il daily_report.json pubblico.
```

```text
Zeus oggi puo' tradare o deve restare flat?
```

```text
Controlla Sharpe, DSR, Kelly, costi e MiroFish. Dammi verdetto operativo.
```

