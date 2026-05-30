#!/usr/bin/env python3
"""
NSE Backtesting Engine v1
=========================
Generic backtesting framework for NSE trading strategies.

Usage:
  python3 nse_backtest_engine.py --strategy signal-engine --period 3y
  python3 nse_backtest_engine.py --strategy ma-crossover --period 5y --output md
  python3 nse_backtest_engine.py --list-strategies
  python3 nse_backtest_engine.py --strategy signal-engine --compare-baseline

Output: JSON data + optional markdown report for Obsidian vault.
"""

import json, os, sys, argparse, math
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

HERMES_HOME = os.path.expanduser("~/.hermes")
RESEARCH_DIR = os.path.join(HERMES_HOME, "data", "trading_research")
DATA_DIR = os.path.join(HERMES_HOME, "data", "nse_signals")
SCRIPTS_DIR = os.path.join(HERMES_HOME, "scripts")

os.makedirs(os.path.join(RESEARCH_DIR, "02-Backtests"), exist_ok=True)

# ── Strategy Registry ──────────────────────────────────────────────────────

STRATEGIES = {}

def register(name, description):
    """Decorator to register a strategy"""
    def wrapper(cls):
        STRATEGIES[name] = {"class": cls, "description": description}
        return cls
    return wrapper

def load_yfinance_data():
    """Lazy import yfinance and fetch data. Returns dict of DataFrames."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Install with: pip install yfinance")
        sys.exit(1)

    end = datetime.now()
    start = end - timedelta(days=365*5)  # 5 years

    print(f"📥 Fetching data: {start.date()} → {end.date()}")

    # Nifty
    nifty = yf.download("^NSEI", start=start, end=end, auto_adjust=True, progress=False)
    # Key factors
    crude = yf.download("BZ=F", start=start, end=end, auto_adjust=True, progress=False)
    usdinr = yf.download("USDINR=X", start=start, end=end, auto_adjust=True, progress=False)
    vix = yf.download("INDIAVIX.NS", start=start, end=end, auto_adjust=True, progress=False)
    dxy = yf.download("DX-Y.NYB", start=start, end=end, auto_adjust=True, progress=False)
    spx = yf.download("^GSPC", start=start, end=end, auto_adjust=True, progress=False)
    n225 = yf.download("^N225", start=start, end=end, auto_adjust=True, progress=False)
    hsi = yf.download("^HSI", start=start, end=end, auto_adjust=True, progress=False)
    bank_nifty = yf.download("^NSEBANK", start=start, end=end, auto_adjust=True, progress=False)

    return {
        "nifty": nifty,
        "crude": crude,
        "usdinr": usdinr,
        "vix": vix,
        "dxy": dxy,
        "spx": spx,
        "n225": n225,
        "hsi": hsi,
        "bank_nifty": bank_nifty,
    }

def compute_pct_change(data, period=1):
    """Compute percentage change, handling NaN"""
    if data is None or data.empty:
        return None
    pct = data['Close'].pct_change(period) * 100
    return pct

def compute_sma(data, period):
    """Compute Simple Moving Average"""
    return data['Close'].rolling(window=period).mean()

def safe_float(val, default=0.0):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return float(val)


# ── Strategy: Signal Engine (Current 8-Factor Model) ────────────────────────

@register("signal-engine", "Current 8-factor signal engine model")
class SignalEngineStrategy:
    def __init__(self):
        self.name = "Signal Engine (8-Factor)"
        self.params = {
            "weights": {
                "gift_nifty": 0.20, "asian_peers": 0.15, "crude_oil": 0.15,
                "india_vix": 0.15, "us_futures": 0.10, "usd_inr": 0.10,
                "bank_nifty": 0.10, "dxy": 0.05,
            },
            "thresholds": {
                "crude_oil": (-1.5, -0.5, 0.5, 1.5),
                "usd_inr": (-0.3, -0.1, 0.1, 0.3),
                "dxy": (-0.4, -0.2, 0.2, 0.4),
                "india_vix": (14.0, 18.0, 22.0, 28.0),
                "asian_peers": (-1.0, -0.3, 0.3, 1.0),
                "us_futures": (-0.8, -0.3, 0.3, 0.8),
                "gift_nifty": (-0.8, -0.3, 0.3, 0.8),
                "bank_nifty_rel": (-1.0, -0.3, 0.3, 1.0),
            }
        }

    def score_factor(self, value, threshold, mode="change_pct"):
        """Score a factor value on -2 to +2 scale."""
        if mode == "vix_level":
            t1, t2, t3, t4 = threshold
            if value <= t1: return 2
            if value <= t2: return 1
            if value <= t3: return 0
            if value <= t4: return -1
            return -2

        # Default: change_pct mode
        t1, t2, t3, t4 = threshold
        if value <= t1: return -2
        if value <= t2: return -1
        if value <= t3: return 1
        if value <= t4: return 2
        return 0

    def generate_signal(self, data):
        """Generate signal for a single day. data = dict of price levels."""
        weights = self.params["weights"]
        thresholds = self.params["thresholds"]
        total_score = 0.0
        raw_scores = {}

        # Gift Nifty (estimated from Nifty)
        if data.get("nifty_change_pct") is not None:
            raw_scores["gift_nifty"] = self.score_factor(
                safe_float(data["nifty_change_pct"]) * 0.7,
                thresholds["gift_nifty"]
            )
        else:
            raw_scores["gift_nifty"] = 0

        # Asian Peers
        asian_avg = None
        n225_v = safe_float(data.get("n225_change"))
        hsi_v = safe_float(data.get("hsi_change"))
        if n225_v is not None and hsi_v is not None:
            asian_avg = (n225_v + hsi_v) / 2
        raw_scores["asian_peers"] = self.score_factor(asian_avg if asian_avg else 0, thresholds["asian_peers"])

        # Crude Oil
        raw_scores["crude_oil"] = self.score_factor(safe_float(data.get("crude_change")), thresholds["crude_oil"])

        # VIX
        vix_level = safe_float(data.get("vix_level"), 20.0)
        raw_scores["india_vix"] = self.score_factor(vix_level, thresholds["india_vix"], mode="vix_level")

        # US Futures
        raw_scores["us_futures"] = self.score_factor(safe_float(data.get("spx_change")), thresholds["us_futures"])

        # USD/INR
        raw_scores["usd_inr"] = self.score_factor(safe_float(data.get("usdinr_change")), thresholds["usd_inr"])

        # DXY
        raw_scores["dxy"] = self.score_factor(safe_float(data.get("dxy_change")), thresholds["dxy"])

        # Bank Nifty relative
        bank_nifty_rel = None
        nifty_c = safe_float(data.get("nifty_change_pct"))
        bank_c = safe_float(data.get("bank_nifty_change"))
        if nifty_c is not None and bank_c is not None:
            bank_nifty_rel = bank_c - nifty_c
        raw_scores["bank_nifty"] = self.score_factor(bank_nifty_rel if bank_nifty_rel else 0, thresholds["bank_nifty_rel"])

        # Weighted score
        for factor, score in raw_scores.items():
            total_score += score * weights[factor]

        # Bias determination
        if total_score >= 1.0:
            bias = "BULLISH"
            confidence = min(10, int(7 + (total_score - 1.0) * 2))
        elif total_score >= 0.3:
            bias = "MILD_BULLISH"
            confidence = int(4 + (total_score - 0.3) * 5)
        elif total_score >= -0.3:
            bias = "NEUTRAL"
            confidence = int(3 + abs(total_score) * 3)
        elif total_score >= -1.0:
            bias = "MILD_BEARISH"
            confidence = int(4 + abs(total_score + 0.3) * 5)
        else:
            bias = "BEARISH"
            confidence = min(10, int(7 + (abs(total_score) - 1.0) * 2))

        return {
            "bias": bias,
            "score": round(total_score, 3),
            "confidence": confidence,
            "raw_scores": {k: int(v) for k, v in raw_scores.items()}
        }


# ── Strategy: Moving Average Crossover ─────────────────────────────────────

@register("ma-crossover", "SMA-20 vs SMA-50 crossover on Nifty")
class MACrossoverStrategy:
    def __init__(self):
        self.name = "MA Crossover (20/50)"

    def generate_signal(self, data):
        sma20 = safe_float(data.get("sma_20"))
        sma50 = safe_float(data.get("sma_50"))
        close = safe_float(data.get("nifty_close"))
        prev_sma20 = safe_float(data.get("prev_sma_20"))
        prev_sma50 = safe_float(data.get("prev_sma_50"))

        if not all([sma20, sma50, prev_sma20, prev_sma50]):
            return {"bias": "NEUTRAL", "score": 0, "confidence": 1}

        # Crossover detection
        if prev_sma20 <= prev_sma50 and sma20 > sma50:
            return {"bias": "BULLISH", "score": 2.0, "confidence": 8}
        elif prev_sma20 >= prev_sma50 and sma20 < sma50:
            return {"bias": "BEARISH", "score": -2.0, "confidence": 8}

        # Trend strength (distance between MAs)
        dist = (sma20 - sma50) / sma50 * 100
        if dist > 1.0:
            return {"bias": "BULLISH", "score": 1.0, "confidence": 5}
        elif dist < -1.0:
            return {"bias": "BEARISH", "score": -1.0, "confidence": 5}
        return {"bias": "NEUTRAL", "score": 0.3, "confidence": 3}


# ── Strategy: RSI Mean Reversion ──────────────────────────────────────────

@register("rsi-reversal", "RSI overbought/oversold mean reversion")
class RSIReversalStrategy:
    def __init__(self):
        self.name = "RSI Mean Reversion"

    def generate_signal(self, data):
        rsi = safe_float(data.get("rsi_14"))
        if rsi is None or rsi == 0:
            return {"bias": "NEUTRAL", "score": 0, "confidence": 1}

        if rsi < 30:
            return {"bias": "BULLISH", "score": 2.0, "confidence": 7}
        elif rsi < 40:
            return {"bias": "MILD_BULLISH", "score": 1.0, "confidence": 5}
        elif rsi > 70:
            return {"bias": "BEARISH", "score": -2.0, "confidence": 7}
        elif rsi > 60:
            return {"bias": "MILD_BEARISH", "score": -1.0, "confidence": 5}
        return {"bias": "NEUTRAL", "score": 0, "confidence": 3}


# ── Strategy: Gap Follow-Through ─────────────────────────────────────────────

@register("gap-followthrough", "Gap detection + follow-through signal (adapted from NSE-Quant-Backtest)")
class GapFollowThroughStrategy:
    def __init__(self, gap_threshold_pct=0.7, atr_multiple=1.5, hold_max=5):
        self.name = f"Gap Follow-Through ({gap_threshold_pct}%)"
        self.gap_threshold = gap_threshold_pct / 100.0
        self.atr_multiple = atr_multiple
        self.hold_max = hold_max

    def generate_signal(self, data):
        # This strategy works across rows — we handle the stateful logic in the backtest loop.
        # Here we just compute per-row gap signals.
        open_p = safe_float(data.get("nifty_open"))
        close = safe_float(data.get("nifty"))
        prev_close = safe_float(data.get("prev_close"))
        atr = safe_float(data.get("atr_14"), 1.0)

        if not all([open_p, close, prev_close]):
            return {"bias": "NEUTRAL", "score": 0, "confidence": 1, "raw_scores": {"gap_long": 0, "gap_short": 0}}

        gap_up = (open_p > prev_close * (1 + self.gap_threshold)) and (close > open_p)
        gap_down = (open_p < prev_close * (1 - self.gap_threshold)) and (close < open_p)

        raw = {"gap_long": 1 if gap_up else 0, "gap_short": 1 if gap_down else 0}

        if gap_up:
            return {"bias": "BULLISH", "score": 2.0, "confidence": 7, "raw_scores": raw}
        elif gap_down:
            return {"bias": "BEARISH", "score": -2.0, "confidence": 7, "raw_scores": raw}
        return {"bias": "NEUTRAL", "score": 0, "confidence": 3, "raw_scores": raw}


# ── Strategy: NR7 Breakout ─────────────────────────────────────────────────

@register("nr7-breakout", "Narrow Range 7 — breakout after 7-session compression (adapted from NSE-Stock-Scanner)")
class NR7BreakoutStrategy:
    def __init__(self, use_trend_filter=False):
        self.name = "NR7 Breakout"
        self.use_trend_filter = use_trend_filter

    def generate_signal(self, data):
        nr7 = data.get("nr7_flag", 0)
        nr7_high = safe_float(data.get("nr7_high"))
        nr7_low = safe_float(data.get("nr7_low"))
        nifty_close = safe_float(data.get("nifty"))
        sma200 = safe_float(data.get("sma_200"))

        if not nr7 or not all([nr7_high, nr7_low, nifty_close]):
            return {"bias": "NEUTRAL", "score": 0, "confidence": 1, "raw_scores": {}}

        # Optional trend filter: close above SMA200 for long only
        if self.use_trend_filter and sma200 and nifty_close > sma200:
            # Long bias only in uptrend
            if nifty_close > nr7_high:
                return {"bias": "BULLISH", "score": 2.0, "confidence": 7,
                        "raw_scores": {"nr7_breakout_up": 1}}
            return {"bias": "NEUTRAL", "score": 0, "confidence": 3, "raw_scores": {}}

        # Dual-direction breakout
        if nifty_close > nr7_high:
            return {"bias": "BULLISH", "score": 2.0, "confidence": 7,
                    "raw_scores": {"nr7_breakout_up": 1}}
        elif nifty_close < nr7_low:
            return {"bias": "BEARISH", "score": -2.0, "confidence": 7,
                    "raw_scores": {"nr7_breakout_down": 1}}

        return {"bias": "NEUTRAL", "score": 0, "confidence": 3, "raw_scores": {}}


# ── Strategy: VWAP Crossover ─────────────────────────────────────────────────

@register("vwap-crossover", "VWAP(5) vs VWAP(20) crossover — close above VWAP = bullish, below = bearish")
class VWAPCrossoverStrategy:
    def __init__(self):
        self.name = "VWAP Crossover (5/20)"

    def generate_signal(self, data):
        close = safe_float(data.get("nifty"))
        vwap5 = safe_float(data.get("vwap_5"))
        vwap20 = safe_float(data.get("vwap_20"))
        prev_vwap5 = safe_float(data.get("prev_vwap_5"))
        prev_vwap20 = safe_float(data.get("prev_vwap_20"))

        if not all([close, vwap5, vwap20, prev_vwap5, prev_vwap20]):
            return {"bias": "NEUTRAL", "score": 0, "confidence": 1, "raw_scores": {}}

        # Crossover detection
        if prev_vwap5 <= prev_vwap20 and vwap5 > vwap20 and close > vwap5:
            return {"bias": "BULLISH", "score": 2.0, "confidence": 8,
                    "raw_scores": {"vwap_bullish_cross": 1}}
        elif prev_vwap5 <= prev_vwap20 and vwap5 > vwap20:
            return {"bias": "MILD_BULLISH", "score": 1.0, "confidence": 6,
                    "raw_scores": {"vwap_bullish": 1}}
        elif prev_vwap5 >= prev_vwap20 and vwap5 < vwap20 and close < vwap5:
            return {"bias": "BEARISH", "score": -2.0, "confidence": 7,
                    "raw_scores": {"vwap_bearish_cross": 1}}
        elif prev_vwap5 >= prev_vwap20 and vwap5 < vwap20:
            return {"bias": "MILD_BEARISH", "score": -1.0, "confidence": 5,
                    "raw_scores": {"vwap_bearish": 1}}

        # Trend alignment: close vs VWAP
        if close > vwap5 * 1.005:
            return {"bias": "MILD_BULLISH", "score": 0.5, "confidence": 4,
                    "raw_scores": {"vwap_close_above": 1}}
        elif close < vwap5 * 0.995:
            return {"bias": "MILD_BEARISH", "score": -0.5, "confidence": 4,
                    "raw_scores": {"vwap_close_below": 1}}
        return {"bias": "NEUTRAL", "score": 0, "confidence": 3, "raw_scores": {}}


# ── Compute RSI ────────────────────────────────────────────────────────────

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ── Run Backtest ─────────────────────────────────────────────────────────────

def run_backtest(strategy_name, period_years=3):
    """Run a full backtest of a strategy against Nifty historical data."""
    print(f"\n{'='*60}")
    print(f"📊 BACKTEST: {strategy_name}")
    print(f"{'='*60}")

    if strategy_name not in STRATEGIES:
        print(f"Unknown strategy: {strategy_name}")
        print(f"Available: {list(STRATEGIES.keys())}")
        return None

    strategy_cls = STRATEGIES[strategy_name]["class"]()
    data = load_yfinance_data()

    if any(df.empty for df in data.values()):
        print("⚠️  Some data sources returned empty. Proceeding with available data.")

    # Handle MultiIndex columns from yfinance
    cleaned = {}
    for name, df in data.items():
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            cleaned[name] = df
    data = cleaned

    # Align all data to common dates
    dfs = []
    for name, df in data.items():
        if df is not None and not df.empty:
            if name == 'nifty':
                # Keep OHLC for strategies that need range (NR7, gap) + Volume for VWAP
                cols = ['Open', 'High', 'Low', 'Close', 'Volume'] if 'Volume' in df.columns else ['Open', 'High', 'Low', 'Close']
                df = df[cols].rename(columns={
                    'Open': 'nifty_open', 'High': 'nifty_high',
                    'Low': 'nifty_low', 'Close': name, 'Volume': 'nifty_volume'
                }).copy()
            else:
                cols = ['Close']
                df = df[cols].rename(columns={'Close': name})
            dfs.append(df)

    if not dfs:
        print("❌ No data available.")
        return None

    from functools import reduce
    combined = reduce(lambda left, right: left.join(right, how='inner'), dfs)
    combined = combined.dropna()

    print(f"📈 Data points: {len(combined)} trading days")

    # Compute indicators that depend on available data
    change_cols = {
        'nifty': 'nifty_change_pct',
        'crude': 'crude_change',
        'usdinr': 'usdinr_change',
        'spx': 'spx_change',
        'n225': 'n225_change',
        'hsi': 'hsi_change',
        'dxy': 'dxy_change',
        'bank_nifty': 'bank_nifty_change',
    }
    for src_col, target_col in change_cols.items():
        if src_col in combined.columns:
            combined[target_col] = combined[src_col].pct_change() * 100

    # Moving averages
    if 'nifty' in combined.columns:
        combined['sma_20'] = combined['nifty'].rolling(20).mean()
        combined['sma_50'] = combined['nifty'].rolling(50).mean()
        combined['sma_200'] = combined['nifty'].rolling(200).mean()
        combined['prev_sma_20'] = combined['sma_20'].shift(1)
        combined['prev_sma_50'] = combined['sma_50'].shift(1)
        combined['rsi_14'] = compute_rsi(combined['nifty'])
        combined['prev_close'] = combined['nifty'].shift(1)
        # ATR for gap follow-through using real OHLC
        if 'nifty_high' in combined.columns and 'nifty_low' in combined.columns:
            high = combined['nifty_high']
            low = combined['nifty_low']
        else:
            high = combined['nifty'].rolling(2).max()
            low = combined['nifty'].rolling(2).min()
        tr = pd.concat([high - low,
                      (high - combined['nifty'].shift(1)).abs(),
                      (low - combined['nifty'].shift(1)).abs()], axis=1).max(axis=1)
        combined['atr_14'] = tr.rolling(14).mean()
        # VWAP computation using Volume
        if 'nifty_volume' in combined.columns and 'nifty_high' in combined.columns:
            typical = (combined['nifty_high'] + combined['nifty_low'] + combined['nifty']) / 3
            combined['vwap_5'] = (typical * combined['nifty_volume']).rolling(5).sum() / combined['nifty_volume'].rolling(5).sum()
            combined['vwap_20'] = (typical * combined['nifty_volume']).rolling(20).sum() / combined['nifty_volume'].rolling(20).sum()
        else:
            # Fallback: SMA if no volume data
            combined['vwap_5'] = combined['nifty'].rolling(5).mean()
            combined['vwap_20'] = combined['nifty'].rolling(20).mean()
        combined['prev_vwap_5'] = combined['vwap_5'].shift(1)
        combined['prev_vwap_20'] = combined['vwap_20'].shift(1)
        # Daily range and NR7 detection
        combined['range'] = high - low
        combined['nr7_flag'] = combined['range'].rolling(7).apply(
            lambda x: x.iloc[-1] == x.min(), raw=False
        )
        combined['nr7_high'] = combined['nifty_high'].rolling(7).max()
        combined['nr7_low'] = combined['nifty_low'].rolling(7).min()

    # VIX handling — might be empty or named differently
    vix_col = None
    for candidate in ['vix', '^VIX', 'INDIAVIX.NS']:
        if candidate in combined.columns:
            vix_col = candidate
            break
    if vix_col:
        combined['vix_level'] = combined[vix_col]
    else:
        combined['vix_level'] = 20.0  # Default VIX level

    # Drop NaN rows
    combined = combined.iloc[210:]  # Need 200 days for SMA200 + RSI warmup

    # Run backtest
    trades = []
    for idx in range(len(combined)):
        row = combined.iloc[idx]
        signal = strategy_cls.generate_signal(row.to_dict())
        next_return = combined['nifty_change_pct'].iloc[idx+1] if idx+1 < len(combined) else 0

        # Determine if prediction was correct
        if signal['bias'] in ('BULLISH', 'MILD_BULLISH'):
            pred_direction = 1
        elif signal['bias'] in ('BEARISH', 'MILD_BEARISH'):
            pred_direction = -1
        else:
            pred_direction = 0

        actual_direction = 1 if next_return > 0 else (-1 if next_return < 0 else 0)
        correct = pred_direction == actual_direction and pred_direction != 0

        trades.append({
            "date": row.name.strftime('%Y-%m-%d') if hasattr(row.name, 'strftime') else str(row.name),
            "bias": signal['bias'],
            "confidence": signal['confidence'],
            "score": signal['score'],
            "next_return": round(float(next_return), 3),
            "correct": correct,
            "raw_scores": signal.get('raw_scores', {})
        })

    # Compute metrics
    total = len(trades)
    non_neutral = [t for t in trades if t['bias'] not in ('NEUTRAL',)]
    correct_trades = [t for t in trades if t['correct']]
    neutral_trades = [t for t in trades if t['bias'] == 'NEUTRAL']

    win_rate = len(correct_trades) / len(non_neutral) * 100 if non_neutral else 0
    overall_accuracy = sum(1 for t in trades if t['correct'] and t['bias'] != 'NEUTRAL') / len(non_neutral) * 100 if non_neutral else 0

    # Sharpe-like: returns from directional trades
    directional_returns = [t['next_return'] for t in non_neutral]
    avg_return = sum(directional_returns) / len(directional_returns) if directional_returns else 0
    std_return = (sum((r - avg_return)**2 for r in directional_returns) / len(directional_returns))**0.5 if directional_returns else 1
    sharpe = avg_return / std_return * (252**0.5) if std_return > 0 else 0

    # Max Drawdown
    portfolio = 100000
    peak = portfolio
    max_dd = 0
    for t in trades:
        portfolio *= (1 + t['next_return'] / 100)
        if portfolio > peak:
            peak = portfolio
        dd = (peak - portfolio) / peak * 100
        max_dd = max(max_dd, dd)

    # CAGR
    if len(trades) > 0:
        start_date = datetime.strptime(trades[0]['date'], '%Y-%m-%d')
        end_date = datetime.strptime(trades[-1]['date'], '%Y-%m-%d')
        years = (end_date - start_date).days / 365.25
        end_value = portfolio
        cagr = ((end_value / 100000) ** (1/years) - 1) * 100 if years > 0 else 0
    else:
        years = 0
        cagr = 0

    # Breakdown by bias type
    by_bias = defaultdict(list)
    for t in trades:
        by_bias[t['bias']].append(t)

    bias_accuracy = {}
    for bias, ts in by_bias.items():
        correct_count = sum(1 for t in ts if t['correct'])
        bias_accuracy[bias] = {
            "count": len(ts),
            "correct": correct_count,
            "accuracy": correct_count / len(ts) * 100 if len(ts) > 0 else 0
        }

    results = {
        "strategy": strategy_name,
        "strategy_name": strategy_cls.name if hasattr(strategy_cls, 'name') else strategy_name,
        "period": f"{trades[0]['date']} → {trades[-1]['date']}" if trades else "N/A",
        "trading_days": total,
        "metrics": {
            "win_rate": round(win_rate, 1),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "cagr_pct": round(cagr, 2),
            "total_trades": total,
            "directional_trades": len(non_neutral),
            "neutral_trades": len(neutral_trades),
            "avg_return_pct": round(avg_return, 3),
            "std_return_pct": round(std_return, 3),
        },
        "bias_accuracy": bias_accuracy,
        "trades": trades,
    }

    print(f"\n📊 RESULTS:")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Sharpe:   {sharpe:.2f}")
    print(f"   Max DD:   {max_dd:.2f}%")
    print(f"   CAGR:     {cagr:.2f}%")
    print(f"   Trades:   {total} ({len(non_neutral)} directional)")

    return results


# ── Output Formatter ──────────────────────────────────────────────────────

def format_markdown(results):
    """Format backtest results as Obsidian-compatible markdown."""
    if results is None:
        return "# Backtest: Failed\nNo results to report."

    m = results['metrics']
    date_str = datetime.now().strftime('%Y-%m-%d')
    period_short = results['period'].split('→')[0].strip()[:10] if results['period'] != 'N/A' else 'unknown'

    md = f"""---
tags: [backtest, {results['strategy']}]
date: {date_str}
instrument: Nifty
period: "{results['period']}"
winrate: {m['win_rate']}
sharpe: {m['sharpe_ratio']}
maxdd: {m['max_drawdown_pct']}
cagr: {m['cagr_pct']}
---

# Backtest: {results['strategy_name']}

**Run by**: nse-trading-researcher agent  
**Date**: {date_str}  
**Instrument**: Nifty 50  
**Period**: {results['period']}  
**Trading Days**: {results['trading_days']}

---

## Results Summary

| Metric | Value |
|--------|-------|
| **Win Rate** | {m['win_rate']}% |
| **Sharpe Ratio** | {m['sharpe_ratio']} |
| **Max Drawdown** | -{m['max_drawdown_pct']}% |
| **CAGR** | {m['cagr_pct']}% |
| **Total Trades** | {m['total_trades']} |
| **Directional Trades** | {m['directional_trades']} |
| **Neutral Calls** | {m['neutral_trades']} |
| **Avg Return/Trade** | {m['avg_return_pct']}% |

## Accuracy by Bias Type

| Bias | Count | Correct | Accuracy |
|------|-------|---------|----------|
"""
    for bias, stats in results['bias_accuracy'].items():
        md += f"| {bias} | {stats['count']} | {stats['correct']} | {stats['accuracy']:.1f}% |\n"

    md += """
## Equity Curve

```
```
*(Mermaid chart will be generated in a future version)*

## Notes

- Backtest uses daily EOD data from yfinance
- No slippage/commission included
- Comparison benchmark: Buy & Hold Nifty
- See [[07-Reference/backtest-methodology]] for methodology

## Related
- [[01-Techniques/signal-engine-8-factor|Signal Engine Details]]
- [[03-Factors]] — Factor analysis
"""
    return md


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='NSE Backtesting Engine')
    parser.add_argument('--strategy', help='Strategy name to backtest')
    parser.add_argument('--period', default='3y', help='Backtest period (e.g., 1y, 3y, 5y)')
    parser.add_argument('--output', default='json', choices=['json', 'md', 'both'],
                        help='Output format')
    parser.add_argument('--list-strategies', action='store_true',
                        help='List available strategies')
    parser.add_argument('--save', action='store_true',
                        help='Save results to Obsidian vault')

    args = parser.parse_args()

    if args.list_strategies:
        print("Available Strategies:")
        for name, info in STRATEGIES.items():
            print(f"  {name}: {info['description']}")
        return

    if not args.strategy:
        parser.print_help()
        return

    # Parse period
    period_map = {'1y': 1, '2y': 2, '3y': 3, '5y': 5}
    period_years = period_map.get(args.period, 3)

    results = run_backtest(args.strategy, period_years)

    if results is None:
        return

    if args.output in ('json', 'both'):
        print(json.dumps(results, indent=2))

    if args.output in ('md', 'both'):
        md = format_markdown(results)
        print(f"\n{'='*60}")
        print("MARKDOWN REPORT:")
        print(f"{'='*60}")
        print(md)

    # Save to vault
    if args.save:
        md = format_markdown(results)
        safe_name = results['strategy'].replace(' ', '-').lower()
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}-{safe_name}.md"
        filepath = os.path.join(RESEARCH_DIR, "02-Backtests", filename)
        with open(filepath, 'w') as f:
            f.write(md)
        print(f"💾 Saved to: {filepath}")


if __name__ == '__main__':
    main()
