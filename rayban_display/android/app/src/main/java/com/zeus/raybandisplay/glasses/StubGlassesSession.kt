package com.zeus.raybandisplay.glasses

import kotlinx.coroutines.delay

/**
 * Implementazione finta di [GlassesSession], usata finché non si ha accesso
 * al vero Meta Wearables DAT SDK. Serve a far compilare e girare l'app e il
 * flusso UI -> backend senza occhiali fisici collegati.
 *
 * ⚠️ IPOTESI: non parla con nessun dispositivo reale. `simulateTranscript`
 * è l'unico modo per "far parlare" l'utente finto in questa fase.
 *
 * Quando si collega l'SDK reale:
 * 1. Creare `RealGlassesSession` che implementa [GlassesSession] usando le
 *    classi del DAT SDK (sessione, callback microfono, API display).
 * 2. Nella UI, sostituire `StubGlassesSession()` con `RealGlassesSession(context)`.
 */
class StubGlassesSession : GlassesSession {
    private var listener: GlassesSessionListener? = null
    override var isConnected: Boolean = false
        private set

    override suspend fun connect() {
        delay(300) // finge una latenza di pairing
        isConnected = true
        listener?.onConnectionStateChanged(true)
    }

    override fun disconnect() {
        isConnected = false
        listener?.onConnectionStateChanged(false)
    }

    override fun setListener(listener: GlassesSessionListener) {
        this.listener = listener
    }

    override suspend fun showOnDisplay(title: String, body: String) {
        // Qui andrebbe la vera chiamata DAT per il rendering sul display.
        // Nello stub ci limitiamo a loggare, la UI Android mostra comunque
        // lo stesso testo a schermo.
    }

    /** Usato dalla UI per simulare l'arrivo di una frase dal microfono. */
    fun simulateTranscript(text: String) {
        listener?.onTranscript(text)
    }
}
