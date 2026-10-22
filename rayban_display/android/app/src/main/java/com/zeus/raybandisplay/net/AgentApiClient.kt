package com.zeus.raybandisplay.net

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.Header
import retrofit2.http.POST

interface AgentApi {
    @POST("agent/invoke")
    suspend fun invoke(
        @Body request: AgentInvokeRequest,
        @Header("X-API-Key") apiKey: String?,
    ): AgentInvokeResponse
}

/**
 * Client minimale verso il backend FastAPI in rayban_display/backend.
 * baseUrl punta di default al dev server locale (es. tramite adb reverse
 * tcp:8000 tcp:8000, o l'IP della macchina sulla stessa rete del telefono).
 */
class AgentApiClient(
    private val baseUrl: String = "http://10.0.2.2:8000/",
    private val apiKey: String? = null,
) {
    private val api: AgentApi by lazy {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .build()
        val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(AgentApi::class.java)
    }

    suspend fun invoke(sessionId: String, text: String): AgentInvokeResponse {
        return api.invoke(AgentInvokeRequest(sessionId = sessionId, text = text), apiKey)
    }
}
