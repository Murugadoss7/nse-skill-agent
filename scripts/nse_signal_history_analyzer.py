#!/usr/bin/env python3
"""
NSE Signal History Analyzer v1
===============================
Reads signal_history.json and performs statistical analysis:
  - Per-factor accuracy over time
  - Factor decay detection
  - Threshold calibration analysis
  - Regime correlation
  - Confidence calibration

Usage:
  python3 nse_signal_history_analyzer.py                    # Full analysis → stdout
  python3 nse_signal_history_analyzer.py --output md        # Markdown for Obsidian
  python3 nse_signal_history_analyzer.py --save             # Save to vault
  python3 nse_signal_history_analyzer.py --quick            # Quick summary only
"""

import json, os, sys, math
from datetime import datetime, timedelta
from collections import defaultdict

HERMES_HOME = os.path.expanduser("~/.hermes")
DATA_DIR = os.path.join(HERMES_HOME, "data", "nse_signals")
RESEARCH_DIR = os.path.join(HERMES_HOME, "data", "trading_research")
SIGNAL_FILE = os.path.join(DATA_DIR, "signal_history.json")

os.makedirs(os.path.join(RESEARCH_DIR, "03-Factors"), exist_ok=True)
os.makedirs(os.path.join(RESEARCH_DIR, "04-History"), exist_ok=True)
os.makedirs(os.path.join(RESEARCH_DIR, "06-Learnings"), exist_ok=True)


# ── Factor Configuration ─────────────────────────────────────────────────

FACTORS = [
    "gift_nifty", "asian_peers", "crude_oil", "india_vix",
    "us_futures", "usd_inr", "bank_nifty", "dxy"
]

FACTOR_NAMES = {
    "gift_nifty": "Gift Nifty",
    "asian_peers": "Asian Peers",
    "crude_oil": "Crude Oil",
    "india_vix": "India VIX",
    "us_futures": "US Futures",
    "usd_inr": "USD/INR",
    "bank_nifty": "Bank Nifty",
    "dxy": "DXY"
}

FACTOR_WEIGHTS = {
    "gift_nifty": 0.20, "asian_peers": 0.15, "crude_oil": 0.15,
    "india_vix": 0.15, "us_futures": 0.10, "usd_inr": 0.10,
    "bank_nifty": 0.10, "dxy": 0.05,
}

BIAS_MAP = {
    "BULLISH": 1, "MILD_BULLISH": 0.5,
    "NEUTRAL": 0,
    "MILD_BEARISH": -0.5, "BEARISH": -1,
}


# ── Load & Parse ─────────────────────────────────────────────────────────

def load_signals():
    """Load signal history from JSON file."""
    if not os.path.exists(SIGNAL_FILE):
        print(f"❌ Signal file not found: {SIGNAL_FILE}")
        return []

    with open(SIGNAL_FILE) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing {SIGNAL_FILE}: {e}")
            return []

    signals = []
    for entry in data:
        ts = entry.get('timestamp', '')
        sig = entry.get('signal', {})
        bd = entry.get('breakdown', [])
        vf = entry.get('verification', {})

        raw_scores = sig.get('raw_scores', {})

        # Extract factor scores from breakdown if raw_scores is empty
        if not raw_scores and bd:
            for item in bd:
                raw_scores[item['factor']] = item.get('score', 0)

        # Determine if signal was correct
        actual_bias = vf.get('actual_bias', '')
        actual_change = vf.get('actual_change_pct', None)
        verified = vf.get('verified', vf.get('direction_correct', False))
        accuracy_score = vf.get('accuracy_score', None)

        # Use direction_correct from verification if available
        if 'direction_correct' in vf and vf['direction_correct'] is not None:
            correct = vf['direction_correct']
            pred_direction = 1 if correct else -1  # approximate for logging
        else:
            pred_direction = BIAS_MAP.get(sig.get('bias', ''), 0)
            actual_direction = BIAS_MAP.get(actual_bias, 0)
            correct = (pred_direction > 0 and actual_direction > 0) or \
                      (pred_direction < 0 and actual_direction < 0)

        signals.append({
            "timestamp": ts,
            "date": ts[:10] if ts else '',
            "bias": sig.get('bias', ''),
            "confidence": sig.get('confidence', 0),
            "score": sig.get('score', 0),
            "raw_scores": raw_scores,
            "verified": bool(verified),
            "actual_bias": actual_bias,
            "actual_change_pct": actual_change,
            "accuracy_score": accuracy_score,
            "correct": correct
        })

    return signals


# ── Analysis Functions ──────────────────────────────────────────────────

def analyze_factor_performance(signals):
    """Per-factor accuracy and statistical significance."""
    verified = [s for s in signals if s['verified'] and s['correct'] is not None]

    factor_stats = {}
    for factor in FACTORS:
        correct = 0
        total = 0
        contributions = []

        for s in verified:
            score = s['raw_scores'].get(factor, 0)
            if score != 0:  # Only count when factor had an opinion
                total += 1
                if s['correct']:
                    correct += 1
                contributions.append({
                    "score": score,
                    "correct": s['correct'],
                    "date": s['date'],
                    "bias": s['bias']
                })

        accuracy = (correct / total * 100) if total > 0 else None

        # Statistical significance: simple correlation test
        # Factor score vs direction correctness
        if total > 5:
            scores = [c['score'] for c in contributions]
            outcomes = [1 if c['correct'] else 0 for c in contributions]
            # Simple correlation
            n = len(scores)
            if n > 1:
                mean_s = sum(scores) / n
                mean_o = sum(outcomes) / n
                num = sum((s - mean_s) * (o - mean_o) for s, o in zip(scores, outcomes))
                den = (sum((s - mean_s)**2 for s in scores) * sum((o - mean_o)**2 for o in outcomes))**0.5
                correlation = num / den if den > 0 else 0
            else:
                correlation = 0
        else:
            correlation = 0

        factor_stats[factor] = {
            "name": FACTOR_NAMES.get(factor, factor),
            "weight": FACTOR_WEIGHTS.get(factor, 0),
            "total_signals": total,
            "correct": correct,
            "accuracy": round(accuracy, 1) if accuracy else None,
            "correlation": round(correlation, 3),
            "contributions": contributions,
            "sample_size": total
        }

    return factor_stats


def analyze_decay(signals, factor_stats):
    """Detect factor decay — is accuracy declining over time?"""
    decay_results = {}

    for factor, stats in factor_stats.items():
        contribs = stats['contributions']
        if len(contribs) < 10:
            decay_results[factor] = {"decay_detected": False, "reason": "Insufficient data"}
            continue

        # Split into windows (chronological order)
        contribs_sorted = sorted(contribs, key=lambda x: x['date'])
        window_size = max(5, len(contribs_sorted) // 3)

        windows = []
        for i in range(0, len(contribs_sorted), window_size):
            window = contribs_sorted[i:i+window_size]
            if len(window) >= 3:
                win_accuracy = sum(1 for c in window if c['correct']) / len(window) * 100
                windows.append({
                    "start": window[0]['date'],
                    "end": window[-1]['date'],
                    "accuracy": win_accuracy,
                    "count": len(window)
                })

        if len(windows) >= 2:
            # Linear trend: simple comparison of first half vs second half
            mid = len(windows) // 2
            first_half_avg = sum(w['accuracy'] for w in windows[:mid]) / mid
            second_half_avg = sum(w['accuracy'] for w in windows[mid:]) / (len(windows) - mid)
            decay = first_half_avg - second_half_avg
            decay_detected = decay > 5  # >5% decline = concerning
        else:
            decay = 0
            decay_detected = False

        decay_results[factor] = {
            "decay_detected": decay_detected,
            "decay_pct": round(decay, 1),
            "first_half_accuracy": round(first_half_avg, 1) if len(windows) >= 2 else None,
            "second_half_accuracy": round(second_half_avg, 1) if len(windows) >= 2 else None,
            "windows": windows,
            "trend": "improving" if decay < -5 else ("decaying" if decay > 5 else "stable")
        }

    return decay_results


def analyze_confidence_calibration(signals):
    """Check if confidence scores match actual accuracy."""
    verified = [s for s in signals if s['verified'] and s['correct'] is not None]

    bands = [(1, 3), (4, 6), (7, 8), (9, 10)]
    calibration = []

    for lo, hi in bands:
        band = [s for s in verified if lo <= s['confidence'] <= hi]
        if band:
            correct = sum(1 for s in band if s['correct'])
            calibration.append({
                "band": f"{lo}-{hi}",
                "count": len(band),
                "actual_accuracy": round(correct / len(band) * 100, 1)
            })

    return calibration


def analyze_bias_distribution(signals):
    """Distribution of bias types and their accuracy."""
    verified = [s for s in signals if s['verified'] and s['correct'] is not None]

    bias_stats = defaultdict(lambda: {"count": 0, "correct": 0})
    for s in verified:
        bias = s['bias']
        bias_stats[bias]["count"] += 1
        if s['correct']:
            bias_stats[bias]["correct"] += 1

    results = {}
    for bias, stats in bias_stats.items():
        results[bias] = {
            "count": stats["count"],
            "accuracy": round(stats["correct"] / stats["count"] * 100, 1) if stats["count"] > 0 else 0
        }

    return results


def detect_regime_shifts(signals):
    """Detect periods where accuracy changed significantly (regime shifts)."""
    verified = sorted([s for s in signals if s['verified'] and s['correct'] is not None],
                      key=lambda x: x['date'])

    if len(verified) < 20:
        return []

    # Rolling accuracy
    window = 10
    regimes = []
    for i in range(len(verified) - window + 1):
        chunk = verified[i:i+window]
        accuracy = sum(1 for s in chunk if s['correct']) / window * 100
        regimes.append({
            "date": chunk[-1]['date'],
            "accuracy": round(accuracy, 1)
        })

    # Detect shifts: accuracy changes >20% in 20 days
    shifts = []
    for i in range(10, len(regimes)):
        p1 = regimes[i-10]['accuracy']
        p2 = regimes[i]['accuracy']
        if abs(p2 - p1) > 20:
            shifts.append({
                "date": regimes[i]['date'],
                "accuracy_before": p1,
                "accuracy_after": p2,
                "change": round(p2 - p1, 1)
            })

    return shifts


# ── Output Formatters ─────────────────────────────────────────────────────

def format_telegram_summary(signals):
    """Generate a concise Telegram-ready summary."""
    verified = [s for s in signals if s['verified'] and s['correct'] is not None]
    total = len(signals)
    verified_count = len(verified)

    if verified_count == 0:
        return "📡 **Signal History: No verified data yet**\nNeed more signal cycles to analyze."

    overall_correct = sum(1 for s in verified if s['correct'])
    overall_accuracy = overall_correct / verified_count * 100

    # Factor performance
    factor_stats = analyze_factor_performance(signals)

    # Decay
    decay = analyze_decay(signals, factor_stats)

    # Calibration
    calib = analyze_confidence_calibration(signals)

    # Bias distribution
    bias_dist = analyze_bias_distribution(signals)

    # Build message
    lines = []
    lines.append(f"📡 **Signal History Analysis — {len(signals)} cycles**")
    lines.append("")

    # Overall
    lines.append(f"━━━ OVERALL ━━━")
    lines.append(f"🎯 Accuracy: {overall_accuracy:.0f}% ({overall_correct}/{verified_count})")
    lines.append(f"📊 Verified signals: {verified_count}/{total}")
    lines.append("")

    # Factor rankings
    lines.append(f"━━━ FACTOR RANKINGS ━━━")
    sorted_factors = sorted(factor_stats.values(), key=lambda x: x['accuracy'] if x['accuracy'] else 0, reverse=True)
    for f in sorted_factors:
        acc = f"{f['accuracy']}%" if f['accuracy'] else "N/A"
        decay_flag = " 🔻" if decay.get(list(factor_stats.keys())[list(factor_stats.values()).index(f)], {}).get('decay_detected') else ""
        weight = f['weight']
        lines.append(f"  {f['name']}: {acc} (w: {int(weight*100)}%){decay_flag}")

    # Decay warnings
    decaying = {k: v for k, v in decay.items() if v.get('decay_detected')}
    if decaying:
        lines.append("")
        lines.append(f"⚠️ **DECAYING FACTORS:**")
        for factor, info in decaying.items():
            name = FACTOR_NAMES.get(factor, factor)
            lines.append(f"  🔻 {name}: {info['first_half_accuracy']}% → {info['second_half_accuracy']}%")

    # Calibration check
    if calib:
        lines.append("")
        lines.append(f"━━━ CONFIDENCE CALIBRATION ━━━")
        for c in calib:
            delta = c['actual_accuracy'] - (int(c['band'].split('-')[0]) + int(c['band'].split('-')[1])) / 2 * 10
            flag = "✅" if abs(delta) < 15 else "⚠️"
            lines.append(f"  {flag} Conf {c['band']}: actual {c['actual_accuracy']}% ({c['count']} trades)")

    # Bias distribution
    if bias_dist:
        lines.append("")
        lines.append(f"━━━ BIAS ACCURACY ━━━")
        for bias, stats in sorted(bias_dist.items(), key=lambda x: x[1]['count'], reverse=True):
            lines.append(f"  {bias}: {stats['accuracy']}% ({stats['count']} calls)")

    # Regime shifts
    shifts = detect_regime_shifts(signals)
    if shifts:
        lines.append("")
        lines.append(f"⚠️ **REGIME SHIFTS DETECTED:**")
        for s in shifts[-3:]:  # Last 3
            lines.append(f"  {s['date']}: {s['accuracy_before']}% → {s['accuracy_after']}%")

    # Recommendations
    lines.append("")
    lines.append(f"━━━ RECOMMENDATIONS ━━━")

    # Check VIX threshold issue
    vix_stats = factor_stats.get('india_vix', {})
    if vix_stats.get('accuracy') and vix_stats['accuracy'] < 50:
        lines.append(f"🔧 VIX threshold (22) too high for current regime — consider lowering to 18-20")

    # Check Gift Nifty
    gift_stats = factor_stats.get('gift_nifty', {})
    if gift_stats.get('total_signals', 0) < 5:
        lines.append(f"🔧 Gift Nifty data still broken (few signals) — 20% weight effectively unused")

    # Check decaying factors
    for factor, info in decaying.items():
        name = FACTOR_NAMES.get(factor, factor)
        lines.append(f"🔧 {name} is decaying ({info['decay_pct']}% drop) — consider reducing weight")

    return '\n'.join(lines)


def save_factor_notes(signals, factor_stats, decay):
    """Save per-factor analysis notes to Obsidian vault."""
    for factor, stats in factor_stats.items():
        d = decay.get(factor, {})
        filename = f"{factor}.md"
        filepath = os.path.join(RESEARCH_DIR, "03-Factors", filename)

        cons = sorted(stats['contributions'], key=lambda x: x['date']) if stats['contributions'] else []

        md = f"""---
tags: [factor, analysis]
date: {datetime.now().strftime('%Y-%m-%d')}
factor: {factor}
weight: {stats['weight']}
accuracy: {stats['accuracy'] if stats['accuracy'] else 'N/A'}
correlation: {stats['correlation']}
decay: {d.get('trend', 'unknown')}
---

# Factor: {stats['name']}

## Current State
- **Weight**: {int(stats['weight'] * 100)}%
- **Data Source**: yfinance

## Historical Performance
| Metric | Value |
|--------|-------|
| **Total Signals** | {stats['total_signals']} |
| **Correct** | {stats['correct']} |
| **Accuracy** | {stats['accuracy']}% |
| **Correlation** | {stats['correlation']} |
| **Decay Trend** | {d.get('trend', 'unknown')} |

## Decay Analysis
- First half accuracy: {d.get('first_half_accuracy', 'N/A')}%
- Second half accuracy: {d.get('second_half_accuracy', 'N/A')}%
- Decay detected: {d.get('decay_detected', False)}
"""
        if d.get('windows'):
            md += "\n## Accuracy Over Time\n"
            md += "| Period | Accuracy | Samples |\n"
            md += "|--------|----------|--------|\n"
            for w in d['windows']:
                md += f"| {w['start']}→{w['end']} | {w['accuracy']:.0f}% | {w['count']} |\n"

        md += f"""
## Recommendations

- TODO: Review after more data points

## Related
- [[01-Techniques/signal-engine-8-factor]]
- [[07-Reference/metrics-definitions]]
"""
        with open(filepath, 'w') as f:
            f.write(md)
        print(f"💾 Saved factor note: {filepath}")


def save_history_report(signals, summary):
    """Save periodic history report to Obsidian vault."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}-signal-analysis.md"
    filepath = os.path.join(RESEARCH_DIR, "04-History", filename)

    verified = [s for s in signals if s['verified']]
    correct = sum(1 for s in verified if s['correct'])

    md = f"""---
tags: [history, analysis]
date: {date_str}
total_signals: {len(signals)}
verified: {len(verified)}
correct: {correct}
---

# Signal History Analysis — {date_str}

## Summary
{summary}

## Raw Data
- File: `~/.hermes/data/nse_signals/signal_history.json`
- Total entries: {len(signals)}
- Verified: {len(verified)}

---

*Auto-generated by nse-trading-researcher*
"""
    with open(filepath, 'w') as f:
        f.write(md)
    print(f"💾 Saved history report: {filepath}")


def save_learnings(signals, decay, factor_stats):
    """Extract learnings and save to vault."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    filepath = os.path.join(RESEARCH_DIR, "06-Learnings", f"{date_str}-learnings.md")

    learnings = []

    # VIX threshold
    vix = factor_stats.get('india_vix', {})
    if vix.get('accuracy') and vix['accuracy'] < 50:
        learnings.append("VIX threshold (22) too high for current low-vol regime")

    # Gift Nifty
    gift = factor_stats.get('gift_nifty', {})
    if gift.get('total_signals', 0) < 5:
        learnings.append("Gift Nifty data source still broken — 20% weight wasted")

    # Decaying factors
    for factor, info in decay.items():
        if info.get('decay_detected'):
            name = FACTOR_NAMES.get(factor, factor)
            learnings.append(f"{name} showing decay ({info['decay_pct']}% accuracy drop)")

    if not learnings:
        learnings.append("No significant findings this cycle")

    md = f"""---
tags: [learning, analysis]
date: {date_str}
---

# Learnings — {date_str}

## Findings
"""
    for l in learnings:
        md += f"- {l}\n"

    md += f"""
## Next Steps
- Review factor weights based on accuracy rankings
- Consider threshold adjustments for decaying factors

---
*Auto-generated by nse-trading-researcher*
"""
    with open(filepath, 'w') as f:
        f.write(md)
    print(f"💾 Saved learnings: {filepath}")

    return learnings


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description='NSE Signal History Analyzer')
    parser.add_argument('--output', default='telegram', choices=['telegram', 'md', 'json'],
                        help='Output format')
    parser.add_argument('--save', action='store_true',
                        help='Save results to Obsidian vault')
    parser.add_argument('--quick', action='store_true',
                        help='Quick summary only')

    args = parser.parse_args()

    signals = load_signals()
    if not signals:
        print("No signals to analyze. Run the signal engine first.")
        return

    print(f"📊 Loaded {len(signals)} signal entries")

    if args.quick:
        verified = [s for s in signals if s['verified']]
        correct = sum(1 for s in verified if s['correct'])
        total_v = len(verified)
        if total_v > 0:
            print(f"Accuracy: {correct}/{total_v} ({correct/total_v*100:.0f}%)")
        else:
            print("No verified signals yet")
        return

    if args.output == 'telegram':
        summary = format_telegram_summary(signals)
        print(summary)
    elif args.output == 'json':
        factor_stats = analyze_factor_performance(signals)
        decay = analyze_decay(signals, factor_stats)
        calib = analyze_confidence_calibration(signals)
        bias_dist = analyze_bias_distribution(signals)

        output = {
            "total_signals": len(signals),
            "verified": len([s for s in signals if s['verified']]),
            "factor_performance": factor_stats,
            "decay": decay,
            "calibration": calib,
            "bias_distribution": bias_dist
        }
        print(json.dumps(output, indent=2))

    if args.save:
        factor_stats = analyze_factor_performance(signals)
        decay = analyze_decay(signals, factor_stats)
        save_factor_notes(signals, factor_stats, decay)
        summary = format_telegram_summary(signals)
        save_history_report(signals, summary)
        learnings = save_learnings(signals, decay, factor_stats)
        print(f"\n✅ All vault files written to: {RESEARCH_DIR}")


if __name__ == '__main__':
    main()
