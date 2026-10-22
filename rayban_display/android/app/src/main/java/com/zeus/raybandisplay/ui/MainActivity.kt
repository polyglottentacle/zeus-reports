package com.zeus.raybandisplay.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.zeus.raybandisplay.databinding.ActivityMainBinding
import com.zeus.raybandisplay.glasses.GlassesSessionListener
import com.zeus.raybandisplay.glasses.StubGlassesSession
import com.zeus.raybandisplay.net.AgentApiClient
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Schermata unica dello scheletro: pulsante "Connetti", pulsante "Simula voce"
 * (finché non c'è l'SDK DAT reale) e area che mostra l'ultima risposta
 * dell'agente, esattamente il testo che finirebbe sul display degli occhiali.
 *
 * Flusso: microfono occhiali (qui: simulato) -> GlassesSession -> questa
 * Activity -> AgentApiClient.invoke() -> backend FastAPI -> risposta ->
 * GlassesSession.showOnDisplay().
 */
class MainActivity : AppCompatActivity(), GlassesSessionListener {

    private lateinit var binding: ActivityMainBinding
    private val sessionId = UUID.randomUUID().toString()
    private val glassesSession = StubGlassesSession()
    private val apiClient = AgentApiClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        glassesSession.setListener(this)

        binding.connectButton.setOnClickListener {
            lifecycleScope.launch {
                binding.statusText.text = "Connessione…"
                glassesSession.connect()
            }
        }

        binding.simulateVoiceButton.setOnClickListener {
            val text = binding.voiceInput.text?.toString()?.trim().orEmpty()
            if (text.isNotEmpty()) {
                glassesSession.simulateTranscript(text)
            }
        }
    }

    override fun onConnectionStateChanged(connected: Boolean) {
        binding.statusText.text = if (connected) "Connesso agli occhiali (stub)" else "Disconnesso"
    }

    override fun onTranscript(text: String) {
        binding.replyText.text = "…"
        lifecycleScope.launch {
            runCatching { apiClient.invoke(sessionId, text) }
                .onSuccess { response ->
                    binding.replyText.text = response.display.body
                    glassesSession.showOnDisplay(response.display.title, response.display.body)
                }
                .onFailure { error ->
                    binding.replyText.text = "Errore agente: ${error.message}"
                }
        }
    }

    override fun onError(message: String) {
        binding.statusText.text = "Errore occhiali: $message"
    }
}
