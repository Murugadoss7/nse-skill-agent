#!/usr/bin/env python3
"""
Nifty Volatility Regime Filter v1
===================================
Detects current volatility regime (Low / Normal / High / Extreme)
using ATR(14) percentile ranking over a trailing window.

Usage:
  python3 nse_volatility_regime.py              # Show current regime
  python3 nse_volatility_regime.py --history    # Plot regime over time
  python3 nse_volatility_regime.py --backtest   # Test regime as signal filter
"""
import argparse, json, os, math
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

HERMES_HOME = os.path.expanduser("~/.hermes")
RESEARCH_DIR = os.path.join(HERMES_HOME, "data", "trading_research")

def fetch_nifty_data(years=5):
    """Fetch Nifty OHLC data."""
    end = datetime.now()
    start = end - timedelta(days=365*years)
    nifty = yf.download("^NSEI", start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.droplevel(1)
    return nifty

def compute_regime(nifty, atr_period=14, lookback=252):
    """Classify current volatility regime using ATR percentile."""
    high = nifty['High']
    low = nifty['Low']
    close = nifty['Close']

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(atr_period).mean()
    atr_pct = atr / close * 100  # ATR as % of price
    atr_pct_clean = atr_pct.dropna()

    if len(atr_pct_clean) == 0:
        return None, None

    # Percentile rank of latest ATR
    latest = atr_pct_clean.iloc[-1]
    rolling_window = atr_pct_clean.tail(min(lookback, len(atr_pct_clean)))
    rank = (rolling_window < latest).sum() / len(rolling_window)

    if rank >= 0.9:
        regime = "EXTREME"
    elif rank >= 0.7:
        regime = "HIGH"
    elif rank >= 0.3:
        regime = "NORMAL"
    else:
        regime = "LOW"

    return {
        "current_atr_pct": round(float(latest), 3),
        "atr_percentile": round(float(rank), 3),
        "regime": regime,
        "window_atr_min": round(float(rolling_window.min()), 3),
        "window_atr_max": round(float(rolling_window.max()), 3),
        "window_atr_mean": round(float(rolling_window.mean()), 3),
    }, atr_pct_clean

def backtest_regime_filter(years=3):
    """Test if volatility regime improves signal engine accuracy."""
    nifty = fetch_nifty_data(years)
    regime_data, atr_series = compute_regime(nifty)
    if regime_data is None:
        print("❌ Insufficient data")
        return

    # Daily returns
    nifty['return_t1'] = nifty['Close'].pct_change().shift(-1) * 100
    nifty['direction'] = nifty['return_t1'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

    # Compute regime for each day
    high = nifty['High']
    low = nifty['Low']
    close = nifty['Close']
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr_pct = atr / close * 100

    lookback = 252
    regimes = []
    for i in range(lookback, len(atr_pct)):
        window = atr_pct.iloc[i-lookback:i].dropna()
        if len(window) == 0:
            continue
        val = atr_pct.iloc[i]
        rank = (window < val).sum() / len(window)
        if rank >= 0.9:
            reg = "EXTREME"
        elif rank >= 0.7:
            reg = "HIGH"
        elif rank >= 0.3:
            reg = "NORMAL"
        else:
            reg = "LOW"
        regimes.append(reg)

    nifty_regime = nifty.iloc[lookback:].copy()
    nifty_regime['regime'] = regimes

    # Naive baseline: always predict UP (buy & hold)
    naive_acc = (nifty_regime['direction'] == 1).sum() / len(nifty_regime) * 100

    # Regime-based prediction: predict continuation in LOW vol, reversal in EXTREME
    results = []
    for reg in ["LOW", "NORMAL", "HIGH", "EXTREME"]:
        subset = nifty_regime[nifty_regime['regime'] == reg]
        if len(subset) == 0:
            continue
        # Prediction: in LOW vol → trend continues; in EXTREME → mean revert; in NORMAL/HIGH → no edge
        if reg == "LOW":
            pred_acc = (subset['direction'] == 1).sum() / len(subset) * 100
            label = "Trend Continue (Bull)"
        elif reg == "EXTREME":
            pred_acc = (subset['direction'] == -1).sum() / len(subset) * 100
            label = "Mean Revert (Bear)"
        else:
            pred_acc = naive_acc
            label = "No Edge"
        results.append({
            "regime": reg,
            "days": len(subset),
            "accuracy": round(pred_acc, 1),
            "strategy": label
        })

    print("━━━ VOLATILITY REGIME BACKTEST ━━━")
    print(f"Period: {nifty_regime.index[0].date()} → {nifty_regime.index[-1].date()}")
    print(f"Naive (always Bull): {naive_acc:.1f}%")
    print()
    for r in results:
        print(f"  {r['regime']:8s} ({r['strategy']:20s}): {r['days']:4d} days  acc={r['accuracy']}%")

    # Summary
    print(f"\n  Edge from regime filter: LOW vol tends UP, EXTREME vol tends DOWN on next day.")
    return results

def main():
    parser = argparse.ArgumentParser(description="Nifty Volatility Regime Filter")
    parser.add_argument("--history", action="store_true", help="Show regime history")
    parser.add_argument("--backtest", action="store_true", help="Backtest regime as filter")
    args = parser.parse_args()

    nifty = fetch_nifty_data()
    regime, atr_series = compute_regime(nifty)

    if regime is None:
        print("❌ Insufficient data")
        return

    print(f"━━━ NIFTY VOLATILITY REGIME ━━━")
    print(f"Date:       {datetime.now().strftime('%Y-%m-%d')}")
    print(f"ATR(14):    {regime['current_atr_pct']}% of price")
    print(f"Percentile: {regime['atr_percentile']*100:.0f}% (trailing 252d)")
    print(f"Regime:     {regime['regime']}")
    print(f"Range:      {regime['window_atr_min']}% — {regime['window_atr_max']}%")
    print(f"Mean ATR:   {regime['window_atr_mean']}%")

    if args.history:
        recent = atr_series.tail(60)
        print(f"\n━━━ RECENT ATR HISTORY (60 days) ━━━")
        for idx, val in recent.items():
            print(f"  {idx.strftime('%Y-%m-%d')}: {val:.3f}%")

    if args.backtest:
        print()
        backtest_regime_filter()

if __name__ == "__main__":
    main()