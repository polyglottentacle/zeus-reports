package com.zeus.raybandisplay.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.zeus.raybandisplay.databinding.ActivityMainBinding
import com.zeus.raybandisplay.glasses.GlassesSessionListener
import com.zeus.raybandisplay.glasses.RealGlassesSession
import com.zeus.raybandisplay.net.AgentApiClient
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Flusso: microfono occhiali -> DAT (speech) -> questa Activity ->
 * AgentApiClient.invoke() -> backend FastAPI -> risposta -> DAT (display).
 *
 * Senza occhiali fisici, testare con MockDeviceKit (mwdat-mockdevice, già in
 * build.gradle.kts): vedi rayban_display/README.md e
 * facebook/meta-wearables-dat-android, plugins/mwdat-android/skills/speech/SKILL.md
 * per `glasses.services.speech.simulateTranscription(...)`.
 */
class MainActivity : AppCompatActivity(), GlassesSessionListener {

    private lateinit var binding: ActivityMainBinding
    private val sessionId = UUID.randomUUID().toString()
    private val apiClient = AgentApiClient()
    private lateinit var glassesSession: RealGlassesSession

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        glassesSession = RealGlassesSession(activity = this, scope = lifecycleScope)
        glassesSession.setListener(this)

        binding.connectButton.setOnClickListener {
            binding.statusText.text = "Registrazione con Meta AI…"
            glassesSession.connect()
        }

        // Ingresso manuale, utile per testare senza microfono/occhiali reali.
        binding.simulateVoiceButton.setOnClickListener {
            val text = binding.voiceInput.text?.toString()?.trim().orEmpty()
            if (text.isNotEmpty()) {
                onTranscript(text)
            }
        }
    }

    override fun onRegistrationChanged(registered: Boolean) {
        binding.statusText.text = if (registered) "Registrato, avvio sessione…" else "Non registrato"
    }

    override fun onConnectionStateChanged(connected: Boolean) {
        binding.statusText.text = if (connected) "Connesso agli occhiali" else "Sessione non attiva"
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
        binding.statusText.text = "Errore DAT: $message"
    }

    override fun onDestroy() {
        glassesSession.disconnect()
        super.onDestroy()
    }
}
