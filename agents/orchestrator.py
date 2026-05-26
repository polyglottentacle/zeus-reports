import json
from datetime import datetime, timezone
from pathlib import Path
import zipfile
from agents.agent2_dsr import compute_dsr
from agents.agent3_kelly import compute_kelly_fraction
from agents.agent4_costs import estimate_costs


BASE_DIR = Path(__file__).resolve().parent.parent
FREQTRADE_RESULTS_DIR = BASE_DIR / "freqtrade" / "user_data" / "backtest_results"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_latest_meta() -> Path:
    meta_files = sorted(
        FREQTRADE_RESULTS_DIR.glob("*.meta.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return meta_files[0] if meta_files else None


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


def extract_backtest_metrics_from_zip(path: Path) -> dict:
    result = {}
    try:
        zip_path = path.with_suffix("").with_suffix(".zip")
        if not zip_path.exists():
            return result

        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                if not name.endswith(".json"):
                    continue
                if name.endswith("_config.json"):
                    continue

                try:
                    content = json.loads(z.read(name).decode("utf-8"))
                except Exception:
                    continue

                if not isinstance(content, dict):
                    continue

                strategy_payload = None
                if "strategy" in content and isinstance(content["strategy"], dict):
                    nested = content["strategy"]
                    if len(nested) == 1 and isinstance(next(iter(nested.values())), dict):
                        strategy_payload = next(iter(nested.values()))
                    else:
                        strategy_payload = nested
                elif "strategy_comparison" in content and isinstance(content["strategy_comparison"], dict):
                    nested = content["strategy_comparison"]
                    if len(nested) == 1 and isinstance(next(iter(nested.values())), dict):
                        strategy_payload = next(iter(nested.values()))
                    else:
                        strategy_payload = nested
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
                    ]:
                        if key in strategy_payload:
                            result[key] = strategy_payload[key]

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
    latest_meta = find_latest_meta()

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
    summary.update(metrics)
    summary["timestamp"] = now

    dsr = compute_dsr(summary)
    kelly = compute_kelly_fraction(summary)
    costs = estimate_costs(summary)

    strategy_status = {
        "backtest_file": summary["meta_file"],
        "run_id": summary.get("run_id"),
        "strategy_name": summary.get("strategy_name"),
        "dsr": dsr,
        "kelly": kelly,
        "costs": costs,
        "summary": summary,
    }

    report = {
        "timestamp": now,
        "status": "ok",
        "backtest_summary": summary,
        "dsr": dsr,
        "kelly": kelly,
        "costs": costs,
        "strategy_status": strategy_status,
    }
    return report


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_json(OUTPUT_DIR / "daily_report.json", report)
    write_json(OUTPUT_DIR / "strategy_status.json", report.get("strategy_status", {}))
    if report["status"] == "ok":
        print("daily_report.json aggiornato con backtest result.")
    else:
        print("daily_report.json aggiornato: nessun dato disponibile.")


if __name__ == "__main__":
    main()
