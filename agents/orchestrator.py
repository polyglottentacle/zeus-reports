import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile
from agents.agent2_dsr import compute_dsr
from agents.agent3_kelly import compute_kelly_fraction
from agents.agent4_costs import estimate_costs
from agents import agent_udito, agent_vista, agent_preveggenza, agent_memoria, agent_equilibrio, agent_occhi
from mirofish_runner.run_daily import run_daily_scenarios


BASE_DIR = Path(__file__).resolve().parent.parent
FREQTRADE_RESULTS_DIR = BASE_DIR / "freqtrade" / "user_data" / "backtest_results"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MIROFISH_FORECAST_DIR = BASE_DIR / "mirofish_runner" / "forecast_history"


def _read_sharpe_from_meta(meta_path: Path) -> float:
    """Estrae lo Sharpe ratio dal .zip corrispondente al .meta.json."""
    try:
        zip_path = _zip_path_from_meta(meta_path)
        if not zip_path.exists():
            return float("-inf")
        with zipfile.ZipFile(zip_path, "r") as z:
            json_name = zip_path.stem + ".json"
            if json_name not in z.namelist():
                return float("-inf")
            content = json.loads(z.read(json_name).decode("utf-8"))
            payload = _unwrap_strategy_payload(content.get("strategy", content))
            sharpe = payload.get("sharpe")
            profit = payload.get("profit_total") or payload.get("profit_pct")
            # Salta strategie senza trades reali (profit=None)
            if profit is None:
                return float("-inf")
            return float(sharpe) if sharpe is not None else float("-inf")
    except Exception:
        return float("-inf")


def find_best_meta() -> Path:
    """Ritorna il .meta.json con il miglior Sharpe ratio tra tutti i backtest.
    Fallback al più recente se nessuno ha dati validi."""
    meta_files = list(FREQTRADE_RESULTS_DIR.glob("*.meta.json"))
    if not meta_files:
        return None

    scored = []
    for p in meta_files:
        sharpe = _read_sharpe_from_meta(p)
        scored.append((sharpe, p.stat().st_mtime, p))

    # Ordina: Sharpe desc, poi mtime desc come tiebreaker
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # Prendi il migliore con Sharpe reale, altrimenti il più recente
    best = scored[0][2]
    if scored[0][0] == float("-inf"):
        # Fallback: più recente
        best = max(meta_files, key=lambda p: p.stat().st_mtime)
    return best


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_meta(meta: dict) -> dict:
    if not isinstance(meta, dict):
        return {}
    if len(meta) == 1:
        first_value = next(iter(meta.values()))
        if isinstance(first_value, dict):
            return first_value
    return meta


def format_timestamp(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value), timezone.utc).isoformat()
        return str(value)
    except Exception:
        return str(value)


def find_latest_mirofish_forecast() -> Path:
    """Ritorna il forecast di OGGI solo se status=='ok' e enabled==True.
    Salta i file dentro mirofish_runs/. Restituisce None → riesegue fresh."""
    if not MIROFISH_FORECAST_DIR.exists():
        return None

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    forecast_files = sorted(
        MIROFISH_FORECAST_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for path in forecast_files:
        # Ignora file nelle sottocartelle (es. mirofish_runs/)
        if path.parent != MIROFISH_FORECAST_DIR:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Usa solo il forecast di oggi con status ok
        file_date = (data.get("timestamp") or "")[:10]
        if file_date == today and data.get("status") == "ok" and data.get("enabled"):
            return path

    return None  # nessun forecast valido oggi → orchestrator riesegue fresh


def load_mirofish_forecast(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _zip_path_from_meta(meta_path: Path) -> Path:
    zip_path = meta_path.with_suffix("")
    zip_path = zip_path.with_suffix("")
    return zip_path.with_suffix(".zip")


def _unwrap_strategy_payload(payload: dict) -> dict:
    if isinstance(payload, dict) and len(payload) == 1:
        first_value = next(iter(payload.values()))
        if isinstance(first_value, dict):
            return first_value
    return payload


def extract_backtest_metrics_from_zip(path: Path) -> dict:
    result = {}
    try:
        zip_path = _zip_path_from_meta(path)
        if not zip_path.exists():
            return result

        with zipfile.ZipFile(zip_path, "r") as z:
            json_name = zip_path.stem + ".json"
            if json_name not in z.namelist():
                return result

            content = json.loads(z.read(json_name).decode("utf-8"))
            strategy_payload = None
            if "strategy" in content:
                strategy_payload = _unwrap_strategy_payload(content["strategy"])
            elif "strategy_comparison" in content:
                strategy_payload = _unwrap_strategy_payload(content["strategy_comparison"])
            else:
                strategy_payload = content

            if isinstance(strategy_payload, dict):
                for key in [
                    "profit_pct",
                    "profit_total",
                    "profit_total_abs",
                    "max_relative_drawdown",
                    "max_drawdown_abs",
                    "trade_count",
                    "total_trades",
                    "trade_count_long",
                    "trade_count_short",
                    "winrate",
                    "cagr",
                    "sortino",
                    "sharpe",
                    "profit_factor",
                    "profit_mean",
                    "avg_profit_pct",
                    "avg_loss_pct",
                    "stake_amount",
                    "starting_balance",
                    "backtest_start",
                    "backtest_end",
                ]:
                    if key in strategy_payload:
                        result[key] = strategy_payload[key]

                trades = strategy_payload.get("trades")
                if isinstance(trades, list):
                    result["trades"] = trades
                    result["trade_count"] = len(trades)
                    result["total_trades"] = len(trades)

                performance = strategy_payload.get("performance")
                if isinstance(performance, dict):
                    for key in [
                        "profit_pct",
                        "drawdown_pct",
                        "trade_count",
                        "win_rate",
                        "avg_profit_pct",
                        "avg_loss_pct",
                    ]:
                        if key in performance:
                            result[key] = performance[key]

        if "profit_pct" not in result and "profit_total" in result:
            result["profit_pct"] = result["profit_total"]
        if "drawdown_pct" not in result and "max_relative_drawdown" in result:
            result["drawdown_pct"] = result["max_relative_drawdown"]
        if "trade_count" not in result:
            if "total_trades" in result:
                result["trade_count"] = result["total_trades"]
            elif "trade_count_long" in result and "trade_count_short" in result:
                result["trade_count"] = result["trade_count_long"] + result["trade_count_short"]
            elif "trade_count_long" in result:
                result["trade_count"] = result["trade_count_long"]

    except Exception:
        pass
    return result


def build_report() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    latest_meta = find_best_meta()

    if latest_meta is None:
        return {
            "timestamp": now,
            "status": "no data available",
            "message": "nessun dato disponibile",
            "backtest": None,
        }

    raw_meta = read_json(latest_meta)
    strategy_name = None
    if isinstance(raw_meta, dict) and len(raw_meta) == 1:
        first_key = next(iter(raw_meta))
        first_value = raw_meta[first_key]
        if isinstance(first_value, dict):
            strategy_name = first_key
            raw_meta = first_value

    meta = normalize_meta(raw_meta)
    summary = {
        "meta_file": str(latest_meta.name),
        "strategy_name": strategy_name or meta.get("strategy_name") or meta.get("strategy"),
        "run_id": meta.get("run_id"),
        "backtest_start_time": format_timestamp(meta.get("backtest_start_ts") or meta.get("backtest_start_time")),
        "backtest_end_time": format_timestamp(meta.get("backtest_end_ts") or meta.get("backtest_end_time")),
    }

    metrics = extract_backtest_metrics_from_zip(latest_meta)
    trades = metrics.pop("trades", [])
    summary.update(metrics)
    summary["timestamp"] = now

    dsr = compute_dsr(summary, trades)
    kelly = compute_kelly_fraction(summary, trades)
    costs = estimate_costs(summary, trades)

    # Sensi di Zeus: solo letture pubbliche, ZERO chiavi, ZERO rischio.
    # OHLCV fetchato una volta sola e condiviso tra Preveggenza/Memoria/Equilibrio.
    # Avvolti in try/except: nessun senso puo' mai uccidere il report.
    senses = {}

    try:
        senses["udito"] = agent_udito.listen()
    except Exception as exc:
        senses["udito"] = {"sense": "udito", "status": "error", "error": str(exc)}

    # Fetch OHLCV una volta, condiviso tra i 3 sensi analitici
    _shared_ohlcv = None
    try:
        senses["vista"] = agent_vista.see()
        # Vista ha gia' fetchato i dati — ri-fetch separato per i sensi analitici
        # (Vista usa limit=30, gli altri ne vogliono 60 per maggiore accuratezza)
        try:
            import ccxt as _ccxt
            _ex = _ccxt.kraken({"enableRateLimit": True})
            _shared_ohlcv = _ex.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=60)
        except Exception:
            _shared_ohlcv = None
    except Exception as exc:
        senses["vista"] = {"sense": "vista", "status": "error", "error": str(exc)}

    try:
        senses["preveggenza"] = agent_preveggenza.foresee(ohlcv=_shared_ohlcv)
    except Exception as exc:
        senses["preveggenza"] = {"sense": "preveggenza", "status": "error", "error": str(exc)}

    try:
        senses["memoria"] = agent_memoria.remember(ohlcv=_shared_ohlcv)
    except Exception as exc:
        senses["memoria"] = {"sense": "memoria", "status": "error", "error": str(exc)}

    try:
        senses["equilibrio"] = agent_equilibrio.balance(ohlcv=_shared_ohlcv)
    except Exception as exc:
        senses["equilibrio"] = {"sense": "equilibrio", "status": "error", "error": str(exc)}

    try:
        # Occhi: TradingAgents multi-agent — piu' lento, timeout gestito internamente
        senses["occhi"] = agent_occhi.look()
    except Exception as exc:
        senses["occhi"] = {"sense": "occhi", "status": "error", "error": str(exc)}

    mirofish_forecast = None
    latest_forecast_path = find_latest_mirofish_forecast()
    if latest_forecast_path is not None:
        mirofish_forecast = load_mirofish_forecast(latest_forecast_path)
        if mirofish_forecast:
            mirofish_forecast["loaded_from"] = str(latest_forecast_path.name)
            mirofish_forecast["message"] = (
                mirofish_forecast.get("message", "Loaded latest MiroFish forecast from disk.")
            )

    if mirofish_forecast is None:
        try:
            mirofish_forecast = run_daily_scenarios()
        except Exception as exc:
            mirofish_forecast = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "message": "MiroFish integration failed.",
                "error": str(exc),
                "scenario_count": 0,
                "scenarios": [],
            }

    strategy_status = {
        "backtest_file": summary["meta_file"],
        "run_id": summary.get("run_id"),
        "strategy_name": summary.get("strategy_name"),
        "dsr": dsr,
        "kelly": kelly,
        "costs": costs,
        "mirofish": {
            "status": mirofish_forecast.get("status"),
            "scenario_count": mirofish_forecast.get("scenario_count"),
            "message": mirofish_forecast.get("message"),
            "sentiment": mirofish_forecast.get("sentiment"),
        },
        "senses": {
            "udito": senses.get("udito", {}).get("verdict"),
            "vista": senses.get("vista", {}).get("verdict"),
            "preveggenza": senses.get("preveggenza", {}).get("verdict"),
            "memoria": senses.get("memoria", {}).get("verdict"),
            "equilibrio": senses.get("equilibrio", {}).get("verdict"),
            "occhi": senses.get("occhi", {}).get("verdict"),
        },
        "summary": summary,
    }

    report = {
        "timestamp": now,
        "status": "ok",
        "backtest_summary": summary,
        "dsr": dsr,
        "kelly": kelly,
        "costs": costs,
        "mirofish": mirofish_forecast,
        "senses": senses,
        "strategy_status": strategy_status,
    }
    return report


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _push_report_if_cloud() -> None:
    """Se siamo in cloud (deploy/push_report.sh esiste), pusha il report su GitHub."""
    push_script = BASE_DIR / "deploy" / "push_report.sh"
    if push_script.exists():
        import subprocess
        try:
            result = subprocess.run(
                ["bash", str(push_script)],
                capture_output=True, text=True, timeout=60
            )
            print(result.stdout.strip() or "[push] ok")
            if result.returncode != 0:
                print(f"[push] warning: {result.stderr.strip()}")
        except Exception as exc:
            print(f"[push] skip: {exc}")


def main() -> None:
    report = build_report()
    write_json(OUTPUT_DIR / "daily_report.json", report)
    write_json(OUTPUT_DIR / "strategy_status.json", report.get("strategy_status", {}))
    if report["status"] == "ok":
        print("daily_report.json aggiornato con backtest result.")
    else:
        print("daily_report.json aggiornato: nessun dato disponibile.")
    _push_report_if_cloud()


if __name__ == "__main__":
    main()
