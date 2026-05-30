#!/usr/bin/env python3
"""
NSE Proactive Signal Engine v2 — Tier 2
=========================================
Proactive: verifies predictions, tracks key levels, generates weekly outlook.

Usage:
  python3 nse_signal_engine.py --verify PATH       Verify morning bias vs actual close
  python3 nse_signal_engine.py --levels             Compute Nifty key levels
  python3 nse_signal_engine.py --weekly             Generate weekly outlook
  python3 nse_signal_engine.py --from-json FILE     Process data (Tier 1)
  python3 nse_signal_engine.py --preview            Preview with demo data
  python3 nse_signal_engine.py --history            Show signal accuracy
"""

import json, os, sys
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import math

HERMES_HOME = os.path.expanduser("~/.hermes")
DATA_DIR = os.path.join(HERMES_HOME, "data", "nse_signals")
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")
SIGNAL_FILE = os.path.join(DATA_DIR, "signal_history.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Tier 1: Weights & Thresholds ────────────────────────────────────────────
WEIGHTS = {
    "gift_nifty":   0.20,
    "asian_peers":  0.15,
    "crude_oil":    0.15,
    "india_vix":    0.15,
    "us_futures":   0.10,
    "usd_inr":      0.10,
    "bank_nifty":   0.10,
    "dxy":          0.05,
}

THRESHOLDS = {
    "crude_oil":       (-1.5, -0.5,  0.5,  1.5),
    "usd_inr":         (-0.3, -0.1,  0.1,  0.3),
    "dxy":             (-0.4, -0.2,  0.2,  0.4),
    "india_vix_level": (14.0, 18.0, 22.0, 28.0),
    "asian_peers":     (-1.0, -0.3,  0.3,  1.0),
    "us_futures":      (-0.8, -0.3,  0.3,  0.8),
    "gift_nifty":      (-0.8, -0.3,  0.3,  0.8),
    "bank_nifty_rel":  (-1.0, -0.3,  0.3,  1.0),
}


# ── Scoring (unchanged from v1) ─────────────────────────────────────────────

def score_value(value, t):
    lo, ml, mh, hi = t
    if value <= lo: return 2
    elif value <= ml: return 1
    elif value <= mh: return 0
    elif value <= hi: return -1
    else: return -2

def score_crude(c):
    return score_value(c, THRESHOLDS["crude_oil"]) if c is not None else 0
def score_usdinr(c):
    return score_value(c, THRESHOLDS["usd_inr"]) if c is not None else 0
def score_dxy(c):
    return score_value(c, THRESHOLDS["dxy"]) if c is not None else 0
def score_vix(l):
    return score_value(l, THRESHOLDS["india_vix_level"]) if l is not None else 0
def score_peers(c):
    return score_value(-c, THRESHOLDS["asian_peers"]) if c is not None else 0
def score_us_futures(c):
    return score_value(-c, THRESHOLDS["us_futures"]) if c is not None else 0
def score_gift_nifty(c):
    return score_value(-c, THRESHOLDS["gift_nifty"]) if c is not None else 0
def score_bank_nifty(n, b):
    if n is None or b is None: return 0
    return score_value(-(b - n), THRESHOLDS["bank_nifty_rel"])


# ── Tier 1: Compute Signal ──────────────────────────────────────────────────

def compute_signal(data):
    nifty = data.get("nifty", {})
    bank_nifty = data.get("bank_nifty", {})
    peers = data.get("peers", {})
    us_fut = data.get("us_futures", {})
    crude = data.get("crude", {})
    usd_inr_data = data.get("usd_inr", {})
    dxy_data = data.get("dxy", {})
    vix_data = data.get("india_vix", {})

    scores = {}
    gn_change = data.get("gift_nifty", {}).get("change_pct", nifty.get("change_pct"))
    scores["gift_nifty"] = score_gift_nifty(gn_change)

    peer_changes = [peers.get(p, {}).get("change_pct") for p in ["nikkei", "hangseng"]]
    peer_changes = [c for c in peer_changes if c is not None]
    avg_peer = sum(peer_changes) / len(peer_changes) if peer_changes else None
    scores["asian_peers"] = score_peers(avg_peer)
    scores["us_futures"] = score_us_futures(us_fut.get("change_pct"))
    scores["crude_oil"] = score_crude(crude.get("change_pct"))
    scores["usd_inr"] = score_usdinr(usd_inr_data.get("change_pct"))
    scores["dxy"] = score_dxy(dxy_data.get("change_pct"))
    scores["india_vix"] = score_vix(vix_data.get("level"))
    scores["bank_nifty"] = score_bank_nifty(nifty.get("change_pct"), bank_nifty.get("change_pct"))

    weighted_total = sum(scores[k] * WEIGHTS[k] for k in scores if k in WEIGHTS)
    total_weight = sum(WEIGHTS[k] for k in scores if k in WEIGHTS)
    final_score = weighted_total / total_weight if total_weight > 0 else 0

    if final_score >= 1.0:
        bias = "BULLISH"; confidence = min(int(abs(final_score) * 3 + 4), 10)
    elif final_score >= 0.3:
        bias = "MILD_BULLISH"; confidence = min(int(abs(final_score) * 4 + 2), 8)
    elif final_score > -0.3:
        bias = "NEUTRAL"; confidence = 4
    elif final_score > -1.0:
        bias = "MILD_BEARISH"; confidence = min(int(abs(final_score) * 4 + 2), 8)
    else:
        bias = "BEARISH"; confidence = min(int(abs(final_score) * 3 + 4), 10)

    # Labels
    labels = {
        "crude_oil": f"Crude at ${crude.get('price','?')} ({crude.get('change_pct','?'):+.2f}%) — {'Bad' if scores['crude_oil']<0 else 'Good' if scores['crude_oil']>0 else 'Neutral'} for India",
        "usd_inr": f"₹ at {usd_inr_data.get('price','?')}/$ ({usd_inr_data.get('change_pct','?'):+.2f}%) — {'Weakening=Bearish' if scores['usd_inr']<0 else 'Strengthening=Bullish' if scores['usd_inr']>0 else 'Neutral'}",
        "india_vix": f"India VIX at {vix_data.get('level','?')} — {'Fear elevated' if (vix_data.get('level') or 0) > 20 else 'Elevated caution' if (vix_data.get('level') or 0) > 17 else 'Normal'}",
        "asian_peers": f"Asian peers avg: {avg_peer:+.2f}% — {'Negative' if scores['asian_peers']<0 else 'Positive' if scores['asian_peers']>0 else 'Mixed'}",
        "us_futures": f"US Futures: {us_fut.get('change_pct',0):+.2f}%",
        "gift_nifty": f"Overnight: {'Positive' if scores['gift_nifty']>0 else 'Negative' if scores['gift_nifty']<0 else 'Flat'}",
        "bank_nifty": f"Bank Nifty {bank_nifty.get('change_pct',0):+.2f}% vs Nifty {nifty.get('change_pct',0):+.2f}% — {'Leading' if scores['bank_nifty']>0 else 'Lagging' if scores['bank_nifty']<0 else 'Neutral'}",
        "dxy": f"DXY: {dxy_data.get('change_pct',0):+.2f}%",
    }

    ctx_parts = []
    if nifty.get("price"): ctx_parts.append(f"Nifty at {nifty['price']}")
    if crude.get("price"): ctx_parts.append(f"Crude ${crude['price']}")
    if usd_inr_data.get("price"): ctx_parts.append(f"₹{usd_inr_data['price']}/$")
    if vix_data.get("level"): ctx_parts.append(f"VIX {vix_data['level']}")

    breakdown = sorted([
        {"factor": k, "score": scores[k], "weight": WEIGHTS.get(k, 0),
         "contribution": round(scores.get(k, 0) * WEIGHTS.get(k, 0), 3),
         "label": labels.get(k, k)}
        for k in scores if k in WEIGHTS
    ], key=lambda x: x["weight"], reverse=True)

    return {
        "timestamp": datetime.now().isoformat(),
        "signal": {
            "bias": bias, "confidence": confidence,
            "score": round(final_score, 3), "raw_scores": scores,
        },
        "breakdown": breakdown,
        "data_sources": {"available": sum(1 for v in scores.values() if v != 0), "total": len(scores)},
        "market_context": " | ".join(ctx_parts),
        "data": data,
    }


# ── Tier 2a: Key Technical Levels ──────────────────────────────────────────

def compute_levels(prices_5d, day_range):
    """Compute key technical levels from 5-day price data and today's range."""
    if not prices_5d:
        return {"note": "Insufficient data for level calculation"}

    closes = [p.get("close", 0) for p in prices_5d if p.get("close")]
    highs = [p.get("high", 0) for p in prices_5d if p.get("high")]
    lows = [p.get("low", 0) for p in prices_5d if p.get("low")]

    if not closes:
        return {"note": "No close data available"}

    current = closes[-1] if closes else 0

    # Simple moving averages (from available data)
    sma_5 = sum(closes[-5:]) / min(5, len(closes[-5:])) if len(closes) >= 1 else current
    # Use approximate SMA-20/50 from the data we have (will improve with more history)
    sma_20 = sum(closes[-min(20, len(closes)):]) / min(20, len(closes)) if closes else current
    sma_50 = sum(closes) / len(closes) if closes else current

    # Support/Resistance from recent range
    recent_high = max(highs) if highs else current
    recent_low = min(lows) if lows else current
    pivot = (recent_high + recent_low + current) / 3
    r1 = 2 * pivot - recent_low
    s1 = 2 * pivot - recent_high
    r2 = pivot + (recent_high - recent_low)
    s2 = pivot - (recent_high - recent_low)

    # Today's range
    today_high = day_range.get("high")
    today_low = day_range.get("low")

    levels = {
        "current": round(current, 1),
        "pivot": round(pivot, 1),
        "resistance": {"r1": round(r1, 1), "r2": round(r2, 1)},
        "support": {"s1": round(s1, 1), "s2": round(s2, 1)},
        "moving_averages": {
            "sma_5": round(sma_5, 1),
            "sma_20": round(sma_20, 1),
            "sma_50": round(sma_50, 1),
        },
        "today_range": {
            "high": today_high, "low": today_low,
            "width": round(today_high - today_low, 1) if today_high and today_low else None,
        },
    }

    # Generate alerts
    alerts = []
    if current < sma_20 * 0.98:
        alerts.append(f"⚠️ Nifty below 2% of SMA-20 ({sma_20:.0f}) — short-term bearish")
    elif current < sma_50 * 0.95:
        alerts.append(f"⚠️ Nifty below 5% of SMA-50 ({sma_50:.0f}) — medium-term bearish")
    if today_low and current <= today_low * 1.005:
        alerts.append(f"⚠️ Nifty near day low — testing support at {s1:.0f}")
    if today_high and current >= today_high * 0.995:
        alerts.append(f"⚡ Nifty near day high — testing resistance at {r1:.0f}")

    levels["alerts"] = alerts
    return levels


def format_levels(levels):
    """Format key levels as Telegram output."""
    lines = ["📊 **Nifty Key Technical Levels**", ""]

    if "note" in levels:
        lines.append(levels["note"])
        return "\n".join(lines)

    lines.append(f"Current: **{levels['current']}**")
    tr = levels.get("today_range", {})
    if tr.get("high"):
        lines.append(f"Today Range: **{tr['low']}** – **{tr['high']}** (width: {tr['width']})")
    lines.append("")

    lines.append("**Support:**")
    lines.append(f"  S2: {levels['support']['s2']}  |  S1: **{levels['support']['s1']}**")
    lines.append("")
    lines.append("**Resistance:**")
    lines.append(f"  R1: **{levels['resistance']['r1']}**  |  R2: {levels['resistance']['r2']}")
    lines.append("")

    ma = levels.get("moving_averages", {})
    lines.append("**Moving Averages:**")
    lines.append(f"  SMA-5: {ma.get('sma_5', 'N/A')}")
    lines.append(f"  SMA-20: {ma.get('sma_20', 'N/A')}")
    lines.append(f"  SMA-50: {ma.get('sma_50', 'N/A')}")
    lines.append("")

    for alert in levels.get("alerts", []):
        lines.append(alert)

    return "\n".join(lines)


# ── Tier 2b: Signal Verification ────────────────────────────────────────────

BIAS_RATING = {"BULLISH": 5, "MILD_BULLISH": 4, "NEUTRAL": 3, "MILD_BEARISH": 2, "BEARISH": 1}

def verify_signal(morning_bias_path, nifty_close_actual):
    """Verify morning bias vs actual close."""
    if not os.path.exists(morning_bias_path):
        return {"error": f"Morning signal not found at {morning_bias_path}"}

    with open(morning_bias_path) as f:
        raw = json.load(f)

    # Get morning bias - could be raw data or computed signal
    if "signal" in raw:
        # Was saved by save_signal() — processed output
        morning_bias = raw.get("signal", {}).get("bias", "UNKNOWN")
        morning_score = raw.get("signal", {}).get("score", 0)
        raw_data = raw.get("data", {})
    else:
        # Raw pre_market.json — compute bias on the fly
        sig = compute_signal(raw)
        morning_bias = sig.get("signal", {}).get("bias", "UNKNOWN")
        morning_score = sig.get("signal", {}).get("score", 0)
        raw_data = raw

    prev_close = raw_data.get("prev_close") or raw_data.get("nifty", {}).get("price", 0)

    if not prev_close:
        return {"error": "No previous close in morning data"}

    change = nifty_close_actual - prev_close
    change_pct = (change / prev_close) * 100

    # Determine what the actual move was
    if change_pct > 0.5:
        actual_bias = "BULLISH"
    elif change_pct > 0.15:
        actual_bias = "MILD_BULLISH"
    elif change_pct > -0.15:
        actual_bias = "NEUTRAL"
    elif change_pct > -0.5:
        actual_bias = "MILD_BEARISH"
    else:
        actual_bias = "BEARISH"

    # Compare
    morning_rating = BIAS_RATING.get(morning_bias, 3)
    actual_rating = BIAS_RATING.get(actual_bias, 3)
    direction_correct = (morning_rating > 3 and actual_rating > 3) or \
                        (morning_rating < 3 and actual_rating < 3) or \
                        (morning_rating == 3 and actual_rating == 3)

    result = {
        "date": date.today().isoformat(),
        "verification_timestamp": datetime.now().isoformat(),
        "morning": {
            "bias": morning_bias,
            "confidence": raw.get("signal", {}).get("confidence") if isinstance(raw, dict) and "signal" in raw else 7,
            "score": morning_score,
        },
        "actual": {
            "close": nifty_close_actual,
            "change_pct": round(change_pct, 2),
            "bias": actual_bias,
        },
        "direction_correct": direction_correct,
        "accuracy_score": 5 - abs(morning_rating - actual_rating),
    }

    # Append to signal history
    history = []
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE) as f:
                history = json.load(f)
        except:
            history = []

    if history:
        # Update the last entry (the morning signal) with verification
        if history and "verification" not in history[-1]:
            history[-1]["verification"] = result
            with open(SIGNAL_FILE, "w") as f:
                json.dump(history, f, indent=2, default=str)

    return result


def format_verification(verif):
    """Format verification result."""
    if "error" in verif:
        return f"❌ {verif['error']}"

    morning = verif["morning"]
    actual = verif["actual"]
    emoji = "✅" if verif.get("direction_correct") else "❌"

    lines = [
        f"{emoji} **Signal Verification — {verif['date']}**",
        "",
        f"**Morning Call:** {morning['bias']} (confidence: {morning['confidence']}/10)",
        f"**Actual Close:** {actual['close']} ({actual['change_pct']:+.2f}%) → {actual['bias']}",
        "",
        f"**Direction:** {'CORRECT ✅' if verif.get('direction_correct') else 'WRONG ❌'}",
        f"**Accuracy Score:** {verif.get('accuracy_score', '?')}/5",
    ]

    # Running accuracy
    history = load_signals()
    if len(history) > 1:
        verified = [h for h in history if "verification" in h]
        correct = sum(1 for v in verified if v["verification"].get("direction_correct"))
        total = len(verified)
        if total > 0:
            lines.append(f"\n**Running Accuracy:** {correct}/{total} ({correct/total*100:.0f}%)")

    return "\n".join(lines)


# ── Tier 2c: Weekly Outlook ─────────────────────────────────────────────────

def generate_weekly():
    """Generate weekly outlook from signal history."""
    history = load_signals(7)

    if not history:
        return "No signals this week to generate an outlook."

    signals = [h.get("signal", {}) for h in history]
    verified = [h for h in history if "verification" in h]
    correct = sum(1 for v in verified if v["verification"].get("direction_correct"))
    total_v = len(verified)

    # Find dominant biases
    biases = [s.get("bias", "UNKNOWN") for s in signals]
    bias_counts = Counter(biases).most_common()

    # Average confidence
    avg_conf = sum(s.get("confidence", 0) for s in signals) / len(signals) if signals else 0

    # Extract latest data for market state
    latest = history[-1]
    ctx = latest.get("market_context", "N/A")

    # Determine weekly trend
    is_bearish_week = any(b in ("BEARISH", "MILD_BEARISH") for b in biases)
    is_bullish_week = any(b in ("BULLISH", "MILD_BULLISH") for b in biases)
    is_mixed = is_bearish_week and is_bullish_week

    if is_mixed:
        weekly_bias = "MIXED"
    elif is_bearish_week and not is_bullish_week:
        weekly_bias = "BEARISH"
    elif is_bullish_week and not is_bearish_week:
        weekly_bias = "BULLISH"
    else:
        weekly_bias = "NEUTRAL"

    # Key levels
    levels = compute_levels([], {})
    # We need historical close data - let's estimate
    last_price = None
    for h in reversed(history):
        d = h.get("data", {})
        nd = d.get("nifty", {})
        if nd.get("price"):
            last_price = nd["price"]
            break

    lines = [
        f"📅 **NSE Weekly Outlook — Week of {date.today().isoformat()}**",
        "",
        f"**Weekly Bias:** {weekly_bias}",
        f"**Signal Count:** {len(signals)} sessions tracked",
        f"**Avg Confidence:** {avg_conf:.1f}/10",
        "",
    ]

    if total_v > 0:
        lines.append(f"**Signal Accuracy:** {correct}/{total_v} ({correct/total_v*100:.0f}%)")
        lines.append("")

    # Bias breakdown
    lines.append("**Daily Bias Breakdown:**")
    for bias, count in bias_counts:
        emoji = {"BULLISH": "🟢🟢", "MILD_BULLISH": "🟢", "NEUTRAL": "⚪",
                 "MILD_BEARISH": "🔴", "BEARISH": "🔴🔴"}.get(bias, "⚪")
        lines.append(f"  {emoji} {bias}: {count} session{'s' if count>1 else ''}")

    lines.append("")
    lines.append(f"**Current Context:** {ctx}")
    if last_price:
        lines.append(f"**Nifty Level:** {last_price}")

    lines.append("")
    lines.append("**Week Ahead Watchlist:**")
    lines.append("  • Crude trajectory (impact on macros)")
    lines.append("  • USD/INR movement (FII flow proxy)")
    lines.append("  • US Fed commentary / rate signals")
    lines.append("  • Key Nifty technical levels")
    lines.append("  • Geopolitical developments (Hormuz/Iran)")

    return "\n".join(lines)


# ── History ─────────────────────────────────────────────────────────────────

def load_signals(days=90):
    if not os.path.exists(SIGNAL_FILE):
        return []
    try:
        with open(SIGNAL_FILE) as f:
            history = json.load(f)
        cutoff = datetime.now() - timedelta(days=days)
        return [h for h in history if h.get("timestamp", "")[:10] >= cutoff.isoformat()[:10]]
    except:
        return []


def save_signal(signal):
    history = []
    if os.path.exists(SIGNAL_FILE):
        try:
            with open(SIGNAL_FILE) as f:
                history = json.load(f)
        except:
            history = []
    history.append(signal)
    if len(history) > 180:
        history = history[-180:]
    with open(SIGNAL_FILE, "w") as f:
        json.dump(history, f, indent=2, default=str)
    return signal


def accuracy_report():
    history = load_signals(60)
    if not history:
        return "No signal history yet."

    by_bias = defaultdict(list)
    for entry in history:
        bias = entry.get("signal", {}).get("bias", "UNKNOWN")
        by_bias[bias].append(entry)

    verified = [h for h in history if "verification" in h]
    correct = sum(1 for v in verified if v["verification"].get("direction_correct"))
    total_v = len(verified)

    lines = [f"📊 **Signal Accuracy Report** (last 60 days)"]
    if total_v > 0:
        lines.append(f"Overall: {correct}/{total_v} correct ({correct/total_v*100:.0f}%)")
    lines.append("")
    for bias, entries in sorted(by_bias.items()):
        lines.append(f"  {bias}: {len(entries)} signals")

    last = history[-1] if history else None
    if last:
        s = last.get("signal", {})
        lines.append(f"\n**Last Signal:** {s.get('bias')} (confidence: {s.get('confidence')}/10)")
        lines.append(f"  {last.get('market_context', 'N/A')}")

    return "\n".join(lines)


# ── Output Formatting ───────────────────────────────────────────────────────

BIAS_EMOJI = {
    "BULLISH": "🟢🟢", "MILD_BULLISH": "🟢", "NEUTRAL": "⚪",
    "MILD_BEARISH": "🔴", "BEARISH": "🔴🔴",
}
BIAS_LABEL = {
    "BULLISH": "BULLISH — Expect positive day",
    "MILD_BULLISH": "MILD BULLISH — Lean positive",
    "NEUTRAL": "NEUTRAL — Range-bound expected",
    "MILD_BEARISH": "MILD BEARISH — Lean negative",
    "BEARISH": "BEARISH — Expect negative day",
}

def format_report(signal):
    s = signal.get("signal", {})
    bias = s.get("bias", "UNKNOWN")
    confidence = s.get("confidence", 0)
    ctx = signal.get("market_context", "")
    ts = signal.get("timestamp", "")[:19].replace("T", " ")

    lines = [
        f"🔮 **NSE Proactive Signal — {ts}**",
        "",
        f"{BIAS_EMOJI.get(bias, '⚪')} **{BIAS_LABEL.get(bias, bias)}**",
        f"   Confidence: **{confidence}/10** | Score: **{s.get('score',0):+.3f}**",
        "",
        f"📊 **Context:** {ctx}",
        "",
        "**Factor Breakdown:**",
    ]

    for b in signal.get("breakdown", []):
        em = "🟢" if b["score"] > 0 else "🔴" if b["score"] < 0 else "⚪"
        fac = b["factor"].replace("_", " ").title()
        lines.append(f"  {em} **{fac}**: {b['score']:+d} (w: {b['weight']})")
        if b.get("label"):
            lines.append(f"     └ {b['label']}")

    ds = signal.get("data_sources", {})
    lines.append(f"\n_Sources: {ds.get('available',0)}/{ds.get('total',0)} active_")
    lines.append("")

    if bias in ("BULLISH", "MILD_BULLISH"):
        lines.append("**💡 Action:** Pre-market signals lean positive. Confirm in first 30 min.")
    elif bias in ("BEARISH", "MILD_BEARISH"):
        lines.append("**💡 Action:** Pre-market signals lean negative. Consider defensive positioning.")
    else:
        lines.append("**💡 Action:** Mixed signals. Wait for first hour to establish direction.")

    return "\n".join(lines)


# ── Demo Data ───────────────────────────────────────────────────────────────

DEMO_DATA = {
    "date": date.today().isoformat(),
    "nifty": {"price": 23519, "change_pct": -0.55},
    "bank_nifty": {"price": 53075, "change_pct": -1.18},
    "peers": {
        "nikkei": {"price": 60816, "change_pct": -0.97},
        "hangseng": {"price": 25614, "change_pct": -1.35},
    },
    "us_futures": {"price": 7388, "change_pct": -0.59},
    "crude": {"price": 110.49, "change_pct": 1.13},
    "usd_inr": {"price": 96.26, "change_pct": 0.32},
    "dxy": {"price": 108.5, "change_pct": 0.15},
    "india_vix": {"level": 19.53, "change_pct": 3.95},
    "gift_nifty": {"price": 23500, "change_pct": -0.40},
}

DEMO_PRICES_5D = [
    {"date": "2026-05-12", "close": 23380, "high": 23758, "low": 23348},
    {"date": "2026-05-13", "close": 23413, "high": 23583, "low": 23263},
    {"date": "2026-05-14", "close": 23690, "high": 23777, "low": 23427},
    {"date": "2026-05-15", "close": 23644, "high": 23839, "low": 23610},
    {"date": "2026-05-18", "close": 23519, "high": 23563, "low": 23317},
]


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--preview" in sys.argv:
        sig = compute_signal(DEMO_DATA)
        print(format_report(sig))
        print(f"\n{'─'*50}")
        print("(Preview mode. Use --from-json for live data.)")

    elif "--from-json" in sys.argv:
        idx = sys.argv.index("--from-json") + 1
        with open(sys.argv[idx]) as f:
            data = json.load(f)
        sig = compute_signal(data)
        save_signal(sig)
        print(format_report(sig))

    elif "--levels" in sys.argv:
        lvls = compute_levels(DEMO_PRICES_5D, {"high": 23563, "low": 23317})
        print(format_levels(lvls))

    elif "--verify" in sys.argv:
        idx = sys.argv.index("--verify") + 1
        morning_path = sys.argv[idx] if idx < len(sys.argv) else \
            os.path.join(DATA_DIR, "pre_market.json")
        close_val = float(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else None
        if close_val:
            verif = verify_signal(morning_path, close_val)
            print(format_verification(verif))
        else:
            print("Usage: --verify <morning_signal.json> <actual_nifty_close>")

    elif "--weekly" in sys.argv:
        print(generate_weekly())

    elif "--history" in sys.argv:
        print(accuracy_report())

    else:
        print("NSE Proactive Signal Engine v2 (Tier 2)")
        print("Usage:")
        print("  --preview              Preview with demo data")
        print("  --from-json FILE       Process live market data")
        print("  --levels               Show Nifty key technical levels")
        print("  --verify PATH CLOSE    Verify morning bias vs actual close")
        print("  --weekly               Generate weekly outlook")
        print("  --history              Show signal accuracy")
