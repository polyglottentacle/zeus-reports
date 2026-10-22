"""Runtime dell'agente vocale: chiama un endpoint LLM compatibile OpenAI
(es. Groq, come già configurato in zeus/.env con LLM_API_KEY/LLM_BASE_URL/
LLM_MODEL_NAME) con tool-calling, e tiene una history breve per session_id.

Questo modulo è agnostico rispetto al tipo di agente collegato: non assume
Zeus, non assume MiroFish. `tools.py` è l'unico punto di contatto opzionale
con il resto del repo (tool `zeus_status`), e può essere rimosso senza
rompere nulla.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from typing import Deque

import httpx

from .config import settings
from .tools import TOOL_REGISTRY, TOOL_SPECS

logger = logging.getLogger("rayban_display.agent")

SYSTEM_PROMPT = (
    "Sei un assistente vocale che risponde a un utente che indossa un "
    "visore Ray-Ban Meta Display. Il tuo testo appare su un display minuscolo: "
    "rispondi SEMPRE in 1-2 frasi brevi, massimo circa 40 parole, senza markdown. "
    "Usa i tool disponibili quando la domanda lo richiede invece di inventare dati."
)

MAX_TOOL_ITERATIONS = 3


class AgentError(RuntimeError):
    pass


class AgentRuntime:
    def __init__(self) -> None:
        self._history: dict[str, Deque[dict]] = defaultdict(
            lambda: deque(maxlen=settings.session_history_turns * 2)
        )
        self._client = httpx.AsyncClient(
            base_url=settings.llm_base_url,
            timeout=20.0,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def respond(self, session_id: str, user_text: str) -> tuple[str, list[str]]:
        if not settings.llm_api_key:
            raise AgentError("LLM_API_KEY non configurata: impostala in backend/.env")

        history = self._history[session_id]
        history.append({"role": "user", "content": user_text})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history]
        tool_calls_used: list[str] = []

        for _ in range(MAX_TOOL_ITERATIONS):
            completion = await self._call_llm(messages)
            choice = completion["choices"][0]["message"]
            tool_calls = choice.get("tool_calls")

            if not tool_calls:
                reply_text = (choice.get("content") or "").strip()
                history.append({"role": "assistant", "content": reply_text})
                return reply_text, tool_calls_used

            messages.append(choice)
            for call in tool_calls:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}

                tool_fn = TOOL_REGISTRY.get(name)
                result = tool_fn(args) if tool_fn else f"Tool sconosciuto: {name}"
                tool_calls_used.append(name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": result,
                    }
                )

        raise AgentError("Troppi tool-call consecutivi senza una risposta finale")

    async def _call_llm(self, messages: list[dict]) -> dict:
        payload = {
            "model": settings.llm_model_name,
            "messages": messages,
            "tools": TOOL_SPECS,
            "tool_choice": "auto",
        }
        resp = await self._client.post("/chat/completions", json=payload)
        if resp.status_code >= 400:
            logger.error("LLM error %s: %s", resp.status_code, resp.text)
            raise AgentError(f"LLM ha risposto {resp.status_code}")
        return resp.json()


agent_runtime = AgentRuntime()
