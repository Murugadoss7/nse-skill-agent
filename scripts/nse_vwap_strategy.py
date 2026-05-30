"""
VWAP Trading Strategy for NSE
================================
Based on the VWAP strategy concept (close vs rolling VWAP cross),
adapted for daily Nifty data from yfinance.

VWAP (Volume-Weighted Average Price) is calculated as:
  VWAP = Σ(Volume_i × Typical_Price_i) / Σ(Volume_i)

Where Typical_Price = (High + Low + Close) / 3

Strategy rules:
- Rolling VWAP(5) acts as dynamic support/resistance
- BUY when Close crosses ABOVE VWAP
- SELL when Close crosses BELOW VWAP
- Holding period: next-day directional prediction
"""
import pandas as pd
import numpy as np

def compute_vwap(data, period=5):
    """Compute rolling VWAP from OHLCV data.
    
    VWAP = Σ(V_i * TP_i) / Σ(V_i)
    where TP_i = (H_i + L_i + C_i) / 3
    """
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    vwap = (typical_price * data['Volume']).rolling(period).sum() / data['Volume'].rolling(period).sum()
    return vwap

def compute_vwap_signal(data, short_period=5, long_period=20):
    """Generate VWAP cross signals.
    
    Returns:
        signal: 1 (bullish), -1 (bearish), 0 (neutral)
        vwap_short: short-term VWAP
        vwap_long: long-term VWAP
    """
    vwap_short = compute_vwap(data, short_period)
    vwap_long = compute_vwap(data, long_period)
    
    # VWAP cross: short VWAP crossing long VWAP
    prev_short = vwap_short.shift(1)
    prev_long = vwap_long.shift(1)
    
    # Buy signal: short VWAP crosses above long VWAP
    buy_cross = (prev_short <= prev_long) & (vwap_short > vwap_long)
    
    # Sell signal: short VWAP crosses below long VWAP  
    sell_cross = (prev_short >= prev_long) & (vwap_short < vwap_long)
    
    # Also use close vs VWAP for trend
    close_above_vwap = data['Close'] > vwap_short
    close_below_vwap = data['Close'] < vwap_short
    
    signal = pd.Series(0, index=data.index)
    signal[buy_cross & close_above_vwap] = 2  # Strong buy
    signal[buy_cross] = 1  # Buy
    signal[sell_cross & close_below_vwap] = -2  # Strong sell
    signal[sell_cross] = -1  # Sell
    
    return signal, vwap_short, vwap_long


if __name__ == '__main__':
    # Quick test
    import yfinance as yf
    
    nifty = yf.download("^NSEI", period="2y", auto_adjust=True, progress=False)
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.droplevel(1)
    
    signal, vwap_s, vwap_l = compute_vwap_signal(nifty, 5, 20)
    
    # Forward test
    next_return = nifty['Close'].pct_change().shift(-1) * 100
    
    correct = 0
    total = 0
    results = []
    for i in range(len(nifty)):
        sig = signal.iloc[i]
        ret = next_return.iloc[i]
        if sig != 0 and not pd.isna(ret):
            pred_dir = 1 if sig > 0 else -1
            actual_dir = 1 if ret > 0 else (-1 if ret < 0 else 0)
            if actual_dir != 0:
                total += 1
                if pred_dir == actual_dir:
                    correct += 1
                results.append({'correct': pred_dir == actual_dir, 'signal': sig, 'return': ret})
    
    print(f"VWAP Crossover Strategy (2y Nifty)")
    print(f"  Signals: {total} trades")
    print(f"  Win Rate: {correct}/{total} = {correct/max(1,total)*100:.1f}%")
    
    # By signal strength
    strong_bull = [r for r in results if r['signal'] >= 2]
    mild_bull = [r for r in results if r['signal'] == 1]
    strong_bear = [r for r in results if r['signal'] <= -2]
    mild_bear = [r for r in results if r['signal'] == -1]
    
    for name, group in [('Strong Bull (+2)', strong_bull), ('Mild Bull (+1)', mild_bull),
                        ('Mild Bear (-1)', mild_bear), ('Strong Bear (-2)', strong_bear)]:
        if group:
            c = sum(1 for r in group if r['correct'])
            print(f"  {name}: {c}/{len(group)} = {c/len(group)*100:.1f}%")