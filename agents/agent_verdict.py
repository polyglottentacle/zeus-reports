"""
agent_verdict.py — Zeus Verdict Synthesizer

Prende l'output di tutti i sensi + MiroFish + backtest e produce:
  • zeus_verdict: "LONG" | "FLAT" | "SHORT" | "CAUTION"
  • zeus_score: float [-1.0, +1.0]  (negativo = bearish, 0 = neutro)
  • zeus_confidence: float [0.0, 1.0]
  • reasoning: lista di evidenze pesate

Questo è il segnale che Apollo DOVREBBE leggere prima di aprire un trade.

Logica di pesi (regolabili via .env):
  Vista        (trend BTC)       → peso 0.20
  Udito        (Fear & Greed)    → peso 0.15
  Preveggenza  (pattern/RSI)     → peso 0.20
  Memoria      (alpha factors)   → peso 0.15
  Equilibrio   (risk regime)     → peso 0.15
  Occhi        (TradingAgents)   → peso 0.10
  MiroFish     (social sim)      → peso 0.05

Regola di blocco:
  Se Equilibrio = EXTREME → forza FLAT indipendentemente dagli altri.
  Se Udito = EXTREME_FEAR + Vista = DOWNTREND → fattore penalty -0.25.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


# ─── PESI (sovrascrivibili via .env) ────────────────────────────────────────

W_VISTA        = float(os.environ.get("ZEUS_W_VISTA",       "0.20"))
W_UDITO        = float(os.environ.get("ZEUS_W_UDITO",       "0.15"))
W_PREVEGGENZA  = float(os.environ.get("ZEUS_W_PREV",        "0.20"))
W_MEMORIA      = float(os.environ.get("ZEUS_W_MEM",         "0.15"))
W_EQUILIBRIO   = float(os.environ.get("ZEUS_W_EQUIL",       "0.15"))
W_OCCHI        = float(os.environ.get("ZEUS_W_OCCHI",       "0.10"))
W_MIROFISH     = float(os.environ.get("ZEUS_W_MIRO",        "0.05"))

# Normalizza automaticamente i pesi a somma 1.0
_W_SUM = W_VISTA + W_UDITO + W_PREVEGGENZA + W_MEMORIA + W_EQUILIBRIO + W_OCCHI + W_MIROFISH
if _W_SUM > 0:
    W_VISTA       /= _W_SUM
    W_UDITO       /= _W_SUM
    W_PREVEGGENZA /= _W_SUM
    W_MEMORIA     /= _W_SUM
    W_EQUILIBRIO  /= _W_SUM
    W_OCCHI       /= _W_SUM
    W_MIROFISH    /= _W_SUM

LONG_THRESHOLD  = float(os.environ.get("ZEUS_LONG_THR",  "0.15"))
SHORT_THRESHOLD = float(os.environ.get("ZEUS_SHORT_THR", "-0.15"))


# ─── TRADUTTORI VERDICT → SCORE ─────────────────────────────────────────────

def _vista_score(verdict: str, change_pct: float = 0.0) -> float:
    mapping = {
        "UPTREND":   +0.8,
        "DOWNTREND": -0.8,
        "SIDEWAYS":   0.0,
        "VOLATILE":  -0.2,
    }
    base = mapping.get(verdict.upper() if verdict else "", 0.0)
    # aggiusta leggermente con momentum 24h
    momentum = max(-1.0, min(1.0, change_pct / 5.0))  # normalizza su range ±5%
    return round(base * 0.8 + momentum * 0.2, 4)


def _udito_score(verdict: str, value: int = 50) -> Tuple[float, bool]:
    """Restituisce (score, is_extreme_fear)."""
    if value <= 20:
        # Extreme Fear → contrarian → leggero bullish, ma trigger penalty con Vista
        return +0.3, True    # contrarian: prezzi bassi = opportunità
    if value <= 40:
        return +0.1, False   # Fear normale
    if value <= 60:
        return 0.0, False    # Neutral
    if value <= 80:
        return -0.1, False   # Greed → mercato surriscaldato
    return -0.3, False       # Extreme Greed → vendita imminente


def _preveggenza_score(verdict: str, confidence: float = 0.5) -> float:
    mapping = {"BULLISH": +1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}
    base = mapping.get(verdict.upper() if verdict else "", 0.0)
    return round(base * min(1.0, max(0.0, confidence)), 4)


def _memoria_score(verdict: str, alpha: float = 0.0) -> float:
    mapping = {"BULLISH": +1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}
    base = mapping.get(verdict.upper() if verdict else "", 0.0)
    # Alpha rinforza/attenua
    alpha_boost = max(-0.5, min(0.5, alpha * 2.0))
    return round(base * 0.7 + alpha_boost * 0.3, 4)


def _equilibrio_score(verdict: str, risk_regime: str = "MEDIUM") -> Tuple[float, bool]:
    """Restituisce (score, is_extreme)."""
    is_extreme = risk_regime.upper() == "EXTREME"
    risk_map = {"LOW": 0.0, "MEDIUM": -0.1, "HIGH": -0.3, "EXTREME": -0.8}
    verdict_map = {"EQUILIBRIUM": 0.0, "STRESS": -0.5}
    score = risk_map.get(risk_regime.upper(), 0.0) + verdict_map.get(verdict.upper() if verdict else "", 0.0)
    return round(max(-1.0, score), 4), is_extreme


def _occhi_score(verdict: str) -> float:
    """TradingAgents final decision → score."""
    mapping = {
        "BUY":         +1.0,
        "OVERWEIGHT":  +0.6,
        "HOLD":         0.0,
        "UNDERWEIGHT": -0.6,
        "SELL":        -1.0,
        "BULLISH":     +0.8,
        "BEARISH":     -0.8,
        "NEUTRAL":      0.0,
    }
    return mapping.get(verdict.upper() if verdict else "", 0.0)


def _mirofish_score(verdict: str, score: float = 0.5) -> float:
    mapping = {"BULLISH": +1.0, "BEARISH": -1.0, "NEUTRAL": 0.0}
    base = mapping.get(verdict.upper() if verdict else "", 0.0)
    # Normalizza score MiroFish da [0,1] a [-1,+1]
    mf_signal = (score - 0.5) * 2.0
    return round(base * 0.6 + mf_signal * 0.4, 4)


# ─── SYNTHESIZER ────────────────────────────────────────────────────────────

def synthesize(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sintetizza il verdetto Zeus da daily_report.json (o dict equivalente).
    Chiamato dall'orchestrator dopo aver raccolto tutti i sensi.
    """
    ts = datetime.now(tz=timezone.utc).isoformat()
    senses = report.get("senses", {})
    mirofish = report.get("mirofish", {})

    reasoning: List[dict] = []
    weighted_score = 0.0
    active_weights = 0.0

    # ── VISTA ──
    vista = senses.get("vista", {})
    v_verdict = vista.get("verdict", "")
    v_change  = vista.get("change_24h_pct", 0.0) or 0.0
    if vista.get("status") == "ok" and v_verdict:
        s = _vista_score(v_verdict, v_change)
        weighted_score += s * W_VISTA
        active_weights += W_VISTA
        reasoning.append({
            "sense": "vista", "verdict": v_verdict,
            "score": s, "weight": round(W_VISTA, 3),
            "detail": f"BTC {v_verdict} | Δ24h {v_change:+.2f}%"
        })

    # ── UDITO ──
    udito = senses.get("udito", {})
    u_verdict = udito.get("verdict", "")
    u_value   = udito.get("value", 50) or 50
    is_extreme_fear = False
    if udito.get("status") == "ok" and u_verdict:
        s, is_extreme_fear = _udito_score(u_verdict, u_value)
        weighted_score += s * W_UDITO
        active_weights += W_UDITO
        reasoning.append({
            "sense": "udito", "verdict": u_verdict,
            "score": s, "weight": round(W_UDITO, 3),
            "detail": f"F&G = {u_value} ({u_verdict})"
        })

    # ── PREVEGGENZA ──
    prev = senses.get("preveggenza", {})
    p_verdict    = prev.get("verdict", "")
    p_confidence = prev.get("confidence", 0.5) or 0.5
    if prev.get("status") == "ok" and p_verdict:
        s = _preveggenza_score(p_verdict, p_confidence)
        weighted_score += s * W_PREVEGGENZA
        active_weights += W_PREVEGGENZA
        reasoning.append({
            "sense": "preveggenza", "verdict": p_verdict,
            "score": s, "weight": round(W_PREVEGGENZA, 3),
            "detail": f"Pattern: {p_verdict} | conf {p_confidence:.0%}"
        })

    # ── MEMORIA ──
    mem = senses.get("memoria", {})
    m_verdict = mem.get("verdict", "")
    m_alpha   = mem.get("alpha_score", 0.0) or 0.0
    if mem.get("status") == "ok" and m_verdict:
        s = _memoria_score(m_verdict, m_alpha)
        weighted_score += s * W_MEMORIA
        active_weights += W_MEMORIA
        reasoning.append({
            "sense": "memoria", "verdict": m_verdict,
            "score": s, "weight": round(W_MEMORIA, 3),
            "detail": f"Alpha = {m_alpha:+.4f} ({m_verdict})"
        })

    # ── EQUILIBRIO ──
    equil = senses.get("equilibrio", {})
    e_verdict = equil.get("verdict", "")
    e_regime  = equil.get("risk_regime", "MEDIUM") or "MEDIUM"
    is_extreme_risk = False
    if equil.get("status") == "ok" and e_verdict:
        s, is_extreme_risk = _equilibrio_score(e_verdict, e_regime)
        weighted_score += s * W_EQUILIBRIO
        active_weights += W_EQUILIBRIO
        reasoning.append({
            "sense": "equilibrio", "verdict": e_verdict,
            "score": s, "weight": round(W_EQUILIBRIO, 3),
            "detail": f"Rischio: {e_regime} | {e_verdict}"
        })

    # ── OCCHI (TradingAgents) ──
    occhi = senses.get("occhi", {})
    o_verdict = occhi.get("verdict", "")
    if occhi.get("status") == "ok" and o_verdict:
        s = _occhi_score(o_verdict)
        weighted_score += s * W_OCCHI
        active_weights += W_OCCHI
        reasoning.append({
            "sense": "occhi", "verdict": o_verdict,
            "score": s, "weight": round(W_OCCHI, 3),
            "detail": f"TradingAgents: {o_verdict}"
        })

    # ── MIROFISH ──
    mf_sentiment = mirofish.get("sentiment", {}) or {}
    mf_verdict   = mf_sentiment.get("verdict", "")
    mf_score_raw = mf_sentiment.get("score", 0.5) or 0.5
    if mirofish.get("status") == "ok" and mf_verdict:
        s = _mirofish_score(mf_verdict, mf_score_raw)
        weighted_score += s * W_MIROFISH
        active_weights += W_MIROFISH
        reasoning.append({
            "sense": "mirofish", "verdict": mf_verdict,
            "score": s, "weight": round(W_MIROFISH, 3),
            "detail": f"Social sim: {mf_verdict} | score {mf_score_raw:.2f}"
        })

    # Normalizza per pesi attivi
    if active_weights > 0:
        normalized_score = weighted_score / active_weights
    else:
        normalized_score = 0.0

    # ── PENALTY RULES ──
    penalty_reasons = []

    # Rule 1: Extreme risk → FLAT forzato
    if is_extreme_risk:
        normalized_score = 0.0
        penalty_reasons.append("BLOCCO: risk_regime=EXTREME → forzato FLAT")

    # Rule 2: Extreme Fear + Downtrend → penalty -0.25
    if is_extreme_fear and v_verdict == "DOWNTREND":
        normalized_score = max(-1.0, normalized_score - 0.25)
        penalty_reasons.append("PENALTY: EXTREME_FEAR + DOWNTREND → -0.25 score")

    # ── FINAL VERDICT ──
    score_clamped = max(-1.0, min(1.0, normalized_score))

    if is_extreme_risk:
        final_verdict = "FLAT"
    elif score_clamped >= LONG_THRESHOLD:
        final_verdict = "LONG"
    elif score_clamped <= SHORT_THRESHOLD:
        final_verdict = "SHORT"
    else:
        final_verdict = "FLAT"

    # Confidence: quanti sensi sono attivi / peso coperto
    coverage = active_weights  # già normalizzato
    confidence = round(min(1.0, coverage + abs(score_clamped) * 0.3), 4)

    return {
        "zeus_verdict": final_verdict,
        "zeus_score": round(score_clamped, 4),
        "zeus_confidence": confidence,
        "active_senses": len(reasoning),
        "timestamp": ts,
        "reasoning": reasoning,
        "penalties": penalty_reasons,
        "thresholds": {
            "long": LONG_THRESHOLD,
            "short": SHORT_THRESHOLD,
        },
        "message": (
            f"Zeus dice {final_verdict} "
            f"(score={score_clamped:+.3f}, conf={confidence:.0%}, "
            f"sensi attivi={len(reasoning)}/7)"
        ),
    }


if __name__ == "__main__":
    import sys

    # Test: carica il report dal disco
    report_path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "output" / "daily_report.json"
    )
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report = {"senses": {}, "mirofish": {}}

    result = synthesize(report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0)
