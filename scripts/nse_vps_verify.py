#!/usr/bin/env python3
"""VPS verification — checks morning bias vs actual close."""
import json, os, sys, warnings
warnings.filterwarnings('ignore')

DATA_DIR = os.path.expanduser('~/.hermes/data/nse_signals')
MORNING_FILE = os.path.join(DATA_DIR, 'pre_market.json')

import yfinance as yf
t = yf.Ticker('^NSEI')
h = t.history(period='2d')
if not h.empty:
    actual_close = round(h['Close'].iloc[-1], 2)
    prev_day = round(h['Close'].iloc[-2], 2) if len(h) > 1 else None
    change_pct = round((actual_close - prev_day) / prev_day * 100, 2) if prev_day else 0
    
    print(f'Nifty Close: {actual_close} ({change_pct:+.2f}%)')
    print(f'Prev Close: {prev_day}')
    
    # Determine bias
    if change_pct > 0.5:
        print(f'Actual Bias: BULLISH')
    elif change_pct > 0.15:
        print(f'Actual Bias: MILD_BULLISH')
    elif change_pct > -0.15:
        print(f'Actual Bias: NEUTRAL')
    elif change_pct > -0.5:
        print(f'Actual Bias: MILD_BEARISH')
    else:
        print(f'Actual Bias: BEARISH')
    
    # Check if morning signal exists
    if os.path.exists(MORNING_FILE):
        with open(MORNING_FILE) as f:
            morning = json.load(f)
        morning_price = morning.get('nifty', {}).get('price', 0)
        morning_prev = morning.get('prev_close', 0)
        if morning_price and morning_prev:
            # Run signal engine verify
            sys.path.insert(0, os.path.expanduser('~/.hermes/scripts'))
            from nse_signal_engine import verify_signal, format_verification
            result = verify_signal(MORNING_FILE, actual_close)
            print()
            print(format_verification(result))
else:
    print('ERROR: No data from Yahoo Finance')
