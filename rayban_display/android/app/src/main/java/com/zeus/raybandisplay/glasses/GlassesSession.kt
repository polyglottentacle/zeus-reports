package com.zeus.raybandisplay.glasses

/**
 * Astrazione dell'app sopra il Meta Wearables Device Access Toolkit (DAT):
 * registrazione, sessione, display e speech.
 *
 * Le firme qui sotto riflettono le API reali documentate nel repo ufficiale
 * `facebook/meta-wearables-dat-android` (letto in questa sessione, commit
 * f4371bc, AGENTS.md + regole .cursor/rules/display-access.mdc e speech.mdc):
 * `Wearables.initialize`, `Wearables.startRegistration`,
 * `Wearables.createSession`, `session.addDisplay()`, `session.addSpeech()`.
 *
 * ⚠️ Speech e Display restano capability "experimental": si possono
 * sviluppare e testare ma non pubblicare ancora sui canali di release
 * pubblici di Meta (vedi plugins/mwdat-android/skills/speech/SKILL.md e
 * rayban_display/README.md).
 */
interface GlassesSession {
    /** true se la registrazione app↔Meta AI è completata (RegistrationState.REGISTERED). */
    val isRegistered: Boolean

    /** true se la sessione verso gli occhiali è DeviceSessionState.STARTED. */
    val isConnected: Boolean

    /** Avvia la registrazione (apre l'app Meta AI) e poi la sessione. */
    fun connect()

    /** Ferma display/speech e la sessione. */
    fun disconnect()

    fun setListener(listener: GlassesSessionListener)

    /** Mostra una card di testo sul display (sostituisce il contenuto precedente). */
    suspend fun showOnDisplay(title: String, body: String)
}

interface GlassesSessionListener {
    fun onRegistrationChanged(registered: Boolean)
    fun onConnectionStateChanged(connected: Boolean)

    /** Trascrizione FINALE dal riconoscimento vocale sugli occhiali (result.isFinal == true). */
    fun onTranscript(text: String)

    fun onError(message: String)
}
