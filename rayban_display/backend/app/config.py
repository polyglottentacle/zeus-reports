from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "llama3-8b-8192")
    backend_api_key: str = os.getenv("RAYBAN_BACKEND_API_KEY", "")
    display_max_chars: int = int(os.getenv("RAYBAN_DISPLAY_MAX_CHARS", "220"))
    session_history_turns: int = int(os.getenv("RAYBAN_SESSION_HISTORY_TURNS", "6"))


settings = Settings()
