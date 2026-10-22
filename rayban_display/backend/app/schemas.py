from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgentInvokeRequest(BaseModel):
    session_id: str = Field(..., description="ID stabile per occhiali/utente, generato dall'app Android")
    text: str = Field(..., description="Trascrizione vocale (o testo) catturata dal microfono dei Ray-Ban")
    source: Literal["voice", "text"] = "voice"


class DisplayPayload(BaseModel):
    title: str
    body: str
    truncated: bool = False


class AgentInvokeResponse(BaseModel):
    session_id: str
    reply_text: str
    display: DisplayPayload
    tool_calls: list[str] = Field(default_factory=list, description="Nomi dei tool invocati durante il turno")


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    model: str
