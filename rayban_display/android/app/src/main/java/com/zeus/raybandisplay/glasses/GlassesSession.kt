package com.zeus.raybandisplay.glasses

/**
 * Astrazione sulla sessione verso i Ray-Ban Meta (via Device Access Toolkit).
 *
 * ⚠️ IPOTESI — nessuna implementazione reale del DAT SDK è disponibile in
 * questo ambiente di sviluppo: l'SDK è distribuito tramite Developer Preview
 * gated (wearables.developer.meta.com) e non è stato possibile scaricarlo né
 * testarlo qui. Questa interfaccia riflette il flusso descritto nella doc
 * pubblica di Meta (sessione → eventi microfono → render su display), ma le
 * firme esatte delle classi DAT reali vanno verificate e adattate quando si
 * ha accesso all'SDK.
 */
interface GlassesSession {
    /** Apre la sessione verso l'app Meta AI / gli occhiali associati. */
    suspend fun connect()

    /** Chiude la sessione e libera le risorse. */
    fun disconnect()

    /** true se la sessione è attualmente connessa a un paio di occhiali. */
    val isConnected: Boolean

    /** Registra un listener per gli eventi di trascrizione vocale e di stato. */
    fun setListener(listener: GlassesSessionListener)

    /** Invia un testo da mostrare sul display degli occhiali. */
    suspend fun showOnDisplay(title: String, body: String)
}

interface GlassesSessionListener {
    /** Chiamato quando il microfono degli occhiali produce una trascrizione finale. */
    fun onTranscript(text: String)

    /** Chiamato quando lo stato della connessione cambia. */
    fun onConnectionStateChanged(connected: Boolean)

    /** Chiamato su errori non recuperabili della sessione DAT. */
    fun onError(message: String)
}
