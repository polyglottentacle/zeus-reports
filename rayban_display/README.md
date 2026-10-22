# Rayban Display Agent — scheletro

Scheletro di progetto per collegare un **agente vocale LLM generico (con tool
calling)** al display dei **Ray-Ban Meta Display**, usando il
**Meta Wearables Device Access Toolkit (DAT)**:

```
Microfono occhiali → DAT (speech) → app Android → POST /agent/invoke → risposta → DAT (display) → Display occhiali
```

Non è legato a Zeus/MiroFish: vive in questo repo solo come modulo
indipendente (`rayban_display/`). L'unico punto di contatto opzionale è il
tool `zeus_status` nel backend, che legge `output/daily_report.json` se
presente — rimovibile senza impatti.

## Link utili (controllali tu stesso)

- **Developer Center DAT** (iscrizione, Application ID / Client Token, gestione progetti): https://wearables.developer.meta.com
- **Guida "Getting started"**: https://wearables.developer.meta.com/docs/develop/dat/getting-started-toolkit/
- **Guida integrazione Android**: https://wearables.developer.meta.com/docs/build-integration-android
- **API reference Android**: https://wearables.developer.meta.com/docs/reference/android/dat/latest
- **Repo ufficiale SDK Android** (sample app incluse): https://github.com/facebook/meta-wearables-dat-android
- **Repo ufficiale SDK iOS**: https://github.com/facebook/meta-wearables-dat-ios
- **Annuncio toolkit** (maggio 2026): https://developers.meta.com/blog/introducing-meta-wearables-device-access-toolkit/
- **Toolkit 1.0** (30 settembre 2026): https://developers.meta.com/blog/build-for-display-glasses/

## Aggiornamento 2026-10-22: cosa è cambiato rispetto alla prima versione

La prima versione di questo scheletro (commit precedente) trattava l'SDK DAT
come non verificabile (Developer Preview gated, coordinate Maven ignote).
Ricerca e verifica in questa sessione hanno corretto quell'assunzione:

- Il toolkit è **pubblico** su GitHub (`facebook/meta-wearables-dat-android`,
  licenza "Meta Wearables Developer Terms") e pubblicato su **Maven Central**
  sotto il gruppo `com.meta.wearable`, versione `1.0.1` — **nessun token o
  repository extra richiesto** (contraddice una vecchia indicazione "GitHub
  Packages + token" trovata in una fonte terza: la fonte primaria, il README
  del repo, non la richiede).
- Il toolkit è passato da *developer preview* (maggio 2026) a **1.0 stabile**
  dal 30 settembre 2026, per Ray-Ban Meta (Gen 1/2), Ray-Ban Meta Display,
  Oakley Meta HSTN e Oakley Meta Vanguard.
- ⚠️ **Importante per questo progetto**: **Speech** (riconoscimento vocale
  sugli occhiali) e, in parte, **Display** restano capability
  **"experimental"**: si possono sviluppare e testare (anche in beta), ma
  **Meta non consente ancora di pubblicarle sui canali di release pubblici**.
  Quindi oggi si può costruire e provare un agente vocale con display, ma
  **non distribuirlo pubblicamente** finché Meta non stabilizza queste due
  capability. Fonte: `plugins/mwdat-android/skills/speech/SKILL.md` nel repo
  ufficiale ("Apps can use it for development and beta testing, but cannot
  publish it to production release channels yet").
- Ho aggiornato `android/` con le dipendenze Gradle reali
  (`com.meta.wearable:mwdat-core/display/speech/mockdevice:1.0.1`), i
  permessi/manifest reali (`BLUETOOTH`, `BLUETOOTH_CONNECT`, `INTERNET` +
  meta-data `APPLICATION_ID`/`CLIENT_TOKEN`), e un `glasses/RealGlassesSession.kt`
  che segue i pattern documentati (registrazione → sessione → `addDisplay()` /
  `addSpeech()` → `sendContent` / `transcriptions`), al posto del vecchio
  stub inventato. Ho anche copiato il Gradle wrapper (binario generico,
  Apache License, identico in ogni progetto Android) dal sample ufficiale
  `DisplayAccess`, così il progetto è davvero compilabile con
  `./gradlew assembleDebug` una volta aperto in Android Studio con l'SDK
  Android installato.

## Stato — cosa è ✅ VERIFICATO e cosa è ⚠️ IPOTESI

- ✅ **VERIFICATO**: il backend FastAPI (`backend/app/`) importa ed esegue
  correttamente. Test con `TestClient`: `GET /health` → 200; `POST
  /agent/invoke` senza `LLM_API_KEY` → 502 con messaggio chiaro; tool
  `get_time`/`zeus_status` eseguiti con successo (`zeus_status` ha letto il
  vero `output/daily_report.json` del repo).
- ✅ **VERIFICATO** (fonte primaria, non ipotesi): le coordinate Gradle
  (`com.meta.wearable:mwdat-*:1.0.1`, Maven Central, nessun token), i
  permessi manifest, i meta-data `APPLICATION_ID`/`CLIENT_TOKEN`, e le firme
  delle API Kotlin usate in `RealGlassesSession.kt` (`Wearables.initialize`,
  `Wearables.startRegistration`, `Wearables.createSession`,
  `session.addDisplay()`, `session.addSpeech()`, `display.sendContent {
  flexBox { ... } }`, `speech.transcriptions`) — letti direttamente dal
  codice e dalla documentazione del repo ufficiale `facebook/meta-wearables-
  dat-android` (commit `f4371bc`), non da fonti terze.
- ⚠️ **IPOTESI (non verificato in questa sessione)**:
  - Nessuna compilazione reale: questo ambiente non ha Android SDK né
    emulatore, quindi `RealGlassesSession.kt` non è stato compilato né
    eseguito. La sintassi segue i sample ufficiali ma potrebbe avere piccoli
    errori di battitura non colti senza una build reale.
  - Nessun test contro hardware reale né contro MockDeviceKit (serve una
    macchina con Android Studio + dispositivo/emulatore).
  - Nessuna chiamata reale a un LLM nel backend (manca una `LLM_API_KEY`
    valida in questo ambiente).
  - `APPLICATION_ID`/`CLIENT_TOKEN` reali non ottenuti: in questa sessione
    nessuno ha un account sul Wearables Developer Center collegato.

**Non dichiarare "funziona con gli occhiali reali" finché non è stato
testato almeno con MockDeviceKit o hardware vero** — questa resta la regola
di tracciabilità del progetto.

## Struttura

```
rayban_display/
├── backend/                      # Proxy FastAPI verso l'LLM (invariato)
└── android/
    ├── local.properties.example   # mwdat_application_id / mwdat_client_token
    ├── gradle/libs.versions.toml  # versioni verificate (AGP 8.11.1, Kotlin 2.2.21, mwdat 1.0.1)
    └── app/src/main/java/com/zeus/raybandisplay/
        ├── RaybanDisplayApplication.kt  # Wearables.initialize(this)
        ├── ui/MainActivity.kt            # UI minima + wiring
        ├── net/AgentApiClient.kt         # client verso il backend
        └── glasses/
            ├── GlassesSession.kt          # interfaccia app-specifica
            └── RealGlassesSession.kt      # implementazione sulle API DAT reali
```

## Come avviare il backend (verificato)

```bash
cd rayban_display/backend
pip install -r requirements.txt
cp .env.example .env   # poi inserire una vera LLM_API_KEY (Groq/OpenAI-compatibile)
uvicorn app.main:app --reload --port 8000
```

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/agent/invoke \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s1", "text": "che ore sono?"}'
```

## Come procedere sull'app Android (passi concreti, non ancora eseguiti qui)

1. Vai su https://wearables.developer.meta.com, crea un account/organizzazione,
   crea un progetto e abilita la **Developer Mode** sull'app Meta AI del tuo
   telefono (richiede Android 10+ e l'app Meta AI installata).
2. Apri `rayban_display/android/` in Android Studio (Flamingo o più recente).
   Lo SDK Android e il Gradle wrapper servono una toolchain reale che questo
   ambiente cloud non ha.
3. Copia `local.properties.example` in `local.properties` (già in
   `.gitignore`); in Developer Mode puoi lasciare `0`/`0`.
4. `./gradlew assembleDebug` per la prima build. Se fallisce per versioni di
   AGP/Kotlin/SDK, allinea `gradle/libs.versions.toml` a quanto richiesto
   dalla tua installazione di Android Studio.
5. Per testare senza occhiali fisici, usa `MockDeviceKit`
   (`mwdat-mockdevice`, già in `build.gradle.kts`): `MockDeviceKit
   .getInstance(context).enable()`, poi `pairGlasses(GlassesModel.RAYBAN_META)`,
   e per la voce `glasses.services.speech.simulateTranscription("...", isFinal
   = true)`. Pattern completo nel repo ufficiale,
   `.cursor/rules/mockdevice-testing.mdc` e
   `plugins/mwdat-android/skills/speech/SKILL.md`.
6. Per il device reale, abbina gli occhiali all'app Meta AI, abilita
   Developer Mode sul dispositivo, poi premi "Connetti" nell'app: parte la
   registrazione (`Wearables.startRegistration`), poi la sessione.
7. Prima di qualunque pubblicazione pubblica, verifica lo stato aggiornato di
   Speech/Display sul Developer Center: a oggi (2026-10-22) sono
   "experimental" e non pubblicabili sui canali pubblici di release.

## Note di sicurezza

- `RAYBAN_BACKEND_API_KEY` (opzionale in `.env`) protegge `/agent/invoke` con
  un header `X-API-Key`.
- Nessuna chiave è hardcoded: `LLM_API_KEY` nel backend e
  `mwdat_application_id`/`mwdat_client_token` nell'app passano da `.env` /
  `local.properties`, entrambi gitignored.
