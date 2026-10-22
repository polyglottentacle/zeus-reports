# Rayban Display Agent — scheletro

Scheletro di progetto per collegare un **agente vocale LLM generico (con tool
calling)** al display dei **Ray-Ban Meta Display**, seguendo l'architettura
ufficiale Meta (Wearables Device Access Toolkit, DAT):

```
Microfono occhiali → DAT → app Android → POST /agent/invoke → risposta → DAT → Display occhiali
```

Non è legato a Zeus/MiroFish: vive in questo repo solo come modulo
indipendente (`rayban_display/`). L'unico punto di contatto opzionale è il
tool `zeus_status` nel backend, che legge `output/daily_report.json` se
presente — rimovibile senza impatti.

## Stato — cosa è ✅ VERIFICATO e cosa è ⚠️ IPOTESI

- ✅ **VERIFICATO**: il backend FastAPI (`backend/app/`) importa ed esegue
  correttamente in questo ambiente. Test eseguiti con `TestClient`:
  - `GET /health` → `200 {"status": "ok", "model": "llama3-8b-8192"}`
  - `POST /agent/invoke` senza `LLM_API_KEY` configurata → `502` con messaggio
    chiaro (nessuna chiamata di rete, nessun crash).
  - `tools.py`: `get_time` e `zeus_status` eseguiti a mano, `zeus_status` ha
    letto il vero `output/daily_report.json` del repo e prodotto
    `"Zeus (2026-06-09T06:05:02.574786+00:00): DSR 0.0037, Kelly 0.0000"`.
  - Non è stata testata la chiamata reale a Groq/OpenAI (serve una
    `LLM_API_KEY` valida, non presente in questo ambiente): il loop di
    tool-calling in `agent.py` è scritto seguendo lo schema OpenAI-compatibile
    standard ma **non è stato verificato end-to-end contro un vero LLM**.

- ⚠️ **IPOTESI (non verificato)**: tutta la parte Android/`glasses/`:
  - Il modulo Android **non è stato compilato né eseguito**: questo ambiente
    non ha Android SDK, emulatore, né accesso al Meta Wearables DAT SDK (è
    dietro Developer Preview gated, richiede iscrizione su
    `wearables.developer.meta.com`).
  - `glasses/GlassesSession.kt` è un'interfaccia scritta sulla base del
    flusso descritto nella documentazione pubblica Meta, ma le classi/metodi
    reali del DAT SDK vanno verificati quando si ha accesso effettivo.
  - `glasses/StubGlassesSession.kt` è un finto "occhiali" per poter sviluppare
    e testare il resto dell'app (UI + chiamata al backend) senza hardware.
  - Le coordinate Maven del DAT SDK in `android/app/build.gradle.kts` e
    `android/settings.gradle.kts` sono placeholder commentati, non reali.

**Non dichiarare mai "funziona con gli occhiali reali"**: finché
`StubGlassesSession` non è sostituito da un'implementazione reale e testata
su hardware, questo resta uno scheletro lato software.

## Struttura

```
rayban_display/
├── backend/                      # Proxy FastAPI verso l'LLM
│   ├── app/
│   │   ├── main.py               # Endpoint /health, /agent/invoke
│   │   ├── agent.py              # Loop tool-calling verso endpoint OpenAI-compatibile
│   │   ├── tools.py               # Tool di esempio (get_time, zeus_status)
│   │   ├── schemas.py             # Modelli Pydantic richiesta/risposta
│   │   └── config.py              # Lettura .env
│   ├── requirements.txt
│   └── .env.example
└── android/                       # App companion (Kotlin)
    └── app/src/main/java/com/zeus/raybandisplay/
        ├── ui/MainActivity.kt      # UI minima: connetti, simula voce, mostra risposta
        ├── net/AgentApiClient.kt   # Client Retrofit verso il backend
        └── glasses/                # Astrazione sessione DAT + stub
```

## Come avviare il backend (verificato)

```bash
cd rayban_display/backend
pip install -r requirements.txt
cp .env.example .env   # poi inserire una vera LLM_API_KEY (Groq/OpenAI-compatibile)
uvicorn app.main:app --reload --port 8000
```

Test rapido:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "text": "che ore sono?"}'
```

## Come procedere sull'app Android (non ancora possibile qui)

1. Iscriversi alla Developer Preview del Wearables DAT su
   `wearables.developer.meta.com` e ottenere l'SDK reale per Android.
2. Aprire `rayban_display/android/` in Android Studio (genererà da solo il
   Gradle wrapper mancante — in questo ambiente non è stato possibile
   scaricare il binario `gradle-wrapper.jar`, nessun accesso di rete a
   servizi Gradle).
3. Aggiungere la dipendenza reale del DAT SDK in `app/build.gradle.kts` al
   posto del placeholder commentato.
4. Creare `glasses/RealGlassesSession.kt` che implementa `GlassesSession`
   con le classi vere del DAT SDK (sessione, callback microfono, display).
5. In `MainActivity.kt`, sostituire `StubGlassesSession()` con
   `RealGlassesSession(context)`.
6. Puntare `AgentApiClient` al backend reale (di default assume
   `10.0.2.2:8000`, cioè l'host visto da un emulatore Android; su dispositivo
   fisico va sostituito con l'IP/hostname raggiungibile del backend).

## Note di sicurezza

- `RAYBAN_BACKEND_API_KEY` (opzionale in `.env`) protegge `/agent/invoke` con
  un header `X-API-Key`. In produzione andrebbe sempre impostata, insieme a
  HTTPS (qui non configurato: è uno scheletro locale/dev).
- Nessuna chiave è hardcoded nel codice: tutto passa da `.env` /
  variabili d'ambiente, seguendo la stessa convenzione già in uso nel resto
  del repo Zeus.
