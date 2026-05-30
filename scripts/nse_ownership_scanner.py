#!/usr/bin/env python3
"""
NSE Ownership Signals Scanner
Fetches insider transaction data from yfinance for portfolio stocks,
analyzes them, and writes signals to the Google Sheet's Ownership Signals tab.

Usage:
  python3 nse_ownership_scanner.py            # Full scan, write results
  python3 nse_ownership_scanner.py --preview  # Preview only, no write
  python3 nse_ownership_scanner.py --force    # Force overwrite existing signals

Mode: no_agent (stdout is the report, sheet write is the side effect)
"""

import json
import os
import sys
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo

import yfinance as yf
import pandas as pd
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ──────────────────────────────────────────────────────────────
SHEET_ID = "1J2OpZyiiGnDMlXJgExR1HgnJmyIH2HjIC5siHoGFbZ4"
TOKEN_PATH = os.path.expanduser("~/.hermes/google_token.json")
CLIENT_SECRET = os.path.expanduser("~/.hermes/google_client_secret.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TIMEZONE = ZoneInfo("Asia/Kolkata")
TODAY = date.today()
TODAY_STR = TODAY.isoformat()

# Scoring thresholds
VOLUME_SPIKE_THRESHOLD = 2.0  # 2x average volume = notable
INSIDER_WINDOW_DAYS = 90      # Look at last 90 days for insider activity
BULK_DEAL_THRESHOLD = 10000000  # ₹1Cr+ for significant insider transactions
STRONG_PURCHASE_PCT = 0.001   # 0.1% of shares bought by insiders = strong signal

# ── Helpers ─────────────────────────────────────────────────────────────

def load_service():
    """Get authenticated Google Sheets service."""
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("sheets", "v4", credentials=creds)


def get_values(service, rng):
    return service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=rng
    ).execute().get("values", [])


def put_values(service, rng, values):
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=rng,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def clear_range(service, rng):
    service.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID, range=rng
    ).execute()


def fmt(x, digits=2):
    if x is None:
        return ""
    return f"{x:.{digits}f}"


def parse_float(v, default=None):
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except (ValueError, TypeError, AttributeError):
        return default


def get_portfolio_symbols(service):
    """Read stock symbols from Portfolio tab."""
    rows = get_values(service, "Portfolio!A:A")
    symbols = []
    for row in rows[1:]:  # skip header
        sym = row[0].strip().upper() if row and row[0].strip() else ""
        if sym:
            symbols.append(sym)
    return symbols


def get_existing_signals(service):
    """Read existing ownership signals to avoid duplicates."""
    rows = get_values(service, "'Ownership Signals'!A:H")
    if len(rows) <= 1:
        return []
    return rows[1:]  # Skip header


def fetch_insider_data(symbol):
    """Fetch insider transaction data from yfinance for an NSE stock."""
    ticker = yf.Ticker(f"{symbol}.NS")
    data = {}

    # Insider transactions
    try:
        it = ticker.insider_transactions
        if it is not None and not it.empty:
            it["Start Date"] = pd.to_datetime(it["Start Date"], errors="coerce")
            recent = it[it["Start Date"] >= pd.Timestamp.now() - pd.Timedelta(days=INSIDER_WINDOW_DAYS)]
            data["insider_transactions"] = recent.to_dict("records") if not recent.empty else []
        else:
            data["insider_transactions"] = []
    except Exception as e:
        data["insider_transactions"] = []
        data["error"] = str(e)

    # Insider purchases summary
    try:
        ip = ticker.insider_purchases
        if ip is not None and not ip.empty:
            data["insider_purchases"] = ip.to_dict()
    except Exception:
        data["insider_purchases"] = {}

    # Major holders
    try:
        mh = ticker.major_holders
        if mh is not None and not mh.empty:
            data["major_holders"] = mh.to_dict()
    except Exception:
        data["major_holders"] = {}

    return data


def fetch_volume_data(symbol):
    """Fetch recent volume data to detect anomalies."""
    ticker = yf.Ticker(f"{symbol}.NS")
    try:
        hist = ticker.history(period="1mo", interval="1d")
        if hist.empty:
            return None
        avg_vol = hist["Volume"].mean()
        latest_vol = hist["Volume"].iloc[-1]
        latest_close = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else latest_close
        price_change_pct = ((latest_close - prev_close) / prev_close) * 100
        vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 1.0
        return {
            "vol_ratio": vol_ratio,
            "avg_vol": int(avg_vol),
            "latest_vol": int(latest_vol),
            "latest_close": float(latest_close),
            "price_change_pct": float(price_change_pct),
        }
    except Exception:
        return None


def analyze_insider_activity(symbol, data):
    """
    Analyze insider transactions and return a signal.
    Returns (direction, strength, confidence, note) or None.
    """
    transactions = data.get("insider_transactions", [])
    if not transactions:
        return None

    # Count purchases vs sales in recent window
    purchases = [t for t in transactions if "acquis" in str(t.get("Text", "")).lower()]
    sales = [t for t in transactions if "sale" in str(t.get("Text", "")).lower()]

    if not purchases and not sales:
        return None

    # Calculate total values
    total_purchase_value = sum(parse_float(t.get("Value", 0), 0) for t in purchases)
    total_sale_value = sum(parse_float(t.get("Value", 0), 0) for t in sales)

    # Check for promoter transactions (higher significance)
    promoter_purchases = [t for t in purchases if "promoter" in str(t.get("Position", "")).lower()]
    promoter_sales = [t for t in sales if "promoter" in str(t.get("Position", "")).lower()]

    net_value = total_purchase_value - total_sale_value

    # Determine direction
    if net_value > BULK_DEAL_THRESHOLD and len(purchases) >= len(sales):
        direction = "positive"
        strength = "strong" if net_value > BULK_DEAL_THRESHOLD * 5 else "medium"
        confidence = "high" if promoter_purchases else "medium"
    elif net_value > 0:
        direction = "positive"
        strength = "weak"
        confidence = "medium"
    elif net_value < -BULK_DEAL_THRESHOLD:
        direction = "negative"
        strength = "strong" if abs(net_value) > BULK_DEAL_THRESHOLD * 5 else "medium"
        confidence = "high" if promoter_sales else "medium"
    elif net_value < 0:
        direction = "negative"
        strength = "weak"
        confidence = "medium"
    else:
        direction = "neutral"
        strength = "weak"
        confidence = "low"

    # Build note
    parts = []
    if purchases:
        parts.append(f"{len(purchases)} purchase(s) totalling ₹{total_purchase_value:,.0f}")
    if sales:
        parts.append(f"{len(sales)} sale(s) totalling ₹{total_sale_value:,.0f}")
    if promoter_purchases:
        parts.append("Promoter buying detected!")
    if promoter_sales:
        parts.append("Promoter selling detected!")

    note = " | ".join(parts)
    return direction, strength, confidence, note


def analyze_volume_anomaly(symbol, vol_data):
    """Analyze volume data for anomaly signals."""
    if vol_data is None:
        return None
    vr = vol_data["vol_ratio"]
    if vr >= VOLUME_SPIKE_THRESHOLD and vol_data["price_change_pct"] > 0:
        return (
            "positive",
            "medium" if vr >= 3 else "weak",
            "medium",
            f"Volume spike {vr:.1f}x avg ({vol_data['price_change_pct']:+.2f}% price up)",
        )
    if vr >= VOLUME_SPIKE_THRESHOLD and vol_data["price_change_pct"] < 0:
        return (
            "negative",
            "medium" if vr >= 3 else "weak",
            "medium",
            f"Volume spike {vr:.1f}x avg ({vol_data['price_change_pct']:+.2f}% price down)",
        )
    return None


def merge_signals(symbol, insider_signal, volume_signal, existing_rows):
    """
    Merge multiple signals for one symbol into a single ownership signal entry.
    """
    existing = [r for r in existing_rows if len(r) > 1 and r[1].strip().upper() == symbol]

    if insider_signal:
        direction, strength, confidence, note = insider_signal
        source = "yfinance-insider"
        return [TODAY_STR, symbol, direction, strength, confidence, source, note, "Yes"]

    if volume_signal:
        direction, strength, confidence, note = volume_signal
        source = "yfinance-volume"
        return [TODAY_STR, symbol, direction, strength, confidence, source, note, "Yes"]

    # No new signal but check if there's an existing one to keep
    if existing:
        return None  # Keep existing

    # No signal at all for this symbol
    return None


def ensure_headers(service):
    """Ensure Ownership Signals tab has correct headers."""
    existing = get_values(service, "'Ownership Signals'!A1:H2")
    expected = ["Date", "Symbol", "Direction", "Strength", "Confidence", "Source", "Note", "Active"]
    if existing and existing[0] == expected:
        return
    # Write headers
    put_values(service, "'Ownership Signals'!A1:H1", [expected])


def clear_old_signals(service, symbols):
    """Remove old automatic signals (from yfinance), keep manual ones."""
    existing = get_values(service, "'Ownership Signals'!A1:H1000")
    if len(existing) <= 1:
        return existing
    header = existing[0]
    rows = existing[1:]
    keep = []
    for row in rows:
        source = (row[5] if len(row) > 5 else "").strip() if len(row) > 5 else ""
        symbol = (row[1] if len(row) > 1 else "").strip().upper() if len(row) > 1 else ""
        if source.startswith("yfinance"):
            continue  # Remove auto-generated signals, will regenerate
        keep.append(row)
    # Rewrite header + kept rows
    put_values(service, "'Ownership Signals'!A1:H1000", [header] + keep)
    return [header] + keep


def run():
    preview = "--preview" in sys.argv
    force = "--force" in sys.argv

    print(f"╔══ NSE Ownership Signals Scanner ═╗")
    print(f"║  Date: {TODAY_STR} (IST)")
    print(f"║  Mode: {'PREVIEW' if preview else 'LIVE'}")
    print(f"╚{'═'*35}╝")
    print()

    # Init
    service = load_service()
    ensure_headers(service)

    # Get portfolio
    symbols = get_portfolio_symbols(service)
    print(f"Portfolio: {len(symbols)} stocks")
    print()

    # Clear old auto-generated signals (keep manual ones)
    existing_rows = clear_old_signals(service, symbols) if not preview else get_values(service, "'Ownership Signals'!A:H")
    if preview:
        # Just read existing for preview
        pass

    print(f"{'Symbol':<14} {'Insider':<10} {'Volume':<10} {'Signal':<12} {'Note'}")
    print("-" * 80)

    new_signals = []
    stats = {"scanned": 0, "insider_activity": 0, "volume_anomaly": 0, "signals_generated": 0}

    for i, symbol in enumerate(symbols):
        stats["scanned"] += 1
        sys.stdout.write(f"\r  [{i+1}/{len(symbols)}] {symbol:<12} ")
        sys.stdout.flush()

        # Fetch data
        vol_data = fetch_volume_data(symbol)
        time.sleep(0.5)  # Rate limit

        insider_data = fetch_insider_data(symbol)
        time.sleep(0.5)  # Rate limit

        # Analyze
        insider_signal = analyze_insider_activity(symbol, insider_data) if insider_data.get("insider_transactions") else None
        volume_signal = analyze_volume_anomaly(symbol, vol_data)

        if insider_signal:
            stats["insider_activity"] += 1

        if volume_signal:
            stats["volume_anomaly"] += 1

        # Merge
        row = merge_signals(symbol, insider_signal, volume_signal, existing_rows)
        if row:
            new_signals.append(row)
            stats["signals_generated"] += 1
            sig_dir = row[2]
            sig_str = row[3]
            note = row[6][:40]
            print(f"\r  {'✓':<1} {symbol:<12} {'INSIDER' if insider_signal else '':<10} {'VOLUME' if volume_signal else '':<10} {sig_dir:<8}/{sig_str:<8} {note:<40}")
        else:
            print(f"\r  {'-':<1} {symbol:<12} {'-':<10} {'-':<10} {'no signal':<12}")

    print()
    print(f"╔══ Results ═══════════════════════╗")
    print(f"║  Scanned:          {stats['scanned']:>4}")
    print(f"║  Insider activity: {stats['insider_activity']:>4}")
    print(f"║  Volume anomalies: {stats['volume_anomaly']:>4}")
    print(f"║  Signals written:  {stats['signals_generated']:>4}")
    print(f"╚{'═'*35}╝")

    if new_signals and not preview:
        # Write new signals below existing (manual) rows
        existing = get_values(service, "'Ownership Signals'!A:H")
        existing_data = existing[1:] if len(existing) > 1 else []
        # Append new signals
        all_data = existing_data + new_signals
        put_values(service, "'Ownership Signals'!A1:H10000", [["Date", "Symbol", "Direction", "Strength", "Confidence", "Source", "Note", "Active"]] + all_data)
        print(f"\n✓ Wrote {len(new_signals)} signal(s) to Ownership Signals tab")

    print()
    print("Done.")


if __name__ == "__main__":
    run()
