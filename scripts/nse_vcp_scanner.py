#!/usr/bin/env python3
"""
NSE VCP Scanner — detects Volatility Contraction Patterns (Minervini SEPA)
across Nifty stocks and reports market breadth.

Usage:
    python3 ~/.hermes/scripts/nse_vcp_scanner.py
    python3 ~/.hermes/scripts/nse_vcp_scanner.py --universe nifty50
    python3 ~/.hermes/scripts/nse_vcp_scanner.py --universe nifty500 --output md

Output: Market breadth score = % of stocks forming VCP patterns.
Useful as a market-structure signal for the signal engine.
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

HERMES_HOME = os.path.expanduser("~/.hermes")
RESEARCH_DIR = os.path.join(HERMES_HOME, "data", "trading_research")
os.makedirs(os.path.join(RESEARCH_DIR, "01-Techniques"), exist_ok=True)

# ── Nifty Constituents ──────────────────────────────────────────────────────

NIFTY_50_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "WIPRO.NS", "AXISBANK.NS", "TITAN.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "BAJFINANCE.NS", "NTPC.NS",
    "POWERGRID.NS", "ULTRACEMCO.NS", "HCLTECH.NS", "M&M.NS", "BAJAJFINSV.NS",
    "TATASTEEL.NS", "JSWSTEEL.NS", "COALINDIA.NS", "ADANIPORTS.NS", "ADANIENT.NS",
    "GRASIM.NS", "INDUSINDBK.NS", "ONGC.NS", "SBILIFE.NS", "DRREDDY.NS",
    "TATACONSUM.NS", "BRITANNIA.NS", "HDFCLIFE.NS", "DIVISLAB.NS", "CIPLA.NS",
    "APOLLOHOSP.NS", "EICHERMOT.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "TECHM.NS",
    "HINDALCO.NS", "BPCL.NS", "BEL.NS", "TRENT.NS", "NESTLEIND.NS",
]


# ── Technical Helpers ───────────────────────────────────────────────────────

def _sf(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return default if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return default


def _ema_series(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def _ema_last(s: pd.Series, period: int) -> float:
    if len(s) < period:
        return _sf(s.iloc[-1]) if len(s) > 0 else 0.0
    return _sf(_ema_series(s, period).iloc[-1])


def _rsi(closes: pd.Series, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    v = rsi.iloc[-1]
    return round(_sf(v, 50.0), 1)


def _hhhl(highs: pd.Series, lows: pd.Series, lookback: int = 40) -> bool:
    """Higher highs and higher lows over lookback period."""
    if len(highs) < lookback:
        return False
    h = highs.iloc[-lookback:].values
    l = lows.iloc[-lookback:].values
    mid = len(h) // 2
    return h[mid:].mean() > h[:mid].mean() and l[mid:].mean() > l[:mid].mean()


def _choc(highs: pd.Series, lows: pd.Series, lookback: int = 5) -> bool:
    """Change of Character — lower low below prior range."""
    if len(lows) < lookback * 2:
        return False
    recent = lows.iloc[-lookback:]
    prior = lows.iloc[-lookback * 2:-lookback]
    return float(recent.min()) < float(prior.min()) * 0.99


def _tight_base(highs: pd.Series, lows: pd.Series, period: int, max_range: float) -> bool:
    """Price range as % of low is within max_range."""
    if len(highs) < period:
        return False
    h = float(highs.iloc[-period:].max())
    l = float(lows.iloc[-period:].min())
    if l == 0:
        return False
    return (h - l) / l * 100 < max_range


def _wave_avg_ranges(highs: pd.Series, lows: pd.Series, waves: int, wave_size: int) -> list[float] | None:
    """Average range per wave for volatility contraction detection."""
    required = waves * wave_size
    if len(highs) < required:
        return None
    ranges = []
    for i in range(waves):
        start = -(required - i * wave_size)
        end = -(required - (i + 1) * wave_size) if (required - (i + 1) * wave_size) > 0 else None
        h_seg = highs.iloc[start:end]
        l_seg = lows.iloc[start:end]
        lo = float(l_seg.min())
        if lo == 0:
            return None
        ranges.append((float(h_seg.max()) - lo) / lo * 100)
    return ranges


# ── VCP Detection ──────────────────────────────────────────────────────────

def check_vcp(ticker: str) -> dict:
    """Check if a single stock has a VCP pattern setup. Returns result dict."""
    result = {
        "ticker": ticker.replace(".NS", ""),
        "vcp_present": False,
        "confidence": 0,
        "conditions_passed": 0,
        "conditions_total": 10,
        "conditions": {},
        "ltp": 0,
        "error": None,
    }

    try:
        # Fetch 1 year of daily data (need ~260 days for all indicators)
        df = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 30:
            result["error"] = "Insufficient data"
            return result

        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        closes = df["Close"].astype(float)
        highs = df["High"].astype(float)
        lows = df["Low"].astype(float)
        vols = df["Volume"].astype(float)

        ltp = _sf(closes.iloc[-1])
        if ltp == 0:
            result["error"] = "Zero price"
            return result
        result["ltp"] = round(ltp, 2)

        # Core indicators
        ema_10 = _ema_last(closes, 10)
        ema_20 = _ema_last(closes, 20)
        ema_50 = _ema_last(closes, 50)
        rsi_val = _rsi(closes)

        avg_vol_5 = _sf(vols.iloc[-5:].mean()) if len(vols) >= 5 else _sf(vols.mean())
        avg_vol_20 = _sf(vols.iloc[-20:].mean()) if len(vols) >= 20 else _sf(vols.mean())

        sma_200 = _sf(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else 0.0

        # VCP-specific checks
        wave_ranges = _wave_avg_ranges(highs, lows, 4, 15)
        wave_contracting = (
            all(wave_ranges[i] > wave_ranges[i + 1] for i in range(len(wave_ranges) - 1))
            if wave_ranges else False
        )
        tight_now = _tight_base(highs, lows, 7, 8.0)
        tight_prior = _tight_base(highs, lows, 21, 20.0)
        vol_dry = avg_vol_5 < avg_vol_20 * 0.65
        sma_200_ok = ltp > sma_200 if sma_200 > 0 else ltp > ema_50

        conditions = {
            "EMA Stack (10>20>50)": ema_10 > ema_20 and ema_20 > ema_50,
            "Price > SMA 200": sma_200_ok,
            "RSI Momentum (45-70)": 45 <= rsi_val <= 70,
            "Higher High/Low (40d)": _hhhl(highs, lows, 40),
            "4-Wave Contraction": wave_contracting,
            "Tight Base <=8% (7d)": tight_now,
            "Prior Base <=20% (21d)": tight_prior,
            "Volume Drying (<65% avg)": vol_dry,
            "No Change of Character": not _choc(highs, lows, 5),
            "Liquidity (>50k vol)": avg_vol_20 >= 50_000,
        }

        passed = sum(1 for v in conditions.values() if v)
        result["conditions"] = conditions
        result["conditions_passed"] = passed
        result["confidence"] = int(passed / 10 * 100)
        result["vcp_present"] = passed >= 7  # Strong VCP setup at 70%+

    except Exception as e:
        result["error"] = str(e)

    return result


def scan_universe(tickers: list[str], max_workers: int = 10) -> list[dict]:
    """Scan all tickers for VCP patterns."""
    results = []
    total = len(tickers)
    print(f"🔍 Scanning {total} stocks for VCP patterns...")

    for i, ticker in enumerate(tickers):
        sys.stdout.write(f"\r  [{i+1}/{total}] {ticker:<20s}")
        sys.stdout.flush()
        result = check_vcp(ticker)
        results.append(result)
        time.sleep(0.1)  # Rate limiting for yfinance

    print()
    return results


def format_report(results: list[dict], output_format: str = "text") -> str:
    """Format scan results as report."""
    total = len(results)
    traded = [r for r in results if not r.get("error")]
    vcp_hits = [r for r in traded if r["vcp_present"]]
    strong_hits = [r for r in traded if r["confidence"] >= 80]

    vcp_breadth = len(vcp_hits) / len(traded) * 100 if traded else 0
    strong_breadth = len(strong_hits) / len(traded) * 100 if traded else 0

    if output_format == "json":
        return json.dumps({
            "total_scanned": total,
            "traded": len(traded),
            "vcp_hits": len(vcp_hits),
            "strong_hits": len(strong_hits),
            "vcp_breadth_pct": round(vcp_breadth, 1),
            "strong_breadth_pct": round(strong_breadth, 1),
            "timestamp": datetime.now().isoformat(),
            "results": [{
                "ticker": r["ticker"],
                "vcp": r["vcp_present"],
                "confidence": r["confidence"],
                "ltp": r["ltp"],
            } for r in sorted(traded, key=lambda x: x["confidence"], reverse=True)],
        }, indent=2)

    # Text/Markdown format
    lines = []
    lines.append(f"## VCP Market Breadth Scan — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Stocks Scanned | {total} |")
    lines.append(f"| Stocks with Data | {len(traded)} |")
    lines.append(f"| VCP Setups (≥70% confidence) | {len(vcp_hits)} |")
    lines.append(f"| Strong VCP Setups (≥80% confidence) | {len(strong_hits)} |")
    lines.append(f"| **VCP Breadth** | **{vcp_breadth:.1f}%** |")
    lines.append(f"| Strong Breadth | {strong_breadth:.1f}% |")
    lines.append("")

    # Top VCP picks
    if vcp_hits:
        sorted_hits = sorted(vcp_hits, key=lambda x: x["confidence"], reverse=True)
        lines.append("### Top VCP Setups")
        lines.append("")
        lines.append("| Ticker | Confidence | Conditions | LTP |")
        lines.append("|--------|-----------|------------|-----|")
        for r in sorted_hits[:10]:
            ticker = r["ticker"]
            conf = f"{r['confidence']}%"
            conds = f"{r['conditions_passed']}/{r['conditions_total']}"
            ltp = r["ltp"]
            lines.append(f"| {ticker} | {conf} | {conds} | ₹{ltp} |")

        lines.append("")
        lines.append("### Full List")
        lines.append("")
        for r in sorted_hits:
            fails = [k for k, v in r["conditions"].items() if not v]
            fail_str = f"  ❌ {', '.join(fails)}" if fails else "  ✅ All conditions met"
            lines.append(f"- **{r['ticker']}** ({r['confidence']}%, {r['conditions_passed']}/10):{fail_str}")

    if errors := [r for r in results if r.get("error")]:
        lines.append("")
        lines.append(f"### Errors ({len(errors)} stocks)")
        lines.append("")
        for r in errors:
            lines.append(f"- {r['ticker']}: {r['error']}")

    return "\n".join(lines)


def save_vault_report(report: str, scan_results: list[dict]) -> str:
    """Save VCP scan results to Obsidian vault."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-vcp-breadth.md"
    filepath = os.path.join(RESEARCH_DIR, "01-Techniques", filename)

    traded = [r for r in scan_results if not r.get("error")]
    vcp_hits = [r for r in traded if r["vcp_present"]]
    vcp_breadth = len(vcp_hits) / len(traded) * 100 if traded else 0

    content = f"""---
tags: [technique, vcp, breadth, nse]
date: {date_str}
vcp_breadth: {vcp_breadth:.1f}%
vcp_hits: {len(vcp_hits)}/{len(traded)}
---

# VCP Market Breadth Scan — {date_str}

## Summary

- **VCP Breadth**: {vcp_breadth:.1f}% of Nifty stocks showing Volatility Contraction Pattern
- **Interpretation**: {'✅ Constructive — many stocks setting up' if vcp_breadth > 20 else '⚠️ Neutral — moderate VCP activity' if vcp_breadth > 10 else '❌ Weak — few stocks setting up'}
- **Strong Setups (≥80%)**: {len([r for r in vcp_hits if r['confidence'] >= 80])}

## Top Setups

| Ticker | Confidence | Conditions | LTP |
|--------|-----------|------------|-----|
"""
    for r in sorted(vcp_hits, key=lambda x: x["confidence"], reverse=True)[:10]:
        content += f"| {r['ticker']} | {r['confidence']}% | {r['conditions_passed']}/10 | ₹{r['ltp']} |\n"

    content += f"""
## Usage

VCP Breadth can be used as a market-structure signal for the signal engine:
- **High VCP Breadth (>20%)**: Bullish market structure — many stocks forming bases
- **Low VCP Breadth (<10%)**: Bearish/neutral — few setups, market lacks constructive pattern

## Source

Adapted from `Negi27921/one-piece` VCP screener (Minervini SEPA methodology).
See [[{date_str}-vcp-technique]] for full technique documentation.

*Generated by nse-trading-researcher*
"""

    with open(filepath, "w") as f:
        f.write(content)

    return filepath


def save_technique_note() -> str:
    """Save the VCP technique documentation to vault."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(RESEARCH_DIR, "01-Techniques", f"{date_str}-vcp-technique.md")

    content = f"""---
tags: [technique, vcp, volatility-contraction, minervini, nse]
date: {date_str}
---

# Volatility Contraction Pattern (VCP) — NSE Adaptation

## Source
- **Found by**: nse-trading-researcher (GitHub → Negi27921/one-piece)
- **Date**: {date_str}
- **Link**: https://github.com/Negi27921/one-piece
- **Category**: New indicator (Market Breadth / Stock Screener)

## Description
Volatility Contraction Pattern (VCP) — Mark Minervini's SEPA methodology adapted for NSE stocks. Detects stocks undergoing sequential volatility contraction (4+ waves of tightening ranges, drying volume, preserved uptrend) ahead of potential breakouts. This is a STOCK-LEVEL screener that, when aggregated, provides a market-breadth signal.

## Mechanics
```
VCP = 10-condition check:
1. EMA Stack (10>20>50)
2. Price > SMA 200
3. RSI Momentum (45-70)
4. Higher High/Low (40 days)
5. 4-Wave Contraction (each wave range smaller than prior)
6. Tight Base ≤8% (7 days)
7. Prior Base ≤20% (21 days)
8. Volume Drying (<65% of 20-day avg)
9. No Change of Character (no lower low)
10. Liquidity (avg vol > 50,000)

VCP Present: ≥7 conditions passed (70% confidence)
Strong VCP: ≥8 conditions passed (80%+ confidence)
```

## Original Parameters
- Waves: 4 waves of 15 periods each
- Base tightness: 8% (7d), 20% (21d)
- Volume dry-up threshold: 65% of 20d avg
- RSI zone: 45-70

## NSE Applicability
- **Can we implement this?** Yes — uses yfinance data
- Built as: `~/.hermes/scripts/nse_vcp_scanner.py`
- Used as: Market breadth signal for the 8-factor engine

## Backtest Status
- [ ] Not tested
- [x] Backtest in progress
- [ ] Backtest completed
- [ ] Integrated
- [ ] Rejected

## Key Insights
- VCP Breadth > 20% = constructive market structure (many stocks setting up)
- VCP Breadth < 10% = weak market (few bases forming)
- This is a breadth signal, not a direct trade signal
- Most valuable as an additive factor to the 8-factor engine

## Related
- [[signal-engine-8-factor]] — could add VCP Breadth as 9th factor
- [[{date_str}-vcp-breadth]] — latest breadth scan results
"""

    with open(filepath, "w") as f:
        f.write(content)

    return filepath


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NSE VCP Scanner — detect Volatility Contraction Patterns")
    parser.add_argument("--universe", choices=["nifty50", "nifty500"], default="nifty50",
                        help="Stock universe to scan (default: nifty50)")
    parser.add_argument("--output", choices=["text", "json", "md"], default="text",
                        help="Output format")
    parser.add_argument("--save", action="store_true", help="Save results to vault")
    args = parser.parse_args()

    if args.universe == "nifty50":
        tickers = NIFTY_50_TICKERS
    else:
        # For nifty500, use the same but warn it's limited without full list
        print("⚠️  Full Nifty 500 list not available. Using Nifty 50.")
        tickers = NIFTY_50_TICKERS

    results = scan_universe(tickers)

    # Summary
    traded = [r for r in results if not r.get("error")]
    vcp_hits = [r for r in traded if r["vcp_present"]]
    vcp_breadth = len(vcp_hits) / len(traded) * 100 if traded else 0

    report = format_report(results, args.output)
    print("\n" + report)

    if args.save:
        vault_path = save_vault_report(report, results)
        technique_path = save_technique_note()
        print(f"\n📂 Saved to vault:")
        print(f"   Breadth: {vault_path}")
        print(f"   Technique: {technique_path}")

    # Final actionable output
    print(f"\n{'='*50}")
    print(f"📊 VCP BREADTH: {vcp_breadth:.1f}%  ({len(vcp_hits)}/{len(traded)} stocks)")
    if vcp_breadth > 20:
        print("   Signal: ✅ BULLISH — constructive market structure")
    elif vcp_breadth > 10:
        print("   Signal: ➡️ NEUTRAL — moderate VCP activity")
    else:
        print("   Signal: ❌ WEAK — few stocks setting up")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()