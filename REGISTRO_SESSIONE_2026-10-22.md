# Registro Sessione — 2026-10-22

**Agente:** Claude (Claude Code, sessione cloud)
**Macchina:** container cloud effimero (NON il PC Zeus Windows) — nessuna
modifica è stata fatta su `C:\Users\docum\...`, solo su questo checkout git.
**Branch:** `claude/rayban-meta-display-2ytwjp`
**Repo:** `zeus-reports`

## Richiesta

Creare lo scheletro di un progetto per collegare un agente vocale LLM
generico (con tool calling) al display dei Ray-Ban Meta Display, secondo il
flusso: microfono occhiali → Meta Wearables DAT → app Android → backend
→ risposta → DAT → display. Confermato dall'utente via domande di chiarimento:
agente = "LLM vocale generico" (non Zeus, non Dioniso), scope = scheletro
completo (Android + backend), repo di destinazione = `zeus-reports`.

## Cosa è stato creato

Nuova cartella `rayban_display/` (nessun file esistente del repo toccato):

- `rayban_display/backend/` — backend FastAPI (`app/main.py`, `agent.py`,
  `tools.py`, `schemas.py`, `config.py`) + `requirements.txt` + `.env.example`.
- `rayban_display/android/` — progetto Android/Kotlin (Gradle) con
  `ui/MainActivity.kt`, `net/AgentApiClient.kt`, `glasses/GlassesSession.kt`
  (interfaccia) e `glasses/StubGlassesSession.kt` (implementazione finta).
- `rayban_display/README.md` — descrive architettura, stato verificato vs
  ipotesi, istruzioni di avvio.

## ✅ VERIFICATO (comando eseguito, output mostrato)

- `python3 -c "from app.main import app; ..."` → import senza errori.
- `TestClient(app).get("/health")` → `200 {"status": "ok", "model":
  "llama3-8b-8192"}`.
- `TestClient(app).post("/agent/invoke", json={...})` senza `LLM_API_KEY` →
  `502 {"detail": "LLM_API_KEY non configurata: impostala in backend/.env"}`
  (comportamento corretto: nessuna chiamata di rete a vuoto).
- `TOOL_REGISTRY["get_time"]({})` → stringa con ora UTC corrente.
- `TOOL_REGISTRY["zeus_status"]({})` → ha letto il vero
  `output/daily_report.json` presente nel repo e ritornato
  `"Zeus (2026-06-09T06:05:02.574786+00:00): DSR 0.0037, Kelly 0.0000"`.

## ⚠️ IPOTESI (non provato in questa sessione)

- Nessuna chiamata reale a un LLM (Groq/OpenAI-compatibile): non c'è una
  `LLM_API_KEY` valida in questo ambiente. Il loop di tool-calling in
  `agent.py` segue lo schema standard OpenAI-compatibile ma non è stato
  testato end-to-end contro un vero modello.
- L'intero progetto Android **non è stato compilato né eseguito**: niente
  Android SDK/emulatore in questo ambiente, e niente accesso al Meta
  Wearables Device Access Toolkit (DAT) reale (richiede Developer Preview
  gated su `wearables.developer.meta.com`).
- Le coordinate Maven del DAT SDK sono placeholder commentati, non
  verificati — da sostituire con quelli reali quando si ha accesso all'SDK.
- Il Gradle wrapper (`gradle-wrapper.jar`) non è stato generato: nessun
  accesso di rete a servizi Gradle da questo ambiente. Va generato aprendo
  il progetto in Android Studio o eseguendo `gradle wrapper` localmente.

## Prossimo passo per chi riprende il lavoro

1. Ottenere accesso alla Developer Preview del DAT SDK (Meta).
2. Scrivere `glasses/RealGlassesSession.kt` con le classi reali dell'SDK.
3. Testare `agent.py` con una `LLM_API_KEY` reale (Groq o altro provider
   OpenAI-compatibile).
4. Solo dopo questi due punti, questo smette di essere "scheletro" ed entra
   nella categoria "provato" secondo la regola di tracciabilità del progetto.
