from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException

from .agent import AgentError, agent_runtime
from .config import settings
from .schemas import AgentInvokeRequest, AgentInvokeResponse, DisplayPayload, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await agent_runtime.aclose()


app = FastAPI(
    title="Rayban Display Agent Backend",
    description=(
        "Proxy tra l'app Android (Meta Wearables DAT) e un agente LLM con "
        "tool-calling. Vedi README.md per il flusso completo."
    ),
    lifespan=lifespan,
)


def _check_api_key(x_api_key: str | None) -> None:
    if settings.backend_api_key and x_api_key != settings.backend_api_key:
        raise HTTPException(status_code=401, detail="API key mancante o errata")


def _to_display(reply_text: str) -> DisplayPayload:
    limit = settings.display_max_chars
    truncated = len(reply_text) > limit
    body = reply_text[: limit - 1].rstrip() + "…" if truncated else reply_text
    return DisplayPayload(title="Assistente", body=body, truncated=truncated)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(model=settings.llm_model_name)


@app.post("/agent/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(
    request: AgentInvokeRequest,
    x_api_key: str | None = Header(default=None),
) -> AgentInvokeResponse:
    _check_api_key(x_api_key)

    try:
        reply_text, tool_calls = await agent_runtime.respond(request.session_id, request.text)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AgentInvokeResponse(
        session_id=request.session_id,
        reply_text=reply_text,
        display=_to_display(reply_text),
        tool_calls=tool_calls,
    )
