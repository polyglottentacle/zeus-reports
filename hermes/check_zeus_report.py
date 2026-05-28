#!/usr/bin/env python3
"""
Zeus report contract check.

Fetches daily_report.json, validates the required operational fields, computes a
SHA256 fingerprint, checks freshness, and prints a compact JSON payload that
Hermes can use before giving a trading verdict.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print(json.dumps({"ok": False, "error": "requests is not installed"}))
    sys.exit(1)


DEFAULT_REPORT_URL = (
    "https://raw.githubusercontent.com/polyglottentacle/zeus-reports/main/output/daily_report.json"
)
DEFAULT_REPORT_FILE = Path(__file__).resolve().parent.parent / "output" / "daily_report.json"


def _get_path(data: dict, path: str) -> Any:
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def _parse_timestamp(value: str) -> datetime:
    if not value:
        raise ValueError("empty timestamp")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _verdict(extract: dict) -> str:
    sharpe = float(extract["sharpe"])
    dsr = float(extract["dsr"])
    kelly = float(extract["kelly_fraction"])
    scenarios = int(extract["scenario_count"])

    if sharpe <= 0 or kelly <= 0 or dsr < 0.5:
        return "RESTA_FLAT"
    if scenarios <= 0:
        return "RESTA_FLAT"
    return "TRADING_CANDIDATE"


def fetch_report(url: str) -> tuple[dict, str]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    raw = response.text
    return json.loads(raw), raw


def read_report_file(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw), raw


def build_payload(report: dict, raw: str, source: str, max_age_hours: float) -> dict:
    required_paths = [
        "timestamp",
        "backtest_summary.strategy_name",
        "backtest_summary.sharpe",
        "backtest_summary.profit_pct",
        "backtest_summary.drawdown_pct",
        "dsr.dsr",
        "kelly.kelly_fraction",
        "kelly.max_position_usdt",
        "costs.profit_netto_stimato",
        "mirofish.status",
        "mirofish.scenario_count",
        "mirofish.mirofish_run.total_actions",
    ]

    missing = []
    for path in required_paths:
        try:
            _get_path(report, path)
        except KeyError:
            missing.append(path)

    if missing:
        return {
            "ok": False,
            "source": source,
            "missing_fields": missing,
            "error": "daily_report.json is missing required fields",
        }

    timestamp = _get_path(report, "timestamp")
    report_time = _parse_timestamp(timestamp)
    age_hours = (datetime.now(timezone.utc) - report_time).total_seconds() / 3600.0

    extract = {
        "timestamp": timestamp,
        "strategy_name": _get_path(report, "backtest_summary.strategy_name"),
        "sharpe": _get_path(report, "backtest_summary.sharpe"),
        "profit_pct": _get_path(report, "backtest_summary.profit_pct"),
        "drawdown_pct": _get_path(report, "backtest_summary.drawdown_pct"),
        "dsr": _get_path(report, "dsr.dsr"),
        "kelly_fraction": _get_path(report, "kelly.kelly_fraction"),
        "max_position_usdt": _get_path(report, "kelly.max_position_usdt"),
        "profit_netto": _get_path(report, "costs.profit_netto_stimato"),
        "mirofish_status": _get_path(report, "mirofish.status"),
        "scenario_count": _get_path(report, "mirofish.scenario_count"),
        "total_actions": _get_path(report, "mirofish.mirofish_run.total_actions"),
    }

    return {
        "ok": True,
        "source": source,
        "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "age_hours": round(age_hours, 3),
        "fresh": age_hours <= max_age_hours,
        "max_age_hours": max_age_hours,
        "extract": extract,
        "verdict": _verdict(extract),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and extract Zeus daily report fields.")
    parser.add_argument("--url", default=DEFAULT_REPORT_URL, help="daily_report.json URL")
    parser.add_argument(
        "--file",
        default=str(DEFAULT_REPORT_FILE),
        help="local daily_report.json path used before URL when present",
    )
    parser.add_argument(
        "--url-only",
        action="store_true",
        help="skip local file fallback and fetch only from URL",
    )
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    args = parser.parse_args()

    try:
        report_file = Path(args.file)
        if not args.url_only and report_file.exists():
            report, raw = read_report_file(report_file)
            source = str(report_file)
        else:
            report, raw = fetch_report(args.url)
            source = args.url
        payload = build_payload(report, raw, source, args.max_age_hours)
    except Exception as exc:
        payload = {
            "ok": False,
            "source": args.url,
            "error": str(exc),
        }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
