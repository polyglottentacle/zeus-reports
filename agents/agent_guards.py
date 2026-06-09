"""
agent_guards.py - Zeus staging and guard layer.

Clean-room application of the Alice-style safety pattern:
verdict -> staged proposal -> guards -> human approval -> emitted signal.

This module never calls a broker and never edits Apollo. It only writes files
under output/staging so Zeus can keep a human checkpoint before zeus_signal.json
becomes actionable.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
STAGING_DIR = OUTPUT_DIR / "staging"
APPROVE_FILE = STAGING_DIR / "APPROVE.txt"
KILL_SWITCH_FILE = STAGING_DIR / "KILL_SWITCH"
AUDIT_LOG = STAGING_DIR / "audit.jsonl"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)).strip())
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.environ.get(name, str(default)).strip()))
    except Exception:
        return default


def _allowed_symbols() -> List[str]:
    raw = os.environ.get("ZEUS_ALLOWED_SYMBOLS", "BTC/USDT")
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _proposal_hash(stable_payload: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(stable_payload).encode("utf-8")).hexdigest()


def _read_approval_hashes() -> List[str]:
    if not APPROVE_FILE.exists():
        return []
    try:
        lines = APPROVE_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    hashes = []
    for line in lines:
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        hashes.append(clean.split()[0].lower())
    return hashes


def _append_audit(event: Dict[str, Any]) -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": _iso_now(), **event}
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


def _recent_approved_or_emitted(cooldown_minutes: int) -> Tuple[bool, str]:
    if cooldown_minutes <= 0 or not AUDIT_LOG.exists():
        return False, "cooldown disabled or no audit log"
    cutoff = _utc_now() - timedelta(minutes=cooldown_minutes)
    try:
        lines = AUDIT_LOG.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False, "audit log unreadable"
    for line in reversed(lines[-500:]):
        try:
            event = json.loads(line)
            state = str(event.get("state", "")).upper()
            ts = datetime.fromisoformat(str(event.get("timestamp", "")).replace("Z", "+00:00"))
        except Exception:
            continue
        if state in {"APPROVED", "EMITTED"} and ts >= cutoff:
            age = int((_utc_now() - ts).total_seconds() // 60)
            return True, f"last {state.lower()} event {age} minutes ago"
    return False, "no recent approved/emitted event"


def build_proposal(verdict_data: Dict[str, Any], component_status: Dict[str, Any] | None = None) -> Dict[str, Any]:
    symbol = os.environ.get("ZEUS_SYMBOL", "BTC/USDT").strip().upper() or "BTC/USDT"
    verdict = str(verdict_data.get("zeus_verdict", "FLAT")).upper()
    theoretical_notional = _env_float("ZEUS_THEORETICAL_NOTIONAL_USDT", 0.0)

    stable_payload = {
        "symbol": symbol,
        "verdict": verdict,
        "score": round(float(verdict_data.get("zeus_score", 0.0) or 0.0), 4),
        "confidence": round(float(verdict_data.get("zeus_confidence", 0.0) or 0.0), 4),
        "active_senses": int(verdict_data.get("active_senses", 0) or 0),
        "message": str(verdict_data.get("message", "")),
        "mode": "PAPER",
        "theoretical_notional_usdt": theoretical_notional,
    }
    h = _proposal_hash(stable_payload)
    return {
        "proposal_hash": h,
        "short_hash": h[:12],
        "created_at": _iso_now(),
        "state": "PENDING",
        "stable_payload": stable_payload,
        "component_status": component_status or {},
        "source": "zeus.agent_verdict",
        "approval": {
            "file": str(APPROVE_FILE),
            "instruction": f"Write this hash on its own line in APPROVE.txt to approve: {h}",
        },
    }


def run_guards(proposal: Dict[str, Any]) -> Dict[str, Any]:
    payload = proposal.get("stable_payload", {})
    verdict = str(payload.get("verdict", "FLAT")).upper()
    symbol = str(payload.get("symbol", "")).upper()
    notional = float(payload.get("theoretical_notional_usdt", 0.0) or 0.0)
    max_notional = _env_float("ZEUS_MAX_THEORETICAL_NOTIONAL_USDT", 100.0)
    cooldown_minutes = _env_int("ZEUS_PROPOSAL_COOLDOWN_MINUTES", 60)

    checks = []

    kill_active = _env_bool("ZEUS_KILL_SWITCH", False) or KILL_SWITCH_FILE.exists()
    checks.append({
        "name": "kill_switch",
        "passed": not kill_active,
        "detail": "kill switch inactive" if not kill_active else "kill switch active",
    })

    allowed = _allowed_symbols()
    checks.append({
        "name": "symbol_whitelist",
        "passed": symbol in allowed,
        "detail": f"{symbol} in {allowed}" if symbol in allowed else f"{symbol} not in {allowed}",
    })

    checks.append({
        "name": "size_cap",
        "passed": notional <= max_notional,
        "detail": f"{notional:.2f} <= {max_notional:.2f} USDT theoretical",
    })

    recent, recent_detail = _recent_approved_or_emitted(cooldown_minutes)
    checks.append({
        "name": "cooldown",
        "passed": (verdict == "FLAT") or (not recent),
        "detail": recent_detail,
    })

    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "state": "GUARDED" if passed else "REJECTED",
        "checks": checks,
    }


def approval_status(proposal: Dict[str, Any], guard_result: Dict[str, Any]) -> Dict[str, Any]:
    proposal_hash = str(proposal.get("proposal_hash", "")).lower()
    approvals = _read_approval_hashes()
    approved = guard_result.get("passed") is True and proposal_hash in approvals
    return {
        "approved": approved,
        "state": "APPROVED" if approved else "PENDING_APPROVAL",
        "approve_file": str(APPROVE_FILE),
        "proposal_hash": proposal_hash,
    }


def stage_and_gate(verdict_data: Dict[str, Any], component_status: Dict[str, Any] | None = None) -> Dict[str, Any]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    proposal = build_proposal(verdict_data, component_status=component_status)
    guard_result = run_guards(proposal)
    approval = approval_status(proposal, guard_result)

    state = approval["state"] if guard_result["passed"] else guard_result["state"]
    staged = {
        **proposal,
        "state": state,
        "guards": guard_result,
        "approval_status": approval,
    }

    proposal_path = STAGING_DIR / f"proposal_{proposal['short_hash']}.json"
    proposal_path.write_text(json.dumps(staged, indent=2, ensure_ascii=True), encoding="utf-8")
    (STAGING_DIR / "latest_proposal.json").write_text(
        json.dumps(staged, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    _append_audit({
        "state": state,
        "proposal_hash": proposal["proposal_hash"],
        "short_hash": proposal["short_hash"],
        "verdict": proposal["stable_payload"]["verdict"],
        "guard_passed": guard_result["passed"],
        "approved": approval["approved"],
        "proposal_file": str(proposal_path),
    })
    return {
        "proposal": staged,
        "approved": approval["approved"],
        "proposal_file": str(proposal_path),
    }
