# Zeus Handoff Per Claude

Questo documento spiega il DNA del progetto Zeus, cosa abbiamo costruito, cosa abbiamo provato davvero, cosa abbiamo sbagliato, cosa abbiamo fatto bene e come continuare senza inventare numeri o confondere i progetti.

## Identita Del Progetto

Zeus non nasce come una semplice dashboard crypto.

Zeus e' un cervello locale di trading: osserva il mercato, ascolta segnali esterni, valuta il rischio, legge memoria storica, confronta fonti diverse e produce un verdetto operativo in modalita PAPER.

La metafora corretta e':

```text
Zeus = cervello e coscienza del sistema
Apollo = muscolo operativo / bot esecutivo
Hermes = voce / messaggero Telegram
MiroFish = simulazione sociale
Occhi = analisi LLM TradingAgents
Polymarket = oracolo dei mercati predittivi
WAL = memoria delle azioni Apollo
Dashboard = volto visibile di Zeus
Laboratorio di bot = luogo di studio, non produzione
```

Zeus deve sembrare un terminale vivo, non un giocattolo e non una pagina SaaS generica.

Visione:

> Quando Zeus dorme, osserva in silenzio. Quando si apre, si risveglia. Quando il mercato chiama, lo sente prima di noi.

## Obiettivo Reale

L'obiettivo non e' promettere profitti.

L'obiettivo e':

1. raccogliere segnali verificabili;
2. sintetizzarli in un verdetto leggibile;
3. pubblicare un file semplice che altri bot possano leggere;
4. tenere tutto in PAPER/SHADOW finche' non ci sono prove;
5. costruire una dashboard che mostri dati veri, non fantasia;
6. studiare Apollo e gli altri bot in laboratorio senza contaminare produzione.

## Stato Verificato

Zeus produce davvero:

```text
output/daily_report.json
output/strategy_status.json
output/zeus_signal.json
```

L'ultimo `zeus_signal.json` verificato contiene:

```text
verdict: SHORT
mode: PAPER
apollo_bridge: SHADOW
allow_long: false
allow_short: true
allow_any: true
```

Questo significa:

- Zeus sta producendo un segnale.
- Il segnale e' PAPER.
- Apollo non va considerato collegato in modo pienamente operativo.
- Il bridge e' ancora SHADOW.
- Non siamo in live trading.

## I Sensi Di Zeus

Zeus usa vari "sensi". La dashboard e i report devono mostrarli con stato chiaro.

```text
Udito        -> Fear & Greed Index
Vista        -> prezzo/trend BTC da exchange
Preveggenza  -> forecast tecnico 3 giorni
Memoria      -> fattori storici e alpha score
Equilibrio   -> rischio, drawdown, Sharpe, regime
Occhi        -> TradingAgents LLM
Polymarket   -> mercati predittivi
WAL          -> memoria Apollo / Cerbero
MiroFish     -> simulazione sociale Twitter/Reddit
```

Ogni senso deve essere marcato come:

```text
LIVE
PAPER
SHADOW
UNAVAILABLE
SETUP_REQUIRED
STALE
ERROR
```

Mai nascondere lo stato. Se un dato non c'e', non inventarlo.

## Cosa Abbiamo Gia Fatto

Abbiamo costruito e verificato:

- orchestrator Zeus;
- calcolo DSR;
- Kelly sizing;
- costi, slippage, funding e tasse stimate;
- MiroFish runner;
- integrazione TradingAgents come `occhi`;
- lettura Polymarket;
- lettura WAL Apollo/Cerbero;
- generazione `daily_report.json`;
- generazione `strategy_status.json`;
- generazione `zeus_signal.json`;
- Hermes briefing Telegram;
- Task Scheduler Windows;
- dashboard precedente `dashboard.html`;
- terminale grafico nuovo in HTML/React;
- cloni di studio:
  - `ochi/` = TradingAgents;
  - `occhio_ai_trader/` = AI-Trader;
- distinzione tra Zeus, Apollo, White Apollo, Black Apollo e laboratorio.

Abbiamo anche provato che:

- i test base Zeus passano;
- `run_zeus_daily.bat` puo' chiudere con `exit 0`;
- Hermes puo' inviare briefing Telegram con `message_id` reale;
- TradingAgents puo' produrre decisione su BTC;
- il WAL Apollo puo' essere letto da file;
- `zeus_signal.json` e' leggibile come ponte verso Apollo.

## Cosa Abbiamo Sbagliato

Questa parte e' importante. Non cancellarla, perche' e' il modo in cui il progetto cresce.

1. Abbiamo confuso "costruito" con "provato".

   Scrivere un file non significa che il sistema lo usi davvero.

2. Abbiamo detto troppo presto "tutto automatico".

   Un task creato nel Task Scheduler non e' riuscito finche' non chiude con ultimo esito `0`.

3. Abbiamo confuso segnale Zeus con esecuzione Apollo.

   Zeus puo' scrivere `zeus_signal.json`, ma Apollo e' collegato solo quando lo legge davvero prima di agire.

4. Abbiamo rischiato di mischiare progetti.

   Zeus, Black Apollo, White Apollo, Apollo legacy e laboratorio di bot devono restare distinti.

5. Abbiamo copiato dashboard/progetti grafici nella root di Zeus.

   Non e' disastroso, ma va ordinato. I file grafici devono vivere in una cartella dedicata, non confondersi con il backend.

6. Abbiamo visto numeri stimati e li abbiamo quasi trattati come risultati.

   Win rate futuro, PnL futuro e miglioramenti non sono reali finche' non sono misurati.

7. Abbiamo avuto rumore operativo.

   Alcuni errori erano cosmetici o di path Windows, ma vanno sempre distinti dagli errori reali.

## Cosa Abbiamo Fatto Bene

1. Abbiamo iniziato a pretendere prove.

   Ora la regola e': prova prima, dichiara dopo.

2. Abbiamo isolato gli esperimenti esterni.

   TradingAgents e AI-Trader non sono stati fusi alla cieca nel cuore di Zeus.

3. Abbiamo creato una tassonomia chiara.

   Cervello, muscolo, voce, occhi, memoria, laboratorio.

4. Abbiamo mantenuto PAPER/SHADOW.

   Nessun live trading va attivato senza consenso esplicito e prove forti.

5. Abbiamo trasformato Zeus da idea poetica a sistema leggibile.

   Ci sono JSON, log, test, task, report, briefing e component status.

6. Abbiamo capito il ruolo della dashboard.

   La dashboard non deve inventare: deve mostrare fedelmente cio' che Zeus sa e cio' che Zeus non sa.

## Regole Per Claude

Claude deve seguire queste regole:

1. Non inventare numeri.
2. Non dire "LIVE" se e' PAPER o SHADOW.
3. Non dichiarare Apollo collegato finche' non c'e' prova.
4. Non dichiarare Telegram inviato senza log o conferma.
5. Non cancellare file.
6. Non spostare cartelle operative senza snapshot e consenso.
7. Non leggere o stampare segreti `.env`.
8. Non fondere progetti diversi.
9. Non promettere win rate, PnL o profitti.
10. Prima controlla, poi dichiara.

## Progetti Da Non Confondere

```text
C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\zeus
```

Sistema analitico, report, segnali, dashboard, Hermes.

```text
C:\Users\docum\Desktop\black_apollo
```

Bot operativo/esperimentale con WAL enorme. Non spostare, non fermare, non modificare senza richiesta.

```text
C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\white_apollo
```

Variante Apollo separata.

```text
C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\apollo
C:\Users\docum\Desktop\_SCRIVANIA_ORDINATA\00_ATTIVI_APOLLO_ZEUS\apollo_era_b
```

Versioni legacy/storiche.

```text
C:\Users\docum\Desktop\laboratorio di bot
```

Qui si studia, si copia codice selezionato, si fanno mappe, si fanno ricerche. Non e' produzione.

## Laboratorio Di Bot

Il laboratorio deve diventare il luogo delle ricerche profonde.

Struttura consigliata:

```text
laboratorio di bot/
├── INVENTARIO_BOT.md
├── ARCHITETTURA_REALE.md
├── DOMANDE_RICERCA.md
├── snapshots/
│   ├── zeus_codice/
│   ├── black_apollo_codice/
│   ├── white_apollo_codice/
│   └── apollo_legacy/
├── esperimenti/
└── risultati/
```

Snapshot consentiti:

- `.py`
- `.md`
- `.html`
- `.json` piccoli;
- configurazioni senza segreti.

Da escludere:

- `.env`;
- WAL enormi;
- database runtime;
- log giganti;
- cache;
- `venv`;
- `node_modules`.

## Dashboard Zeus

La dashboard e' il volto di Zeus.

Deve mostrare:

- Zeus verdict;
- score;
- confidence;
- mode;
- Apollo bridge;
- `allow_long`;
- `allow_short`;
- `allow_any`;
- 8 sensi;
- reasoning con peso e score;
- BTC price/trend;
- backtest storico;
- DSR;
- Kelly;
- costi;
- MiroFish;
- TradingAgents/Occhi;
- Polymarket;
- WAL Apollo;
- freshness del report;
- stato Telegram/Hermes;
- stato sistema.

Deve distinguere:

```text
BACKTEST != PAPER != SHADOW != LIVE
```

Quick Trade, leva, Buy/Long, Sell/Short, TP/SL devono restare disabilitati o marcati `PAPER ONLY` finche' non decidiamo diversamente.

## DNA Visivo

Zeus terminale ha un DNA preciso:

- grafite scura;
- bronzo/oro antico;
- pietra/marmo;
- verde solo dove significa vita, dato live o attenzione;
- rosso solo per rischio, short, errore;
- ambra per warning;
- compatto quando dorme;
- espanso quando si risveglia;
- Zeus come presenza, non decorazione.

Non deve sembrare:

- casinò crypto;
- cyberpunk economico;
- dashboard SaaS generica;
- giocattolo;
- landing page;
- app mobile.

## Metafore Da Conservare

```text
Zeus dorme ma osserva.
Hermes parla quando il report e' pronto.
Apollo e' il braccio, non il cervello.
Il WAL e' la memoria dei muscoli.
MiroFish e' il coro sociale.
Polymarket e' l'oracolo probabilistico.
Occhi e' il consiglio degli analisti LLM.
Il laboratorio e' l'officina, non il tempio.
```

## Cosa Fare Adesso

Priorita':

1. Fare inventario dei progetti senza spostare produzione.
2. Tenere Zeus pulito da file copiati a caso.
3. Mettere la dashboard in cartella dedicata, quando deciso.
4. Collegare la dashboard ai JSON reali.
5. Segnalare ogni dato demo rimasto.
6. Verificare Task Scheduler e Hermes con log, non a parole.
7. Studiare Apollo nel laboratorio.
8. Capire se Apollo legge davvero `zeus_signal.json`.
9. Misurare PAPER performance, non stimarla.
10. Solo dopo parlare di live.

## Cosa Non Fare Adesso

- Non attivare trading reale.
- Non migrare tutto su VPS senza inventario.
- Non cancellare versioni vecchie.
- Non spostare `black_apollo` mentre scrive WAL.
- Non mischiare codice Zeus dentro Apollo.
- Non mischiare Apollo dentro Zeus.
- Non trasformare ogni idea in produzione.

## Frase Guida

Zeus deve restare poetico nella visione e severo nei dati.

Se una cosa non e' provata, va chiamata:

```text
ipotesi
setup_required
shadow
paper
unavailable
da verificare
```

Mai "fatto" solo perche' e' bello dirlo.

