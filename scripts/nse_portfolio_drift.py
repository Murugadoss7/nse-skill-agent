#!/usr/bin/env python3
"""
NSE Portfolio Drift Monitor
Checks actual portfolio allocation vs target allocation.
Adapted from Claude Routines "Portfolio Drift Monitor" for NSE portfolio.

Usage:
  python3 nse_portfolio_drift.py              # Full scan + report
  python3 nse_portfolio_drift.py --preview    # Preview only
  python3 nse_portfolio_drift.py --telegram   # Telegram format output

Mode: no_agent (stdout is the report)
"""

import json
import os
import sys
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
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TIMEZONE = ZoneInfo("Asia/Kolkata")
TODAY = date.today()
TODAY_STR = TODAY.isoformat()

DRIFT_THRESHOLD = 5.0  # % deviation before flagging

# ── Target Allocation (sector-level) ────────────────────────────────────
# Set your target allocation by sector.
# These are opinionated defaults — adjust to your actual strategy.
TARGET_ALLOCATION = {
    "Banking": 15.0,        # 15% in banking stocks
    "IT": 10.0,             # 10% in IT
    "Energy": 8.0,          # 8% in energy
    "Pharma": 8.0,          # 8% in pharma
    "Auto": 6.0,            # 6% in auto
    "Consumer": 6.0,        # 6% in consumer staples
    "Financials": 6.0,      # 6% in financials (NBFCs, insurance)
    "Capital Goods": 6.0,   # 6% in capital goods
    "Telecom": 4.0,         # 4% in telecom
    "Materials": 4.0,       # 4% in materials (cement, metals)
    "Metals": 6.0,          # 6% in metals & mining
    "Infrastructure": 5.0,  # 5% in infra (construction, railways)
    "FMCG": 5.0,            # 5% in FMCG
    "PSU Banks": 5.0,       # 5% in PSU banks
    "Chemicals": 3.0,       # 3% in chemicals
    "Power": 4.0,           # 4% in power utilities
    "Realty": 2.0,          # 2% in real estate
    "Media": 1.0,           # 1% in media
    "ETF/Hybrid": 2.0,      # 2% in ETFs
    "Cash": 0.0,            # Cash (not tracked)
}

# Sector mapping for portfolio stocks
SECTOR_MAP = {
    "ADVENZYMES": "Pharma", "AFCONS": "Infrastructure", "AWL": "FMCG",
    "BAJAJHFL": "Financials", "BANDHANBNK": "Banking", "BAYERCROP": "Chemicals",
    "CAMPUS": "Consumer", "CDSL": "Financials", "CENTRALBK": "PSU Banks",
    "CESC": "Power", "COLPAL": "Consumer", "CONCOR": "Infrastructure",
    "EXPLEOSOL": "IT", "FIEMIND": "Auto", "FLUOROCHEM": "Chemicals",
    "FMCGIETF": "ETF/Hybrid", "GMDCLTD": "Metals", "HAVELLS": "Capital Goods",
    "HDFCAMC": "Financials", "HINDALCO": "Metals", "HINDCOPPER": "Metals",
    "HINDUNILVR": "FMCG", "IDFCFIRSTB": "Banking", "INDIGO": "Infrastructure",
    "INTERNET": "ETF/Hybrid", "IOB": "PSU Banks", "IRCTC": "Infrastructure",
    "IRFC": "Infrastructure", "J&KBANK": "PSU Banks", "JIOFIN": "Financials",
    "KNRCON": "Infrastructure", "M&M": "Auto", "MTNL": "Telecom",
    "NHPC": "Power", "ONGC": "Energy", "PETRONET": "Energy",
    "PGHH": "Consumer", "PNB": "PSU Banks", "RECLTD": "Financials",
    "ROSSARI": "Chemicals", "RVNL": "Infrastructure", "SBIN": "PSU Banks",
    "SILVERBEES": "ETF/Hybrid", "THERMAX": "Capital Goods", "UNIONBANK": "PSU Banks",
    "UNITDSPR": "Consumer", "VEDL": "Metals", "WHIRLPOOL": "Consumer",
}


def load_service():
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


def fetch_current_prices(symbols):
    """Fetch current market prices for all symbols via yfinance."""
    # Batch fetch for efficiency
    tickers_str = " ".join(f"{s}.NS" for s in symbols)
    try:
        data = yf.download(tickers_str, period="1d", progress=False)
        prices = {}
        for s in symbols:
            try:
                prices[s] = float(data["Close"][s + ".NS"].iloc[-1])
            except (KeyError, IndexError, TypeError):
                prices[s] = None
        return prices
    except Exception:
        # Fallback: fetch individually
        prices = {}
        for s in symbols:
            try:
                t = yf.Ticker(f"{s}.NS")
                hist = t.history(period="1d")
                if not hist.empty:
                    prices[s] = float(hist["Close"].iloc[-1])
                else:
                    prices[s] = None
            except Exception:
                prices[s] = None
        return prices


def compute_portfolio_allocation(portfolio, prices):
    """
    Compute portfolio allocation by stock and by sector.
    portfolio: list of (symbol, qty) tuples
    prices: dict of symbol -> current price
    """
    # Compute total value
    positions = []
    total_value = 0
    for symbol, qty in portfolio:
        price = prices.get(symbol)
        if price is None or qty is None:
            continue
        value = price * qty
        total_value += value
        sector = SECTOR_MAP.get(symbol, "Other")
        positions.append({
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "value": value,
            "sector": sector,
        })

    if total_value == 0:
        return [], {}, total_value

    # Per stock allocation
    for p in positions:
        p["allocation_pct"] = (p["value"] / total_value) * 100

    # Per sector allocation
    sector_values = {}
    for p in positions:
        sector = p["sector"]
        sector_values[sector] = sector_values.get(sector, 0) + p["value"]

    sector_allocation = {}
    for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
        sector_allocation[sector] = (value / total_value) * 100

    return positions, sector_allocation, total_value


def analyze_drift(actual_pct, sector):
    """Analyze drift for a sector."""
    target = TARGET_ALLOCATION.get(sector, 0)
    if target == 0 and actual_pct == 0:
        return None
    drift = actual_pct - target
    drift_pct = (drift / target * 100) if target > 0 else float("inf")
    return {
        "sector": sector,
        "target": target,
        "actual": actual_pct,
        "drift": drift,
        "drift_pct": drift_pct,
        "flagged": abs(drift) > DRIFT_THRESHOLD,
    }


def run():
    preview = "--preview" in sys.argv
    telegram_mode = "--telegram" in sys.argv

    print(f"╔══ NSE Portfolio Drift Monitor ═══╗")
    print(f"║  Date: {TODAY_STR} (IST)")
    print(f"║  Mode: {'PREVIEW' if preview else 'LIVE'}{' + TELEGRAM' if telegram_mode else ''}")
    print(f"╠{'═'*35}╣")
    print(f"║  Drift threshold: {DRIFT_THRESHOLD}%")
    print(f"║  Target: Sector-level allocation")
    print(f"╚{'═'*35}╝")
    print()

    # Read portfolio from sheet
    service = load_service()
    rows = get_values(service, "Portfolio!A:N")
    if len(rows) <= 1:
        print("ERROR: No portfolio data found in sheet")
        return

    header = rows[0]
    # Find column indices
    sym_idx = 0  # A
    qty_idx = 4  # E (Qty)
    entry_idx = 2  # C (Entry Price)

    # Build portfolio
    portfolio = []
    for row in rows[1:]:
        sym = row[sym_idx].strip().upper() if len(row) > sym_idx and row[sym_idx].strip() else ""
        qty_str = row[qty_idx].strip() if len(row) > qty_idx and row[qty_idx].strip() else "0"
        try:
            qty = float(qty_str.replace(",", ""))
        except (ValueError, AttributeError):
            qty = 0
        if sym and qty > 0:
            portfolio.append((sym, qty))

    print(f"Portfolio: {len(portfolio)} positions")
    print()

    # Fetch current prices
    symbols = [p[0] for p in portfolio]
    print("Fetching current prices...")
    prices = fetch_current_prices(symbols)
    found = sum(1 for s in symbols if prices.get(s) is not None)
    print(f"  Got prices for {found}/{len(symbols)} stocks")
    print()

    # Compute allocation
    positions, sector_allocation, total_value = compute_portfolio_allocation(portfolio, prices)
    print(f"Total Portfolio Value: ₹{total_value:,.2f}")
    print()

    # Per-stock breakdown (top 10 by value)
    print("── Top Holdings ──")
    print(f"{'Symbol':<14} {'Sector':<16} {'Qty':<8} {'Price':<10} {'Value':<14} {'%':<8}")
    print("-" * 70)
    sorted_positions = sorted(positions, key=lambda p: p["value"], reverse=True)
    for p in sorted_positions[:10]:
        print(f"{p['symbol']:<14} {p['sector']:<16} {p['qty']:<8.0f} ₹{p['price']:<8.2f} ₹{p['value']:<10,.0f} {p['allocation_pct']:<7.2f}%")
    if len(sorted_positions) > 10:
        print(f"  ... and {len(sorted_positions)-10} more positions")

    # Sector allocation vs target
    print()
    print("── Sector Allocation vs Target ──")
    print(f"{'Sector':<18} {'Target':<8} {'Actual':<8} {'Drift':<8} {'Flag':<6}")
    print("-" * 50)

    all_sectors = set(list(TARGET_ALLOCATION.keys()) + list(sector_allocation.keys()))
    drift_results = []
    for sector in sorted(all_sectors):
        actual = sector_allocation.get(sector, 0)
        result = analyze_drift(actual, sector)
        if result is None:
            continue
        drift_results.append(result)
        flag = "⚠️" if result["flagged"] else "✓"
        arrow = "↑" if result["drift"] > 0 else "↓"
        print(f"{result['sector']:<18} {result['target']:<7.1f}% {result['actual']:<7.1f}% {arrow}{abs(result['drift']):<6.1f}% {flag:<6}")

    # Flagged sectors
    flagged = [r for r in drift_results if r["flagged"]]
    if flagged:
        print()
        print("── ⚠️  Drift Alerts ──")
        for r in flagged:
            direction = "overweight" if r["drift"] > 0 else "underweight"
            urgency = "HIGH" if abs(r["drift"]) > 10 else "MODERATE"
            print(f"  {r['sector']}: {direction} by {abs(r['drift']):.1f}% (target: {r['target']:.1f}%, actual: {r['actual']:.1f}%) [{urgency}]")
    else:
        print()
        print("✅ No significant drift detected")

    # Summary
    print()
    print("── Summary ──")
    print(f"  Total Value:  ₹{total_value:,.2f}")
    print(f"  Positions:    {len(positions)}")
    print(f"  Sectors:      {len(sector_allocation)}")
    print(f"  Drift Alerts: {len(flagged)}")
    print()

    # Telegram format
    if telegram_mode:
        print("══════ TELEGRAM REPORT ══════")
        print(f"📊 Portfolio Drift — {TODAY_STR}")
        print(f"💰 Total: ₹{total_value:,.0f} | {len(positions)} positions")
        print()
        if flagged:
            print("⚠️ Drift Alerts:")
            for r in flagged:
                direction = "↑ Overweight" if r["drift"] > 0 else "↓ Underweight"
                icon = "🔴" if abs(r["drift"]) > 10 else "🟡"
                print(f"  {icon} {r['sector']}: target {r['target']:.0f}%, actual {r['actual']:.0f}% ({direction} {abs(r['drift']):.0f}%)")
        else:
            print("✅ All sectors within drift threshold")
        print()
        # Show top 5
        print("Top Holdings:")
        for p in sorted_positions[:5]:
            print(f"  • {p['symbol']}: ₹{p['value']:,.0f} ({p['allocation_pct']:.1f}%)")
        print("══════════════════════════════")

    print("Done.")


if __name__ == "__main__":
    run()
