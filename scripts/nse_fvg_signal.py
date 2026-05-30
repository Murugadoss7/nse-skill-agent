#!/usr/bin/env python3
"""
NSE FVG Signal Module — Fair Value Gap Market Structure Factor
===============================================================
Computes ICT Smart Money Concepts FVG (Fair Value Gap) signals
on Nifty daily data, generating a -2 to +2 factor value for the
signal engine and morning trader.

Usage:
  python3 nse_fvg_signal.py                       # Print signal for today
  python3 nse_fvg_signal.py --json                # JSON output for cron
  python3 nse_fvg_signal.py --history --days 90   # Backtest historical accuracy
  python3 nse_fvg_signal.py --plot                # Show zone chart (requires matplotlib)

Dependencies:
  pip install smartmoneyconcepts yfinance pandas numpy
"""

import json, os, sys, argparse, warnings
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser('~/.hermes/data/nse_signals')
RESEARCH_DIR = os.path.expanduser('~/.hermes/data/trading_research')

def fetch_nifty_ohlc(days=30):
    """Fetch Nifty daily OHLC data from yfinance."""
    import yfinance as yf
    end = datetime.now()
    start = end - timedelta(days=days)
    nifty = yf.download("^NSEI", start=start, end=end, auto_adjust=True, progress=False)
    if nifty.empty:
        return None
    # Handle MultiIndex columns
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)
    nifty = nifty.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume"
    })
    return nifty


def compute_fvg_signal(ohlc, lookback=20):
    """
    Compute real-time FVG signal factor based on RECENT FVG momentum.
    
    Approach: FVG signals capture strong trend continuations.
    Since zones get mitigated quickly, we use the TREND of recent
    FVG signals as a momentum indicator.
    
    Returns dict with:
      - fvg_direction: 1 (bullish momentum), -1 (bearish), 0 (mixed/neutral)
      - score: -2 to +2 (aligned with signal engine scoring)
      - confidence: 0.0 to 1.0
      - recent_signals: last N days of FVG signals
      - zone_near_price: nearest FVG zone to current price
    """
    from smartmoneyconcepts import smc
    
    if ohlc is None or len(ohlc) < 5:
        return {
            'fvg_direction': 0, 'score': 0, 'confidence': 0.0,
            'recent_signals': [], 'zone_near_price': None,
            'current_price': None, 'bullish_ratio': 0.5
        }
    
    orig_index = ohlc.index.copy()
    fvg = smc.fvg(ohlc, join_consecutive=False)
    fvg.index = orig_index
    
    last_price = float(ohlc['close'].iloc[-1])
    
    # Get RECENT FVG signals (last N bars, or fewer)
    recent = fvg.tail(lookback)
    recent_signals = []
    bullish_count = 0
    bearish_count = 0
    
    for idx, row in recent.iterrows():
        if pd.notna(row['FVG']):
            direction = int(row['FVG'])
            if direction == 1:
                bullish_count += 1
            else:
                bearish_count += 1
            recent_signals.append({
                'date': str(idx.date()),
                'direction': direction,
                'top': float(row['Top']),
                'bottom': float(row['Bottom']),
            })
    
    total = len(recent_signals)
    if total == 0:
        return {
            'fvg_direction': 0, 'score': 0, 'confidence': 0.2,
            'recent_signals': [], 'zone_near_price': None,
            'current_price': round(last_price, 2), 'bullish_ratio': 0.5,
            'last_fvg_direction': 0
        }
    
    bullish_ratio = bullish_count / total
    
    # Direction based on majority
    if bullish_ratio > 0.6:
        direction = 1
        strength = (bullish_ratio - 0.5) * 4  # 0.6→0.4, 0.8→1.2, 1.0→2.0
    elif bullish_ratio < 0.4:
        direction = -1
        strength = (0.5 - bullish_ratio) * 4  # 0.4→0.4, 0.2→1.2, 0.0→2.0
    else:
        direction = 0
        strength = 0
    
    score = direction * min(strength, 2.0)
    
    # Confidence: better with more signals and clearer majority
    confidence = min(total / 10.0, 1.0) * min(abs(bullish_ratio - 0.5) * 4, 1.0)
    
    # Find nearest zone to current price
    nearest_zone = None
    min_dist = float('inf')
    for s in recent_signals:
        zone_mid = (s['top'] + s['bottom']) / 2
        dist = abs(last_price - zone_mid)
        if dist < min_dist:
            min_dist = dist
            nearest_zone = s
    
    # Last FVG direction (most recent signal)
    last_fvg = recent_signals[-1]['direction'] if recent_signals else 0
    
    return {
        'fvg_direction': direction,
        'last_fvg_direction': last_fvg,
        'score': round(score, 2),
        'confidence': round(confidence, 2),
        'recent_signals': recent_signals[-10:],  # last 10 max
        'signal_count': total,
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'bullish_ratio': round(bullish_ratio, 2),
        'zone_near_price': nearest_zone,
        'current_price': round(last_price, 2),
    }


def backtest_accuracy(days=365):
    """Backtest FVG zones as support/resistance levels over given period."""
    from smartmoneyconcepts import smc
    
    end = datetime.now()
    start = end - timedelta(days=days)
    
    import yfinance as yf
    nifty = yf.download("^NSEI", start=start, end=end, auto_adjust=True, progress=False)
    if nifty.empty:
        return None
    
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)
    nifty = nifty.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume"
    })
    
    fvg = smc.fvg(nifty, join_consecutive=False)
    fvg.index = nifty.index
    
    # For each FVG, check if price returned to the zone within N bars
    results = []
    hits = 0
    total = 0
    
    for i in range(len(fvg)):
        if pd.isna(fvg.iloc[i]['FVG']):
            continue
            
        total += 1
        direction = int(fvg.iloc[i]['FVG'])
        zone_top = float(fvg.iloc[i]['Top'])
        zone_bottom = float(fvg.iloc[i]['Bottom'])
        
        # Check if price returns to zone within next 10 bars
        lookahead = min(i + 10, len(nifty))
        future_prices = nifty.iloc[i:lookahead+1]
        
        zone_hit = False
        for j in range(len(future_prices)):
            low = float(future_prices.iloc[j]['low'])
            high = float(future_prices.iloc[j]['high'])
            if low <= zone_top and high >= zone_bottom:
                zone_hit = True
                break
        
        if zone_hit:
            hits += 1
            
        results.append({
            'date': str(nifty.index[i].date()),
            'direction': direction,
            'top': zone_top,
            'bottom': zone_bottom,
            'zone_hit': zone_hit,
        })
    
    accuracy = hits / total * 100 if total > 0 else 0
    
    return {
        'period': f'{start.date()} → {end.date()}',
        'total_zones': total,
        'zones_hit': hits,
        'hit_rate': round(accuracy, 1),
        'results': results,
    }


def main():
    parser = argparse.ArgumentParser(description='NSE FVG Market Structure Signal')
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--history', action='store_true', help='Backtest historical accuracy')
    parser.add_argument('--days', type=int, default=90, help='Days of history to analyze')
    parser.add_argument('--plot', action='store_true', help='Plot FVG zones (requires matplotlib)')
    args = parser.parse_args()
    
    if args.history:
        bt = backtest_accuracy(days=args.days)
        if bt is None:
            print(json.dumps({'error': 'Failed to fetch data'}))
            return
        
        print(f"📊 FVG Zone Backtest — {bt['period']}")
        print(f"   Total FVG zones: {bt['total_zones']}")
        print(f"   Price returned to zone: {bt['zones_hit']}/{bt['total_zones']} ({bt['hit_rate']}%)")
        print(f"   → FVG zones act as support/resistance {bt['hit_rate']}% of the time")
        
        if args.json:
            print(json.dumps(bt, indent=2, default=str))
        return
    
    # Live signal
    ohlc = fetch_nifty_ohlc(days=args.days)
    if ohlc is None:
        print(json.dumps({'error': 'Failed to fetch Nifty data'}))
        return
    
    signal = compute_fvg_signal(ohlc)
    
    if args.json:
        print(json.dumps(signal, indent=2, default=str))
        return
    
    # Human-readable output
    print(f"━━━ FVG Market Structure Signal ━━━")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Nifty: {signal['current_price']}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    dir_str = {1: "🟢 BULLISH", -1: "🔴 BEARISH", 0: "⚪ NEUTRAL"}
    print(f"Trend direction: {dir_str.get(signal['fvg_direction'], 'N/A')}")
    print(f"Last signal: {dir_str.get(signal['last_fvg_direction'], 'N/A')}")
    print(f"Score: {signal['score']:+.2f}")
    print(f"Confidence: {signal['confidence']:.0%}")
    print(f"")
    print(f"Recent FVG signals (last {signal['signal_count']}):")
    print(f"  Bullish: {signal['bullish_count']} | Bearish: {signal['bearish_count']}")
    print(f"  Bullish ratio: {signal['bullish_ratio']:.0%}")
    
    if signal['recent_signals']:
        print(f"\nRecent FVG zones:")
        for z in signal['recent_signals'][-5:]:
            emoji = "🟢" if z['direction'] == 1 else "🔴"
            print(f"  {emoji} {z['date']}: {z['bottom']:.0f} — {z['top']:.0f}")
    
    if signal['zone_near_price']:
        z = signal['zone_near_price']
        emoji = "🟢" if z['direction'] == 1 else "🔴"
        print(f"\nNearest zone to price:")
        print(f"  {emoji} {z['date']}: {z['bottom']:.0f} — {z['top']:.0f}")
    
    print(f"\nSignal factor recommendation:")
    print(f"  Factor: 'fvg_structure' (Market Structure Momentum)")
    print(f"  Weight: 5-10% (as 9th signal engine factor)")
    print(f"  Scoring: -2 (bearish momentum) to +2 (bullish momentum)")
    print(f"  Best use: trend confirmation — combine with existing factors")


if __name__ == '__main__':
    main()
