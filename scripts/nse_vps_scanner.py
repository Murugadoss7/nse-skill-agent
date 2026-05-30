#!/usr/bin/env python3
"""
NSE VPS Scanner — standalone pre-market signal generator
Fetches data via yfinance (works from VPS IP), runs signal engine, outputs report.
Designed for no_agent=True cron jobs on Hermes.
"""
import json, os, sys, warnings
from datetime import datetime

warnings.filterwarnings('ignore')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser('~/.hermes/data/nse_signals')
os.makedirs(DATA_DIR, exist_ok=True)

# ── Step 1: Fetch data via yfinance ───────────────────────────────
def fetch_data():
    import yfinance as yf
    data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'nifty': {}, 'bank_nifty': {}, 'peers': {}, 'us_futures': {},
        'crude': {}, 'usd_inr': {}, 'dxy': {}, 'india_vix': {},
        'gift_nifty': {},
    }
    
    tickers = {
        '^NSEI': ('nifty', 'nifty'),
        '^NSEBANK': ('bank_nifty', 'bank_nifty'),
        '^N225': ('nikkei', 'peers'),
        '^HSI': ('hangseng', 'peers'),
        'BZ=F': ('crude', 'crude'),
        'USDINR=X': ('usd_inr', 'usd_inr'),
        '^INDIAVIX': ('india_vix', 'india_vix'),
        'ES=F': ('us_futures', 'us_futures'),
        'DX-Y.NYB': ('dxy', 'dxy'),
    }
    
    for sym, (key, group) in tickers.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period='5d')
            if not h.empty:
                close = h['Close'].iloc[-1]
                prev_close = h['Close'].iloc[-2] if len(h) > 1 else None
                change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0
                
                entry = {'price': round(close, 2), 'change_pct': round(change_pct, 2)}
                
                if group == 'peers':
                    data['peers'][key] = entry
                elif key == 'india_vix':
                    data['india_vix'] = {'level': round(close, 2), 'change_pct': round(change_pct, 2)}
                else:
                    data[key] = entry
        except Exception as e:
            pass  # Skip if unavailable
    
    # Estimate gift_nifty from Nifty
    nifty = data.get('nifty', {})
    nifty_prev = nifty.get('change_pct', 0)
    data['gift_nifty'] = {'price': 0, 'change_pct': round(nifty_prev * 0.7, 2)}
    
    # Add prev_close for verification
    if data.get('nifty', {}).get('price'):
        try:
            t = yf.Ticker('^NSEI')
            h = t.history(period='5d')
            if len(h) >= 2:
                data['prev_close'] = round(h['Close'].iloc[-2], 2)
        except:
            data['prev_close'] = data['nifty']['price']
    
    return data

# ── Step 2: Save and Run Engine ───────────────────────────────────
def main():
    data = fetch_data()
    
    # Save raw data
    raw_path = os.path.join(DATA_DIR, 'pre_market.json')
    with open(raw_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Run signal engine
    sys.path.insert(0, SCRIPTS_DIR)
    from nse_signal_engine import compute_signal, save_signal, format_report
    
    signal = compute_signal(data)
    save_signal(signal)
    print(format_report(signal))
    
    # Summary line for quick parsing
    bias = signal['signal']['bias']
    conf = signal['signal']['confidence']
    ctx = signal['market_context']
    print(f'\n[SIGNAL_SUMMARY] {bias} | Confidence: {conf}/10 | {ctx}')
    

if __name__ == '__main__':
    main()
