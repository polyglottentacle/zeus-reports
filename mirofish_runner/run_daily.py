from dotenv import load_dotenv
load_dotenv(r'C:/Users/docum/Desktop/zeus/.env')
import csv
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Python interpreter corretto: legge PYTHON_EXECUTABLE da .env o usa il percorso codex
_CODEX_PYTHON = r"C:\Users\docum\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
PYTHON_EXECUTABLE = (
    os.environ.get("PYTHON_EXECUTABLE")
    or (_CODEX_PYTHON if Path(_CODEX_PYTHON).exists() else sys.executable)
)

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
FREQTRADE_DATA_FILE = BASE_DIR.parent / "freqtrade" / "user_data" / "data" / "binance" / "BTC_USDT-1h.feather"
MAX_MIROFISH_AGENTS = 100


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


def _get_data_reference() -> str:
    if FREQTRADE_DATA_FILE.exists():
        return (
            "Use the last 30 days of BTC/USDT market data from Freqtrade "
            f"at {FREQTRADE_DATA_FILE}."
        )
    return "Use the Zeus BTC/USDT Freqtrade dataset if available."


def _build_agent_configs(agent_count: int = MAX_MIROFISH_AGENTS) -> List[Dict[str, Any]]:
    configs = []
    for agent_id in range(1, agent_count + 1):
        configs.append(
            {
                "agent_id": agent_id,
                "entity_uuid": f"zeus_agent_{agent_id}",
                "entity_name": f"Zeus Market Agent {agent_id}",
                "entity_type": "forecast",
                "activity_level": 0.5,
                "posts_per_hour": 0.5 + 0.3 * ((agent_id % 5) / 4),
                "comments_per_hour": 0.5,
                "active_hours": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
                "response_delay_min": 5,
                "response_delay_max": 40,
                "sentiment_bias": 0.0,
                "stance": "neutral",
                "influence_weight": 1.0,
            }
        )
    return configs


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
        "simulation_requirement": (
            "Generate a daily Zeus market forecast using the last 30 days of BTC/USDT data "
            "from Freqtrade, keeping the simulation under 40 rounds and within the Zeus agent limit."
        ),
        "time_config": {
            "total_simulation_hours": 40,
            "minutes_per_round": 60,
            "agents_per_hour_min": 20,
            "agents_per_hour_max": 60,
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [0, 1, 2, 3, 4, 5],
            "peak_activity_multiplier": 1.2,
            "off_peak_activity_multiplier": 0.2,
            "morning_activity_multiplier": 0.5,
            "work_activity_multiplier": 0.7,
        },
        "agent_configs": _build_agent_configs(),
        "event_config": {
            "initial_posts": [
                {
                    "content": (
                        "Use the last 30 days of BTC/USDT market performance from Zeus Freqtrade and "
                        "generate a market forecast focused on risk, sentiment, liquidity, and trading strategy."
                    ),
                    "author": "Zeus Forecast Agent",
                    "timestamp": timestamp,
                }
            ],
            "hot_topics": ["BTC/USDT", "crypto", "market sentiment", "risk", "volatility"],
            "narrative_direction": (
                "Focus on a low-budget forecast using 30 days of BTC/USDT input, constrained to 40 simulation rounds "
                "and a maximum of 500 agents."
            ),
            "source_data_reference": _get_data_reference(),
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


def _generate_agent_profiles(run_dir: Path, agent_count: int) -> None:
    """
    Genera i file profilo agenti richiesti da OASIS prima della simulazione.
    - twitter_profiles.csv  → colonne: user_char, username, description
    - reddit_profiles.json  → lista di {persona, mbti, gender, age, country, username, realname, bio}
    """
    # Archetipi trader BTC variati (bullish / bearish / neutral)
    _ARCHETYPES = [
        ("Retail crypto trader focused on momentum and trend following in BTC/USDT markets.",
         "ENFP", "M", 28, "Italy",   "momentum_mike",  "Mike Rossi",    "Crypto trader obsessed with BTC momentum plays."),
        ("Risk-averse institutional analyst who monitors macro signals and volatility regimes.",
         "INTJ", "F", 35, "Germany", "macro_hanna",    "Hanna Bauer",   "Quantitative analyst tracking macro + crypto correlations."),
        ("Contrarian bear who sees BTC valuations as fundamentally overextended.",
         "ISTP", "M", 42, "USA",     "bear_thesis",    "David Chen",    "Skeptical economist questioning crypto narratives."),
        ("Long-term HODLer who buys every dip and ignores short-term noise.",
         "INFJ", "F", 31, "Brazil",  "hodl_forever",   "Sofia Lima",    "Diamond-hand BTC hodler since 2017."),
        ("Algorithmic trader running Freqtrade strategies on BTC/USDT 1h timeframe.",
         "INTP", "M", 26, "Spain",   "algo_zeus",      "Carlos García", "Quant dev optimizing EMA+RSI+ADX strategies on Freqtrade."),
        ("Day trader focused on support/resistance levels and order flow.",
         "ESTP", "F", 29, "France",  "sr_trader",      "Julie Dubois",  "Technical analyst specializing in S/R levels and volume."),
        ("Crypto journalist covering market narratives and sentiment shifts.",
         "ENFJ", "M", 33, "UK",      "crypto_news",    "James Wilson",  "Journalist tracking crypto sentiment and market narratives."),
        ("Derivatives trader hedging BTC exposure using options and futures.",
         "ENTJ", "F", 38, "Japan",   "deriv_hedge",    "Yuki Tanaka",   "Options trader using BTC derivatives for portfolio hedging."),
        ("Retail investor who recently entered crypto and follows influencers.",
         "ISFP", "M", 22, "India",   "newbie_btc",     "Raj Patel",     "New crypto investor learning TA and following market news."),
        ("Portfolio manager balancing BTC allocation with traditional assets.",
         "ISTJ", "F", 45, "Canada",  "portfolio_mgr",  "Linda Clarke",  "Asset manager integrating BTC into diversified portfolios."),
    ]

    # Scala archetipi fino ad agent_count con varianti numeriche
    profiles_twitter = []
    profiles_reddit = []

    for i in range(agent_count):
        base = _ARCHETYPES[i % len(_ARCHETYPES)]
        idx = i // len(_ARCHETYPES)
        suffix = f"_{idx}" if idx > 0 else ""
        sentiment = ["bullish", "bearish", "neutral"][i % 3]

        char = f"{base[0]} Current market sentiment: {sentiment}."
        username = f"{base[4]}{suffix}"
        realname = base[5]
        description = f"{base[7] if idx == 0 else base[7].replace('.', f' (v{idx+1}).').replace('  ', ' ')}"

        profiles_twitter.append({
            "user_char": char,
            "username": username,
            "description": description,
        })
        profiles_reddit.append({
            "persona": char,
            "mbti": base[1],
            "gender": base[2],
            "age": base[3] + (idx * 2),
            "country": base[6] if isinstance(base[6], str) else base[6],
            "username": username,
            "realname": realname,
            "bio": description,
        })

    # Scrivi twitter_profiles.csv
    csv_path = run_dir / "twitter_profiles.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["user_char", "username", "description"])
        writer.writeheader()
        writer.writerows(profiles_twitter)

    # Scrivi reddit_profiles.json
    json_path = run_dir / "reddit_profiles.json"
    json_path.write_text(json.dumps(profiles_reddit, indent=2, ensure_ascii=False), encoding="utf-8")


def _run_mirofish_simulation() -> Dict:
    config = _build_simulation_config()
    run_timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    run_dir = MIROFISH_RUN_DIR / f"run_{run_timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Genera i profili agenti richiesti da OASIS prima della simulazione
    _generate_agent_profiles(run_dir, agent_count=MAX_MIROFISH_AGENTS)

    config_path = run_dir / "simulation_config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    env = os.environ.copy()
    for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL_NAME", "ZEP_API_KEY"]:
        value = _load_env_value(key)
        if value:
            env[key] = value

    command = [
        PYTHON_EXECUTABLE,
        str(MIROFISH_SIMULATION_SCRIPT),
        "--config",
        str(config_path),
        "--no-wait",
        "--max-rounds",
        "40",
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

    output_file = FORECAST_HISTORY_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    if output_file.exists():
        output_file = FORECAST_HISTORY_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')}.json"

    output_file.write_text(json.dumps(forecast, indent=2, ensure_ascii=False), encoding="utf-8")
    return forecast


if __name__ == "__main__":
    forecast = run_daily_scenarios()
    print(json.dumps(forecast, indent=2, ensure_ascii=False))


