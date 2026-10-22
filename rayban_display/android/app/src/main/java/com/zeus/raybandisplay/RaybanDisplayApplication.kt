package com.zeus.raybandisplay

import android.app.Application
import android.util.Log
import com.meta.wearable.dat.core.Wearables

private const val TAG = "RaybanDisplayApp"

/**
 * `Wearables.initialize(context)` deve girare una sola volta, prima di ogni
 * altra chiamata DAT (sessione, display, speech). Verificato in
 * facebook/meta-wearables-dat-android (AGENTS.md, sezione "Step 3: Initialize the SDK").
 */
class RaybanDisplayApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Wearables.initialize(this).onFailure { error, _ ->
            Log.e(TAG, "Inizializzazione DAT fallita: ${error.description}")
        }
    }
}
