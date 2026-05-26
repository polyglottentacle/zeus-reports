import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = BASE_DIR / "scenarios"
FORECAST_HISTORY_DIR = BASE_DIR / "forecast_history"
FORECAST_HISTORY_DIR.mkdir(parents=True, exist_ok=True)

ROOT_ENV_PATH = BASE_DIR.parent / ".env"
MIROFISH_ROOT = BASE_DIR.parent / "MiroFish"
MIROFISH_BACKEND = MIROFISH_ROOT / "backend"
MIROFISH_SIMULATION_SCRIPT = MIROFISH_BACKEND / "scripts" / "run_parallel_simulation.py"
MIROFISH_RUN_DIR = FORECAST_HISTORY_DIR / "mirofish_runs"
MIROFISH_RUN_DIR.mkdir(parents=True, exist_ok=True)


def _load_env_value(name: str) -> Optional[str]:
    value = os.environ.get(name)
    if value:
        return value.strip().strip('"').strip("'")

    if not ROOT_ENV_PATH.exists():
        return None

    for raw_line in ROOT_ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, val = line.split("=", 1)
        if key.strip() != name:
            continue

        return val.strip().strip('"').strip("'")

    return None


def _collect_existing_scenarios() -> List[Dict]:
    scenarios = []
    if not SCENARIOS_DIR.exists():
        return scenarios

    for scenario_file in sorted(SCENARIOS_DIR.glob("*.json")):
        try:
            scenarios.append(json.loads(scenario_file.read_text(encoding="utf-8")))
        except Exception:
            continue
    return scenarios


def _count_jsonl_records(path: Path) -> int:
    if not path.exists():
        return 0

    try:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except Exception:
        return 0


def _is_mirofish_available() -> bool:
    return MIROFISH_BACKEND.exists() and MIROFISH_SIMULATION_SCRIPT.exists()


def _get_mirofish_validation_errors() -> List[str]:
    errors = []
    if not _is_mirofish_available():
        errors.append(f"MiroFish repository missing at {MIROFISH_ROOT}.")

    if not _load_env_value("LLM_API_KEY"):
        errors.append("LLM_API_KEY not configured.")
    if not _load_env_value("ZEP_API_KEY"):
        errors.append("ZEP_API_KEY not configured.")

    return errors


def _build_simulation_config() -> Dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "simulation_id": f"zeus_mirofish_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "project_id": "zeus",
        "graph_id": "zeus_graph",
        "simulation_requirement": "Generate a short daily scenario forecast for Zeus using MiroFish.",
        "time_config": {
            "total_simulation_hours": 6,
            "minutes_per_round": 60,
            "agents_per_hour_min": 3,
            "agents_per_hour_max": 10,
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "peak_activity_multiplier": 1.2,
            "off_peak_activity_multiplier": 0.2,
            "morning_activity_multiplier": 0.5,
            "work_activity_multiplier": 0.7,
        },
        "agent_configs": [
            {
                "agent_id": 1,
                "entity_uuid": "zeus_forecast_agent_1",
                "entity_name": "Zeus Forecast Agent",
                "entity_type": "forecast",
                "activity_level": 0.5,
                "posts_per_hour": 1.0,
                "comments_per_hour": 0.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
                "response_delay_min": 5,
                "response_delay_max": 30,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0,
            }
        ],
        "event_config": {
            "initial_posts": [
                {
                    "content": "Generate a daily market forecast for Zeus operations, strategy, and sentiment.",
                    "author": "Zeus Forecast Agent",
                    "timestamp": timestamp,
                }
            ],
            "hot_topics": ["crypto", "trading", "market", "AI", "strategy"],
            "narrative_direction": "forecast market sentiment and risk factors relevant to the Zeus strategy.",
        },
        "twitter_config": {
            "platform": "twitter",
            "recency_weight": 0.4,
            "popularity_weight": 0.3,
            "relevance_weight": 0.3,
            "viral_threshold": 10,
            "echo_chamber_strength": 0.5,
        },
        "reddit_config": {
            "platform": "reddit",
            "recency_weight": 0.4,
            "popularity_weight": 0.3,
            "relevance_weight": 0.3,
            "viral_threshold": 10,
            "echo_chamber_strength": 0.5,
        },
        "llm_model": _load_env_value("LLM_MODEL_NAME") or "gpt-4o-mini",
        "llm_base_url": _load_env_value("LLM_BASE_URL") or "https://api.openai.com/v1",
        "generated_at": timestamp,
        "generation_reasoning": "Default Zeus daily forecast config generated for local MiroFish integration.",
    }


def _load_simulation_summary(simulation_dir: Path) -> Dict:
    twitter_actions_path = simulation_dir / "twitter" / "actions.jsonl"
    reddit_actions_path = simulation_dir / "reddit" / "actions.jsonl"

    return {
        "simulation_dir": str(simulation_dir),
        "twitter_actions": _count_jsonl_records(twitter_actions_path),
        "reddit_actions": _count_jsonl_records(reddit_actions_path),
        "total_actions": _count_jsonl_records(twitter_actions_path) + _count_jsonl_records(reddit_actions_path),
    }


def _run_mirofish_simulation() -> Dict:
    config = _build_simulation_config()
    run_timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    run_dir = MIROFISH_RUN_DIR / f"run_{run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "simulation_config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    env = os.environ.copy()
    for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME", "ZEP_API_KEY"]:
        value = _load_env_value(key)
        if value:
            env[key] = value

    command = [
        sys.executable,
        str(MIROFISH_SIMULATION_SCRIPT),
        "--config",
        str(config_path),
        "--no-wait",
        "--max-rounds",
        "8",
    ]

    result = subprocess.run(
        command,
        cwd=str(MIROFISH_BACKEND),
        capture_output=True,
        text=True,
        env=env,
        timeout=900,
    )

    summary = {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": " ".join(command),
    }

    if result.returncode != 0:
        raise RuntimeError(
            f"MiroFish simulation failed with return code {result.returncode}.\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )

    summary.update(_load_simulation_summary(run_dir))
    return summary


def _build_mirofish_forecast(existing_scenarios: List[Dict]) -> Dict:
    now = datetime.now(timezone.utc).isoformat()
    forecast = {
        "timestamp": now,
        "source": "mirofish",
        "enabled": False,
        "status": "disabled",
        "message": "MiroFish integration is not available.",
        "scenario_count": len(existing_scenarios),
        "scenarios": existing_scenarios,
        "recommendation": "Provide LLM_API_KEY and ZEP_API_KEY in the root .env and ensure MiroFish is cloned under the workspace.",
    }

    validation_errors = _get_mirofish_validation_errors()
    if validation_errors:
        forecast["errors"] = validation_errors
        return forecast

    try:
        simulation_summary = _run_mirofish_simulation()
        forecast.update(
            {
                "enabled": True,
                "status": "ok",
                "message": "MiroFish forecast generated successfully.",
                "mirofish_run": simulation_summary,
            }
        )
    except Exception as exc:
        forecast.update(
            {
                "status": "error",
                "message": "MiroFish simulation could not be completed.",
                "errors": [str(exc)],
            }
        )

    return forecast


def run_daily_scenarios() -> Dict:
    existing_scenarios = _collect_existing_scenarios()
    forecast = _build_mirofish_forecast(existing_scenarios)

    output_file = FORECAST_HISTORY_DIR / f"forecast_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.write_text(json.dumps(forecast, indent=2, ensure_ascii=False), encoding="utf-8")
    return forecast


if __name__ == "__main__":
    forecast = run_daily_scenarios()
    print(json.dumps(forecast, indent=2, ensure_ascii=False))
