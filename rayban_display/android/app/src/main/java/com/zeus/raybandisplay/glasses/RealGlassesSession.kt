package com.zeus.raybandisplay.glasses

import android.app.Activity
import android.util.Log
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.display.Display
import com.meta.wearable.dat.display.addDisplay
import com.meta.wearable.dat.display.removeDisplay
import com.meta.wearable.dat.display.types.DisplayState
import com.meta.wearable.dat.display.views.FlexBoxBackground
import com.meta.wearable.dat.display.views.TextStyle
import com.meta.wearable.dat.speech.Speech
import com.meta.wearable.dat.speech.addSpeech
import com.meta.wearable.dat.speech.removeSpeech
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch

private const val TAG = "RealGlassesSession"

/**
 * Implementazione reale di [GlassesSession] sul DAT SDK.
 *
 * ⚠️ IPOTESI (non verificato in questa sessione, nessun Android SDK/toolchain
 * disponibile qui): le chiamate seguono esattamente i pattern documentati nel
 * repo ufficiale (`AGENTS.md`, `display-access.mdc`, `speech.mdc` di
 * facebook/meta-wearables-dat-android, commit f4371bc), ma il codice non è
 * stato compilato né eseguito contro hardware reale o MockDeviceKit in
 * questo ambiente. Per testare senza occhiali fisici, usare `mwdat-mockdevice`
 * (già incluso in build.gradle.kts) seguendo samples/DisplayAccess e
 * plugins/mwdat-android/skills/speech/SKILL.md del repo ufficiale.
 *
 * Nota: Speech e Display sono capability "experimental" — si possono
 * sviluppare/testare ma Meta non ne consente ancora la pubblicazione sui
 * canali di release pubblici (vedi rayban_display/README.md).
 */
class RealGlassesSession(
    private val activity: Activity,
    private val scope: CoroutineScope,
) : GlassesSession {

    private var listener: GlassesSessionListener? = null
    private var session: DeviceSession? = null
    private var display: Display? = null
    private var speech: Speech? = null
    private var isDisplayReady: Boolean = false

    override var isRegistered: Boolean = false
        private set
    override var isConnected: Boolean = false
        private set

    override fun setListener(listener: GlassesSessionListener) {
        this.listener = listener
    }

    override fun connect() {
        scope.launch {
            Wearables.registrationState.collect { state ->
                isRegistered = state == RegistrationState.REGISTERED
                listener?.onRegistrationChanged(isRegistered)
                if (isRegistered && session == null) {
                    startSession()
                }
            }
        }
        Wearables.startRegistration(activity)
    }

    private fun startSession() {
        val selector = AutoDeviceSelector(filter = { device -> device.isDisplayCapable() })
        Wearables.createSession(selector).fold(
            onSuccess = { newSession ->
                session = newSession
                scope.launch {
                    newSession.errors.collect { error ->
                        Log.e(TAG, "session error: ${error.description}")
                        listener?.onError(error.description)
                    }
                }
                scope.launch {
                    newSession.state.collect { state ->
                        isConnected = state == DeviceSessionState.STARTED
                        listener?.onConnectionStateChanged(isConnected)
                        if (state == DeviceSessionState.STARTED) {
                            attachDisplay(newSession)
                            attachSpeech(newSession)
                        }
                    }
                }
                newSession.start()
            },
            onFailure = { error, _ ->
                Log.e(TAG, "createSession failed: ${error.description}")
                listener?.onError(error.description)
            },
        )
    }

    private fun attachDisplay(activeSession: DeviceSession) {
        if (display != null) return
        activeSession.addDisplay().fold(
            onSuccess = { newDisplay ->
                display = newDisplay
                scope.launch {
                    newDisplay.state.collect { state ->
                        isDisplayReady = state == DisplayState.STARTED
                    }
                }
            },
            onFailure = { error, _ ->
                Log.e(TAG, "addDisplay failed: ${error.description}")
                listener?.onError(error.description)
            },
        )
    }

    private fun attachSpeech(activeSession: DeviceSession) {
        if (speech != null) return
        activeSession.addSpeech().fold(
            onSuccess = { newSpeech ->
                speech = newSpeech
                scope.launch {
                    newSpeech.transcriptions.collect { result ->
                        result ?: return@collect
                        if (result.isFinal) listener?.onTranscript(result.text)
                    }
                }
                scope.launch {
                    newSpeech.state.collect { state ->
                        Log.d(TAG, "speech state: $state")
                    }
                }
                newSpeech.start().onFailure { error, _ ->
                    Log.e(TAG, "speech.start failed: ${error.description}")
                    listener?.onError(error.description)
                }
            },
            onFailure = { error, _ ->
                Log.e(TAG, "addSpeech failed: ${error.description}")
                listener?.onError(error.description)
            },
        )
    }

    override suspend fun showOnDisplay(title: String, body: String) {
        val activeDisplay = display ?: return
        if (!isDisplayReady) {
            Log.w(TAG, "showOnDisplay ignorato: display non ancora STARTED")
            return
        }
        activeDisplay.sendContent {
            flexBox(gap = 12, padding = 24, background = FlexBoxBackground.CARD) {
                text(title, style = TextStyle.HEADING)
                text(body, style = TextStyle.BODY)
            }
        }.onFailure { error, _ ->
            Log.e(TAG, "sendContent failed: ${error.description}")
            listener?.onError(error.description)
        }
    }

    override fun disconnect() {
        speech?.stop()
        session?.removeSpeech()
        session?.removeDisplay()
        session?.stop()
        speech = null
        display = null
        session = null
        isConnected = false
        isDisplayReady = false
    }
}
