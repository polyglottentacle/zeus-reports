package com.zeus.raybandisplay.net

import com.squareup.moshi.Json

data class AgentInvokeRequest(
    @Json(name = "session_id") val sessionId: String,
    val text: String,
    val source: String = "voice",
)

data class DisplayPayload(
    val title: String,
    val body: String,
    val truncated: Boolean,
)

data class AgentInvokeResponse(
    @Json(name = "session_id") val sessionId: String,
    @Json(name = "reply_text") val replyText: String,
    val display: DisplayPayload,
    @Json(name = "tool_calls") val toolCalls: List<String> = emptyList(),
)
