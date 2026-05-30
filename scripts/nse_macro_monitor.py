#!/usr/bin/env python3
"""
NSE Macro Event Monitor
Tracks key Indian economic indicators and market macro context.
Adapted from Claude Routines "Macro Data Processor" for Indian markets.

Data sources:
  - yfinance: Nifty, Bank Nifty, USD/INR, India VIX, Brent Crude
  - Historical comparison for trend analysis

Usage:
  python3 nse_macro_monitor.py              # Full scan, write to sheet + report
  python3 nse_macro_monitor.py --preview    # Preview only
  python3 nse_macro_monitor.py --telegram   # Format output for Telegram delivery

Mode: no_agent (stdout is the report)
"""

import json
import os
import sys
from datetime import datetime, date, timedelta
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

# Macro indicators to track
MACRO_INDICATORS = [
    {
        "name": "Nifty 50",
        "ticker": "^NSEI",
        "category": "Equity",
        "interpretation": "higher_is_better",
    },
    {
        "name": "Bank Nifty",
        "ticker": "^NSEBANK",
        "category": "Equity",
        "interpretation": "higher_is_better",
    },
    {
        "name": "India VIX",
        "ticker": "^INDIAVIX",
        "category": "Volatility",
        "interpretation": "lower_is_better",
    },
    {
        "name": "USD/INR",
        "ticker": "USDINR=X",
        "category": "Currency",
        "interpretation": "lower_is_better",
    },
    {
        "name": "Brent Crude",
        "ticker": "BZ=F",
        "category": "Commodity",
        "interpretation": "lower_is_better",
    },
    {
        "name": "Nifty IT",
        "ticker": "^CNXIT",
        "category": "Sector",
        "interpretation": "higher_is_better",
    },
    {
        "name": "Nifty Pharma",
        "ticker": "^CNXPHARMA",
        "category": "Sector",
        "interpretation": "higher_is_better",
    },
    {
        "name": "Nifty Auto",
        "ticker": "^CNXAUTO",
        "category": "Sector",
        "interpretation": "higher_is_better",
    },
    {
        "name": "Nifty FMCG",
        "ticker": "^CNXFMCG",
        "category": "Sector",
        "interpretation": "higher_is_better",
    },
    {
        "name": "Nifty Energy",
        "ticker": "^CNXENERGY",
        "category": "Sector",
        "interpretation": "higher_is_better",
    },
]

# Macro event reminders (static calendar — update quarterly)
MACRO_EVENTS = [
    # RBI Monetary Policy (6 per year, ~first week of each month in a cycle)
    {"event": "RBI Monetary Policy", "upcoming": "2026-06-03", "severity": "high"},
    {"event": "RBI Monetary Policy", "upcoming": "2026-08-05", "severity": "high"},
    {"event": "RBI Monetary Policy", "upcoming": "2026-10-07", "severity": "high"},
    {"event": "RBI Monetary Policy", "upcoming": "2026-12-02", "severity": "high"},
    # India CPI (monthly, ~12th of month)
    {"event": "India CPI Inflation", "upcoming": "2026-06-12", "severity": "medium"},
    # India IIP (monthly, ~12th of month)
    {"event": "India IIP Data", "upcoming": "2026-06-12", "severity": "medium"},
    # US Fed (impacts INR)
    {"event": "US FOMC Decision", "upcoming": "2026-06-17", "severity": "high"},
    {"event": "US FOMC Decision", "upcoming": "2026-07-29", "severity": "high"},
    {"event": "US FOMC Decision", "upcoming": "2026-09-16", "severity": "high"},
]

MARKET_PULSE_HEADERS = [
    "Date", "Scope", "Symbol/Index", "Category", "Trend", "Current", "1W %", "1M %", "3M %", "Note"
]


# ── Helpers ─────────────────────────────────────────────────────────────

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


def put_values(service, rng, values):
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=rng,
        valueInputOption="RAW", body={"values": values},
    ).execute()


def clear_range(service, rng):
    service.spreadsheets().values().clear(spreadsheetId=SHEET_ID, range=rng).execute()


def fmt(x, digits=2):
    if x is None:
        return ""
    return f"{x:.{digits}f}"


def get_trend(change_pct, interpretation):
    """Classify trend as bullish/bearish/neutral based on change and interpretation."""
    if interpretation == "higher_is_better":
        if change_pct > 3:
            return "strong bullish"
        elif change_pct > 0.5:
            return "bullish"
        elif change_pct > -0.5:
            return "neutral"
        elif change_pct > -3:
            return "bearish"
        else:
            return "strong bearish"
    else:  # lower_is_better
        if change_pct < -3:
            return "strong bullish"
        elif change_pct < -0.5:
            return "bullish"
        elif change_pct < 0.5:
            return "neutral"
        elif change_pct < 3:
            return "bearish"
        else:
            return "strong bearish"


def fetch_indicator(indicator):
    """Fetch yfinance data for a macro indicator and compute returns."""
    ticker = yf.Ticker(indicator["ticker"])
    try:
        hist = ticker.history(period="3mo", interval="1d")
        if hist.empty:
            return None

        close = hist["Close"]
        current = float(close.iloc[-1])

        # Compute returns over different periods
        ret_1w = ((current / float(close.iloc[-6])) - 1) * 100 if len(close) >= 6 else 0
        ret_1m = ((current / float(close.iloc[-22])) - 1) * 100 if len(close) >= 22 else 0
        ret_3m = ((current / float(close.iloc[-66])) - 1) * 100 if len(close) >= 66 else 0

        # 20D SMA for trend context
        sma20 = float(close.tail(20).mean()) if len(close) >= 20 else current
        above_sma = "above" if current > sma20 else "below"

        trend = get_trend(ret_1m, indicator["interpretation"])
        note = f"{above_sma} 20DMA | 1M: {ret_1m:+.1f}%"

        return {
            "current": current,
            "ret_1w": ret_1w,
            "ret_1m": ret_1m,
            "ret_3m": ret_3m,
            "trend": trend,
            "note": note,
            "sma20": sma20,
        }
    except Exception as e:
        return None


def check_upcoming_events():
    """Check which macro events are upcoming in the next 14 days."""
    events_near = []
    for ev in MACRO_EVENTS:
        try:
            ev_date = datetime.strptime(ev["upcoming"], "%Y-%m-%d").date()
            days_until = (ev_date - TODAY).days
            if 0 <= days_until <= 14:
                events_near.append((days_until, ev))
        except ValueError:
            continue
    return sorted(events_near, key=lambda x: x[0])


def assess_market_risk(indicators_data):
    """Assess overall market risk based on indicator readings."""
    risk_score = 0
    factors = []

    # VIX > 20 = high fear
    vix_data = indicators_data.get("^INDIAVIX")
    if vix_data and vix_data["current"] > 25:
        risk_score += 2
        factors.append(f"VIX at {vix_data['current']:.1f} (elevated fear)")
    elif vix_data and vix_data["current"] > 20:
        risk_score += 1
        factors.append(f"VIX at {vix_data['current']:.1f} (moderate fear)")

    # USD/INR weakening
    inr_data = indicators_data.get("USDINR=X")
    if inr_data and inr_data["ret_1m"] > 2:
        risk_score += 1
        factors.append(f"Rupee weakening {inr_data['ret_1m']:+.1f}% in 1M")

    # Crude oil spike
    crude_data = indicators_data.get("BZ=F")
    if crude_data and crude_data["ret_1m"] > 5:
        risk_score += 1
        factors.append(f"Crude up {crude_data['ret_1m']:+.1f}% in 1M (bad for India)")

    # Nifty down trend
    nifty_data = indicators_data.get("^NSEI")
    if nifty_data and nifty_data["ret_1m"] < -3:
        risk_score += 1
        factors.append(f"Nifty down {nifty_data['ret_1m']:+.1f}% in 1M")

    if risk_score >= 3:
        level = "HIGH"
    elif risk_score >= 1:
        level = "MODERATE"
    else:
        level = "LOW"

    return level, risk_score, factors


def run():
    preview = "--preview" in sys.argv
    telegram_mode = "--telegram" in sys.argv

    print(f"╔══ NSE Macro Event Monitor ═══════╗")
    print(f"║  Date: {TODAY_STR} (IST)")
    print(f"║  Mode: {'PREVIEW' if preview else 'LIVE'}{' + TELEGRAM' if telegram_mode else ''}")
    print(f"╚{'═'*32}╝")
    print()

    # Fetch all indicators
    indicators_data = {}
    pulse_rows = [MARKET_PULSE_HEADERS]

    print(f"{'Indicator':<18} {'Current':<12} {'1W %':<8} {'1M %':<8} {'3M %':<8} {'Trend':<16}")
    print("-" * 75)

    for ind in MACRO_INDICATORS:
        data = fetch_indicator(ind)
        if data:
            indicators_data[ind["ticker"]] = data
            pulse_rows.append([
                TODAY_STR, ind["category"], ind["ticker"], ind["name"],
                data["trend"], fmt(data["current"]),
                fmt(data["ret_1w"]), fmt(data["ret_1m"]), fmt(data["ret_3m"]),
                data["note"],
            ])
            sym = ind["name"]
            cur = fmt(data["current"])
            w1 = f"{data['ret_1w']:+.2f}%"
            m1 = f"{data['ret_1m']:+.2f}%"
            m3 = f"{data['ret_3m']:+.2f}%"
            trend = data["trend"]
            print(f"{sym:<18} {cur:<12} {w1:<8} {m1:<8} {m3:<8} {trend:<16}")
        else:
            print(f"{ind['name']:<18} {'NO DATA':<12}")

    # Check upcoming events
    print()
    print("── Upcoming Events (next 14 days) ──")
    events = check_upcoming_events()
    if events:
        for days, ev in events:
            marker = "⚠️" if ev["severity"] == "high" else "📅"
            print(f"  {marker} {ev['event']} — {ev['upcoming']} ({days}d away)")
    else:
        print("  No major events in next 14 days")

    # Market risk assessment
    print()
    print("── Market Risk Assessment ──")
    level, score, factors = assess_market_risk(indicators_data)
    risk_icon = {"HIGH": "🔴", "MODERATE": "🟡", "LOW": "🟢"}
    print(f"  {risk_icon.get(level, '⚪')} Risk Level: {level} (score: {score}/5)")
    for f in factors:
        print(f"    • {f}")
    if not factors:
        print("    No significant risk factors detected")

    # Write to sheet
    if not preview:
        service = load_service()
        # Clear existing pulse rows (keep header)
        clear_range(service, "'Market Pulse'!A2:J500")
        put_values(service, "'Market Pulse'!A1:J500", pulse_rows)
        print(f"\n✓ Wrote {len(pulse_rows)-1} indicator(s) to Market Pulse tab")

    # Telegram-formatted output
    if telegram_mode:
        print()
        print("══════ TELEGRAM REPORT ══════")
        level_icon = risk_icon.get(level, "⚪")
        print(f"{'📊'} NSE Macro Monitor — {TODAY_STR}")
        print(f"{level_icon} Risk: {level}")
        print()
        for ind in MACRO_INDICATORS:
            data = indicators_data.get(ind["ticker"])
            if data:
                icon = "🟢" if "bullish" in data["trend"] else "🔴" if "bearish" in data["trend"] else "⚪"
                print(f"{icon} {ind['name']}: {fmt(data['current'])} ({data['ret_1m']:+.1f}% 1M)")
        if events:
            print()
            print("📅 Upcoming Events:")
            for days, ev in events:
                print(f"  • {ev['event']} ({days}d)")
        print("══════════════════════════════")

    print()
    print("Done.")


if __name__ == "__main__":
    run()
