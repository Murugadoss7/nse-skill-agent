#!/usr/bin/env python3
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1J2OpZyiiGnDMlXJgExR1HgnJmyIH2HjIC5siHoGFbZ4"
HERMES_HOME = os.path.expanduser("~/.hermes")
TOKEN_PATH = os.path.join(HERMES_HOME, "google_token.json")
TIMEZONE = ZoneInfo("Asia/Kolkata")
TODAY = datetime.now(TIMEZONE).date()
TODAY_STR = TODAY.isoformat()
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]

PORTFOLIO_HEADERS = [
    "Symbol", "Entry Date", "Entry Price", "Stop Loss", "Qty", "Strategy Type", "Sector",
    "Initial Reason", "Current Status", "Last Close", "P/L %", "Last Review Date", "Decision",
    "Decision Note", "Confidence Score", "Technical Score", "Market Score", "Sector Score",
    "Ownership Score", "Event Risk Score", "Market Context", "Ownership Signal", "Earnings Date",
    "Review Trigger"
]
REVIEW_LOG_HEADERS = [
    "Review Date", "Symbol", "Price", "P/L %", "Distance from Stop %", "Technical Score",
    "Market Score", "Sector Score", "Ownership Score", "Event Risk Score", "Confidence Score",
    "Trend Note", "Sector Trend", "Market Context", "Volume Note", "Event Context",
    "Ownership Note", "Decision", "Exit Trigger Type", "Why Hold / Exit"
]
NEW_PICKS_HEADERS = [
    "Date", "Symbol", "Sector", "Entry Zone", "Stop Loss", "Strategy Type", "Technical Score",
    "Market Score", "Sector Score", "Ownership Score", "Event Risk Score", "Confidence Score",
    "Setup Reason", "Market Alignment", "Ownership Confirmation", "Earnings Risk", "Risk/Reward",
    "Status", "Added to Portfolio?"
]
LEARNING_HEADERS = ["Metric", "Value"]
MARKET_PULSE_HEADERS = [
    "Date", "Scope", "Symbol/Index", "Sector", "Trend", "5D %", "20D %", "Above20DMA", "Note"
]
EVENT_CALENDAR_HEADERS = [
    "Event Date", "Scope", "Symbol", "Title", "Severity", "Note", "Source", "Active"
]
OWNERSHIP_HEADERS = [
    "Date", "Symbol", "Direction", "Strength", "Confidence", "Source", "Note", "Active"
]

UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "SUNPHARMA",
    "BEL", "BHARTIARTL", "TITAN", "AXISBANK", "ULTRACEMCO", "BAJFINANCE", "KOTAKBANK",
    "MARUTI", "NTPC", "POWERGRID", "HCLTECH", "TECHM"
]
SECTOR_MAP = {
    "RELIANCE": "Energy",
    "TCS": "IT",
    "INFY": "IT",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "LT": "Capital Goods",
    "SUNPHARMA": "Pharma",
    "BEL": "Capital Goods",
    "BHARTIARTL": "Telecom",
    "TITAN": "Consumer",
    "AXISBANK": "Banking",
    "ULTRACEMCO": "Materials",
    "BAJFINANCE": "Financials",
    "KOTAKBANK": "Banking",
    "MARUTI": "Auto",
    "NTPC": "Energy",
    "POWERGRID": "Energy",
    "HCLTECH": "IT",
    "TECHM": "IT",
}
SECTOR_INDEX_MAP = {
    "IT": "^CNXIT",
    "Pharma": "^CNXPHARMA",
    "Auto": "^CNXAUTO",
    "Energy": "^CNXENERGY",
    "Consumer": "^CNXFMCG",
    "Banking": "^NSEBANK",
    "Financials": "^NSEBANK",
    "Capital Goods": "^NSEI",
    "Materials": "^NSEI",
    "Telecom": "^NSEI",
}
INDEXES = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY FMCG": "^CNXFMCG",
}
SEVERITY_PENALTY = {"low": 1.0, "medium": 3.0, "high": 5.0}
STRENGTH_SCORE = {"weak": 4.5, "medium": 6.5, "strong": 8.5}
CONF_SCORE = {"low": 0.75, "medium": 0.9, "high": 1.0}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
CACHE = {}


def fmt(x, digits=2):
    return f"{x:.{digits}f}"


def pct(a, b):
    if not b:
        return 0.0
    return (a - b) / b * 100.0


def sma(values, n):
    values = [v for v in values if v is not None]
    if not values:
        return 0.0
    if len(values) < n:
        return sum(values) / len(values)
    return sum(values[-n:]) / n


def parse_float(value, default=None):
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return default


def parse_date(value):
    try:
        return datetime.fromisoformat(str(value).strip()).date()
    except Exception:
        return None


def clamp(x, lo=0.0, hi=10.0):
    return max(lo, min(hi, x))


def load_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return build("sheets", "v4", credentials=creds)


def get_values(service, rng):
    return service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=rng).execute().get("values", [])


def put_values(service, rng, values):
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=rng,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def get_sheet_meta(service):
    return service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()


def ensure_tabs(service, required_titles):
    meta = get_sheet_meta(service)
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}
    requests = []
    for title in required_titles:
        if title not in existing:
            requests.append({"addSheet": {"properties": {"title": title}}})
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": requests}).execute()


def ensure_headers(service, title, headers, width=2000):
    values = get_values(service, f"'{title}'!A1:ZZ{width}")
    body = values[1:] if values else []
    normalized = [headers]
    for row in body:
        current = {headers[i]: (row[i] if i < len(row) else "") for i in range(min(len(row), len(headers)))}
        legacy = {values[0][i]: row[i] for i in range(min(len(values[0]) if values else 0, len(row)))} if values else {}
        merged = []
        for h in headers:
            merged.append(current.get(h, legacy.get(h, "")))
        normalized.append(merged)
    put_values(service, f"'{title}'!A1:ZZ{width}", normalized)


def fetch_chart(ticker, range_="6mo", interval="1d"):
    key = (ticker, range_, interval)
    if key in CACHE:
        return CACHE[key]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    r = SESSION.get(url, params={"range": range_, "interval": interval, "includePrePost": "false"}, timeout=20)
    r.raise_for_status()
    data = r.json()["chart"]["result"][0]
    ts = data.get("timestamp") or []
    q = data["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(ts):
        close = q.get("close", [None])[i]
        open_ = q.get("open", [None])[i]
        high = q.get("high", [None])[i]
        low = q.get("low", [None])[i]
        vol = q.get("volume", [None])[i]
        if None in (close, open_, high, low):
            continue
        out.append({
            "date": datetime.fromtimestamp(t, TIMEZONE).date().isoformat(),
            "open": float(open_),
            "high": float(high),
            "low": float(low),
            "close": float(close),
            "volume": float(vol or 0),
        })
    if not out:
        raise RuntimeError(f"No data for {ticker}")
    CACHE[key] = out
    return out


def fetch_stock_history(symbol):
    return fetch_chart(f"{symbol}.NS")


def compute_trend_metrics(history):
    closes = [x["close"] for x in history]
    vols = [x["volume"] for x in history]
    latest = history[-1]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    avg_vol20 = sma(vols, 20)
    ret5 = pct(latest["close"], closes[-6]) if len(closes) >= 6 else pct(latest["close"], closes[0])
    ret20 = pct(latest["close"], closes[-21]) if len(closes) >= 21 else pct(latest["close"], closes[0])
    high20 = max(closes[-20:]) if len(closes) >= 20 else max(closes)
    low10 = min([x["low"] for x in history[-10:]]) if len(history) >= 10 else min([x["low"] for x in history])
    dist20 = pct(latest["close"], sma20)
    vol_ratio = latest["volume"] / avg_vol20 if avg_vol20 else 1.0
    return {
        "latest": latest,
        "sma20": sma20,
        "sma50": sma50,
        "ret5": ret5,
        "ret20": ret20,
        "high20": high20,
        "low10": low10,
        "dist20": dist20,
        "vol_ratio": vol_ratio,
    }


def classify_trend(metrics):
    c = metrics["latest"]["close"]
    sma20 = metrics["sma20"]
    sma50 = metrics["sma50"]
    ret20 = metrics["ret20"]
    if c > sma20 > sma50 and ret20 > 4:
        return "strong uptrend"
    if c >= sma20 and ret20 >= 0:
        return "uptrend / constructive"
    if c >= sma50:
        return "sideways / mixed"
    return "downtrend pressure"


def technical_score(metrics, entry_price=None, stop_loss=None):
    score = 4.0
    c = metrics["latest"]["close"]
    if c > metrics["sma20"]:
        score += 1.5
    if metrics["sma20"] > metrics["sma50"]:
        score += 1.5
    if metrics["ret20"] > 4:
        score += 1.5
    elif metrics["ret20"] > 0:
        score += 0.75
    if metrics["ret5"] > 0:
        score += 0.75
    if 0.9 <= metrics["vol_ratio"] <= 1.5:
        score += 0.5
    elif metrics["vol_ratio"] > 1.5:
        score += 0.75
    if abs(pct(c, metrics["high20"])) <= 5:
        score += 0.5
    if pct(c, metrics["sma20"]) > 8:
        score -= 1.0
    if stop_loss:
        dist_stop = pct(c, stop_loss)
        if dist_stop < 0:
            score -= 4.0
        elif dist_stop < 2:
            score -= 1.5
        elif dist_stop < 4:
            score -= 0.5
    return clamp(score)


def build_market_context():
    context = {}
    pulse_rows = [MARKET_PULSE_HEADERS]
    for name, ticker in INDEXES.items():
        hist = fetch_chart(ticker)
        metrics = compute_trend_metrics(hist)
        trend = classify_trend(metrics)
        note = f"close vs 20DMA {metrics['dist20']:+.2f}%"
        pulse_rows.append([
            TODAY_STR, "INDEX", ticker, name, trend, fmt(metrics["ret5"]), fmt(metrics["ret20"]),
            "Yes" if metrics["latest"]["close"] > metrics["sma20"] else "No", note
        ])
        context[ticker] = {"name": name, "ticker": ticker, "metrics": metrics, "trend": trend, "note": note}
    nifty = context["^NSEI"]["metrics"]
    bank = context["^NSEBANK"]["metrics"]
    market_score = 5.0
    if nifty["latest"]["close"] > nifty["sma20"]:
        market_score += 1.5
    if nifty["sma20"] > nifty["sma50"]:
        market_score += 1.5
    if nifty["ret20"] > 2:
        market_score += 1.0
    if bank["ret20"] > 2:
        market_score += 0.5
    market_score = clamp(market_score)
    broad_note = f"Nifty {context['^NSEI']['trend']} ({nifty['ret20']:+.2f}% 20d), Bank Nifty {context['^NSEBANK']['trend']} ({bank['ret20']:+.2f}% 20d)"
    return context, pulse_rows, market_score, broad_note


def sector_context(sector, market_ctx):
    ticker = SECTOR_INDEX_MAP.get(sector, "^NSEI")
    data = market_ctx[ticker]
    metrics = data["metrics"]
    score = 5.0
    if metrics["latest"]["close"] > metrics["sma20"]:
        score += 1.5
    if metrics["sma20"] > metrics["sma50"]:
        score += 1.5
    if metrics["ret20"] > 3:
        score += 1.0
    elif metrics["ret20"] < -3:
        score -= 1.5
    return clamp(score), data["trend"], f"{data['name']} {data['trend']} ({metrics['ret20']:+.2f}% 20d)"


def load_event_rows(service):
    rows = get_values(service, "'Event Calendar'!A1:H500")
    header = rows[0] if rows else EVENT_CALENDAR_HEADERS
    data = []
    for row in rows[1:]:
        item = {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}
        data.append(item)
    return data


def load_ownership_rows(service):
    rows = get_values(service, "'Ownership Signals'!A1:H1000")
    header = rows[0] if rows else OWNERSHIP_HEADERS
    data = []
    for row in rows[1:]:
        item = {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}
        data.append(item)
    return data


def evaluate_event_risk(symbol, event_rows):
    relevant = []
    for row in event_rows:
        active = str(row.get("Active", "")).strip().lower()
        if active and active not in ("yes", "true", "1", "active"):
            continue
        event_date = parse_date(row.get("Event Date"))
        if not event_date:
            continue
        days = (event_date - TODAY).days
        if days < 0 or days > 10:
            continue
        scope = str(row.get("Scope", "")).strip().upper()
        event_symbol = str(row.get("Symbol", "")).strip().upper()
        if scope == "MARKET" or event_symbol == symbol:
            relevant.append((days, row))
    if not relevant:
        return 9.0, "No near-term event entered", "Unknown", "no-near-event"
    penalty = 0.0
    notes = []
    earnings_date = ""
    trigger = "event-watch"
    for days, row in sorted(relevant, key=lambda x: x[0]):
        severity = str(row.get("Severity", "medium")).strip().lower() or "medium"
        penalty += max(1.0, SEVERITY_PENALTY.get(severity, 3.0) - min(days, 5) * 0.5)
        title = row.get("Title", "Event")
        notes.append(f"{title} in {days}d ({severity})")
        if "earn" in title.lower() or str(row.get("Scope", "")).strip().upper() == "SYMBOL":
            earnings_date = row.get("Event Date", "")
    score = clamp(10.0 - penalty)
    label = "High" if score <= 4 else "Medium" if score <= 7 else "Low"
    return score, "; ".join(notes), earnings_date or "Unknown", trigger


def evaluate_ownership(symbol, ownership_rows):
    candidates = []
    for row in ownership_rows:
        active = str(row.get("Active", "")).strip().lower()
        if active and active not in ("yes", "true", "1", "active"):
            continue
        if str(row.get("Symbol", "")).strip().upper() != symbol:
            continue
        row_date = parse_date(row.get("Date")) or datetime(1970, 1, 1).date()
        candidates.append((row_date, row))
    if not candidates:
        return 5.0, "No ownership signal entered", "Unknown"
    _, latest = sorted(candidates, key=lambda x: x[0])[-1]
    direction = str(latest.get("Direction", "neutral")).strip().lower() or "neutral"
    strength = str(latest.get("Strength", "medium")).strip().lower() or "medium"
    confidence = str(latest.get("Confidence", "medium")).strip().lower() or "medium"
    base = STRENGTH_SCORE.get(strength, 6.5)
    if direction in ("sell", "negative", "reduce"):
        base = 10.5 - base
    elif direction in ("neutral", "mixed"):
        base = 5.5
    score = clamp(base * CONF_SCORE.get(confidence, 0.9))
    note = f"{direction} / {strength} / {confidence} — {latest.get('Note', '')}".strip()
    label = f"{direction.title()} ({strength})"
    return score, note, label


def stock_analysis(symbol, sector, market_score, market_note, market_ctx, event_rows, ownership_rows, entry_price=None, stop_loss=None):
    history = fetch_stock_history(symbol)
    metrics = compute_trend_metrics(history)
    trend = classify_trend(metrics)
    tech = technical_score(metrics, entry_price=entry_price, stop_loss=stop_loss)
    sector_score, sector_trend, sector_note = sector_context(sector, market_ctx)
    ownership_score, ownership_note, ownership_label = evaluate_ownership(symbol, ownership_rows)
    event_score, event_note, earnings_date, review_trigger = evaluate_event_risk(symbol, event_rows)
    confidence = clamp(0.40 * tech + 0.20 * market_score + 0.15 * sector_score + 0.15 * ownership_score + 0.10 * event_score)
    latest_close = metrics["latest"]["close"]
    pnl = pct(latest_close, entry_price) if entry_price else None
    dist_stop = pct(latest_close, stop_loss) if stop_loss else None
    volume_note = (
        "above-average volume" if metrics["vol_ratio"] >= 1.2 else
        "below-average volume" if metrics["vol_ratio"] <= 0.8 else
        "average volume"
    )
    exit_trigger = "none"
    if stop_loss and (latest_close <= stop_loss or metrics["latest"]["low"] <= stop_loss * 0.995):
        decision = "EXIT"
        exit_trigger = "stop-loss-breach"
        note = "Price violated stop-loss zone"
    elif confidence < 5.0:
        decision = "EXIT"
        exit_trigger = "low-confidence"
        note = "Multi-signal confidence deteriorated"
    elif stop_loss and dist_stop is not None and dist_stop <= 2.0:
        decision = "WATCH"
        exit_trigger = "near-stop"
        note = "Very close to stop-loss"
    elif tech < 6.0 or event_score <= 4.0 or metrics["ret5"] < -2.5:
        decision = "WATCH"
        exit_trigger = "momentum-or-event-risk"
        note = "Needs close monitoring due to setup weakness or event risk"
    else:
        decision = "HOLD"
        note = "Trend, market, and sector alignment remain supportive"
    movement_note = f"5d {metrics['ret5']:+.2f}%, 20d {metrics['ret20']:+.2f}%, close vs 20DMA {metrics['dist20']:+.2f}%"
    return {
        "symbol": symbol,
        "sector": sector,
        "close": latest_close,
        "pnl": pnl,
        "distance_to_stop": dist_stop,
        "trend_note": trend,
        "sector_trend": sector_trend,
        "market_context": market_note,
        "sector_context": sector_note,
        "volume_note": volume_note,
        "event_context": event_note,
        "ownership_note": ownership_note,
        "ownership_label": ownership_label,
        "earnings_date": earnings_date,
        "technical_score": tech,
        "market_score": market_score,
        "sector_score": sector_score,
        "ownership_score": ownership_score,
        "event_score": event_score,
        "confidence": confidence,
        "decision": decision,
        "decision_note": note,
        "review_trigger": review_trigger,
        "exit_trigger": exit_trigger,
        "movement_note": movement_note,
        "low10": metrics["low10"],
        "high20": metrics["high20"],
        "sma20": metrics["sma20"],
        "sma50": metrics["sma50"],
        "ret5": metrics["ret5"],
        "ret20": metrics["ret20"],
        "vol_ratio": metrics["vol_ratio"],
    }


def build_new_picks(existing_symbols, market_score, market_note, market_ctx, event_rows, ownership_rows):
    picks = []
    for symbol in UNIVERSE:
        if symbol in existing_symbols:
            continue
        sector = SECTOR_MAP.get(symbol, "Unknown")
        try:
            a = stock_analysis(symbol, sector, market_score, market_note, market_ctx, event_rows, ownership_rows)
        except Exception:
            continue
        if a["technical_score"] < 6.5 or a["confidence"] < 6.2 or a["event_score"] <= 3.5:
            continue
        entry_low = a["close"] * 0.995
        entry_high = a["close"] * 1.005
        stop = min(a["low10"] * 0.995, a["sma20"] * 0.985)
        risk = max(entry_low - stop, 0.01)
        reward = max(a["high20"] * 1.05 - entry_high, risk)
        rr = reward / risk
        strategy = "trend-following" if a["close"] > a["sma20"] > a["sma50"] else "pullback"
        picks.append({
            "symbol": symbol,
            "sector": sector,
            "entry_zone": f"{fmt(entry_low)}-{fmt(entry_high)}",
            "stop_loss": fmt(stop),
            "strategy": strategy,
            "technical_score": a["technical_score"],
            "market_score": a["market_score"],
            "sector_score": a["sector_score"],
            "ownership_score": a["ownership_score"],
            "event_score": a["event_score"],
            "confidence": a["confidence"],
            "setup_reason": f"{a['trend_note']}; {a['movement_note']}; {a['volume_note']}",
            "market_alignment": a["market_context"],
            "ownership_confirmation": a["ownership_label"],
            "earnings_risk": a["event_context"],
            "rr": rr,
        })
    picks.sort(key=lambda x: (x["confidence"], x["technical_score"], x["rr"]), reverse=True)
    return picks[:5]


def learning_summary(portfolio_rows, analyses):
    total = 0
    wins = 0
    losses = 0
    active = 0
    by_strategy = defaultdict(list)
    by_decision = defaultdict(int)
    by_sector = defaultdict(list)
    technicals = []
    confidences = []
    watches = 0
    exits = 0
    for row in portfolio_rows:
        if not row.get("Symbol"):
            continue
        total += 1
        status = str(row.get("Current Status", "")).strip().lower()
        if status == "active":
            active += 1
        pnl = parse_float(row.get("P/L %"))
        if pnl is not None:
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
        strategy = row.get("Strategy Type") or "unknown"
        sector = row.get("Sector") or "unknown"
        if pnl is not None:
            by_strategy[strategy].append(pnl)
            by_sector[sector].append(pnl)
        decision = row.get("Decision") or "unknown"
        by_decision[decision] += 1
        a = analyses.get(row.get("Symbol"))
        if a and "error" not in a:
            technicals.append(a["technical_score"])
            confidences.append(a["confidence"])
            if a["decision"] == "WATCH":
                watches += 1
            if a["decision"] == "EXIT":
                exits += 1
    avg_strategy = {k: (sum(v) / len(v)) for k, v in by_strategy.items() if v}
    avg_sector = {k: (sum(v) / len(v)) for k, v in by_sector.items() if v}
    best_strategy = max(avg_strategy, key=avg_strategy.get) if avg_strategy else "insufficient-data"
    weakest_strategy = min(avg_strategy, key=avg_strategy.get) if avg_strategy else "insufficient-data"
    strongest_sector = max(avg_sector, key=avg_sector.get) if avg_sector else "insufficient-data"
    weakest_sector = min(avg_sector, key=avg_sector.get) if avg_sector else "insufficient-data"
    common_failure = "Positions slipping below 20DMA or carrying high event risk need faster action" if (watches or exits) else "No strong failure pattern yet"
    common_success = "High-confidence trend-following setups aligned with market/sector trend are favored" if confidences else "Need more review history"
    stop_note = "Watchlist positions close to stop should not be averaged down" if watches else "Current stop placements are not flashing broad stress"
    return [
        LEARNING_HEADERS,
        ["Total Recommendations", str(total)],
        ["Win Count", str(wins)],
        ["Loss Count", str(losses)],
        ["Open Active Positions", str(active)],
        ["Average Technical Score", fmt(sum(technicals) / len(technicals)) if technicals else "n/a"],
        ["Average Confidence Score", fmt(sum(confidences) / len(confidences)) if confidences else "n/a"],
        ["Best Strategy Type", best_strategy],
        ["Weakest Strategy Type", weakest_strategy],
        ["Strongest Sector", strongest_sector],
        ["Weakest Sector", weakest_sector],
        ["Decision Mix", ", ".join(f"{k}:{v}" for k, v in sorted(by_decision.items())) or "n/a"],
        ["Common Success Pattern", common_success],
        ["Common Failure Pattern", common_failure],
        ["Stop Loss Note", stop_note],
    ]


def row_dicts(values):
    header = values[0]
    out = []
    for row in values[1:]:
        out.append({header[i]: row[i] if i < len(row) else "" for i in range(len(header))})
    return out


def repair_legacy_portfolio_rows(rows):
    repaired = []
    valid_statuses = {"active", "closed", "watch", "exit", "inactive"}
    for row in rows:
        symbol = str(row.get("Symbol", "")).strip().upper()
        if not symbol:
            repaired.append(row)
            continue
        initial_reason = str(row.get("Initial Reason", "")).strip().lower()
        current_status = str(row.get("Current Status", "")).strip().lower()
        current_status_numeric = parse_float(row.get("Current Status"))
        if initial_reason in valid_statuses and current_status_numeric is not None:
            old_initial_reason = row.get("Sector", "")
            old_status = row.get("Initial Reason", "")
            old_last_close = row.get("Current Status", "")
            old_pnl = row.get("Last Close", "")
            old_last_review = row.get("P/L %", "")
            old_decision = row.get("Last Review Date", "")
            old_decision_note = row.get("Decision", "") or row.get("Decision Note", "")
            row["Sector"] = SECTOR_MAP.get(symbol, row.get("Sector") or "Unknown")
            row["Initial Reason"] = old_initial_reason
            row["Current Status"] = old_status
            row["Last Close"] = old_last_close
            row["P/L %"] = old_pnl
            row["Last Review Date"] = old_last_review
            row["Decision"] = old_decision
            row["Decision Note"] = old_decision_note
        if not row.get("Sector"):
            row["Sector"] = SECTOR_MAP.get(symbol, "Unknown")
        repaired.append(row)
    return repaired


def dicts_to_rows(dict_rows, headers):
    rows = [headers]
    for item in dict_rows:
        rows.append([item.get(h, "") for h in headers])
    return rows


def seed_helper_tabs(service):
    events = get_values(service, "'Event Calendar'!A1:H50")
    if len(events) <= 1:
        sample = [
            EVENT_CALENDAR_HEADERS,
            [TODAY_STR, "MARKET", "", "RBI / macro event placeholder", "medium", "Update upcoming macro events here", "manual", "Yes"],
            [(TODAY + timedelta(days=7)).isoformat(), "SYMBOL", "TCS", "Earnings placeholder", "medium", "Replace with actual date when known", "manual", "Yes"],
        ]
        put_values(service, "'Event Calendar'!A1:H50", sample)
    ownership = get_values(service, "'Ownership Signals'!A1:H50")
    if len(ownership) <= 1:
        sample = [
            OWNERSHIP_HEADERS,
            [TODAY_STR, "RELIANCE", "neutral", "medium", "medium", "manual", "Replace with promoter/institutional signal", "Yes"],
            [TODAY_STR, "TCS", "positive", "weak", "medium", "manual", "Example placeholder row", "Yes"],
        ]
        put_values(service, "'Ownership Signals'!A1:H50", sample)


def main():
    service = load_service()
    ensure_tabs(service, ["Portfolio", "Daily Review Log", "New Picks", "Learning Summary", "Market Pulse", "Event Calendar", "Ownership Signals"])
    ensure_headers(service, "Portfolio", PORTFOLIO_HEADERS)
    ensure_headers(service, "Daily Review Log", REVIEW_LOG_HEADERS)
    ensure_headers(service, "New Picks", NEW_PICKS_HEADERS)
    ensure_headers(service, "Learning Summary", LEARNING_HEADERS)
    ensure_headers(service, "Market Pulse", MARKET_PULSE_HEADERS)
    ensure_headers(service, "Event Calendar", EVENT_CALENDAR_HEADERS)
    ensure_headers(service, "Ownership Signals", OWNERSHIP_HEADERS)
    seed_helper_tabs(service)

    market_ctx, pulse_rows, market_score, market_note = build_market_context()
    event_rows = load_event_rows(service)
    ownership_rows = load_ownership_rows(service)

    portfolio_values = get_values(service, "'Portfolio'!A1:Z1000")
    if not portfolio_values:
        raise RuntimeError("Portfolio tab is empty")
    portfolio_dicts = repair_legacy_portfolio_rows(row_dicts(portfolio_values))

    analyses = {}
    summary_lines = []
    active_symbols = set()
    updated_portfolio = []

    for row in portfolio_dicts:
        symbol = str(row.get("Symbol", "")).strip().upper()
        if not symbol:
            updated_portfolio.append(row)
            continue
        sector = (row.get("Sector") or SECTOR_MAP.get(symbol) or "Unknown").strip()
        row["Sector"] = sector
        status = str(row.get("Current Status", "")).strip().lower()
        entry_price = parse_float(row.get("Entry Price"))
        stop_loss = parse_float(row.get("Stop Loss"))
        try:
            analyses[symbol] = stock_analysis(symbol, sector, market_score, market_note, market_ctx, event_rows, ownership_rows, entry_price, stop_loss)
        except Exception as e:
            analyses[symbol] = {"error": str(e), "decision": row.get("Decision", "ERROR"), "decision_note": f"Data fetch failed: {e}"}
        a = analyses[symbol]
        if status == "active" and "error" not in a:
            active_symbols.add(symbol)
            row["Last Close"] = fmt(a["close"])
            row["P/L %"] = fmt(a["pnl"] if a["pnl"] is not None else 0.0)
            row["Last Review Date"] = TODAY_STR
            row["Decision"] = a["decision"]
            row["Decision Note"] = f"{a['decision_note']}; {a['movement_note']}"
            row["Confidence Score"] = fmt(a["confidence"])
            row["Technical Score"] = fmt(a["technical_score"])
            row["Market Score"] = fmt(a["market_score"])
            row["Sector Score"] = fmt(a["sector_score"])
            row["Ownership Score"] = fmt(a["ownership_score"])
            row["Event Risk Score"] = fmt(a["event_score"])
            row["Market Context"] = a["market_context"]
            row["Ownership Signal"] = a["ownership_label"]
            row["Earnings Date"] = a["earnings_date"]
            row["Review Trigger"] = a["review_trigger"] if a["decision"] != "EXIT" else a["exit_trigger"]
            summary_lines.append(
                f"- {symbol}: {a['decision']} @ {fmt(a['close'])} | conf {a['confidence']:.1f}/10 | tech {a['technical_score']:.1f} | sector {a['sector_trend']} | {a['decision_note']}"
            )
        updated_portfolio.append(row)

    # review log refresh for today
    log_values = get_values(service, "'Daily Review Log'!A1:T5000")
    existing_log = row_dicts(log_values) if log_values else []
    filtered_log = [r for r in existing_log if not (r.get("Review Date") == TODAY_STR and r.get("Symbol", "").strip().upper() in active_symbols)]
    for symbol in sorted(active_symbols):
        a = analyses[symbol]
        filtered_log.append({
            "Review Date": TODAY_STR,
            "Symbol": symbol,
            "Price": fmt(a["close"]),
            "P/L %": fmt(a["pnl"] if a["pnl"] is not None else 0.0),
            "Distance from Stop %": fmt(a["distance_to_stop"] if a["distance_to_stop"] is not None else 0.0),
            "Technical Score": fmt(a["technical_score"]),
            "Market Score": fmt(a["market_score"]),
            "Sector Score": fmt(a["sector_score"]),
            "Ownership Score": fmt(a["ownership_score"]),
            "Event Risk Score": fmt(a["event_score"]),
            "Confidence Score": fmt(a["confidence"]),
            "Trend Note": a["trend_note"],
            "Sector Trend": a["sector_trend"],
            "Market Context": a["market_context"],
            "Volume Note": a["volume_note"],
            "Event Context": a["event_context"],
            "Ownership Note": a["ownership_note"],
            "Decision": a["decision"],
            "Exit Trigger Type": a["exit_trigger"],
            "Why Hold / Exit": a["decision_note"],
        })

    picks = build_new_picks(active_symbols, market_score, market_note, market_ctx, event_rows, ownership_rows)
    pick_rows = []
    for p in picks:
        pick_rows.append({
            "Date": TODAY_STR,
            "Symbol": p["symbol"],
            "Sector": p["sector"],
            "Entry Zone": p["entry_zone"],
            "Stop Loss": p["stop_loss"],
            "Strategy Type": p["strategy"],
            "Technical Score": fmt(p["technical_score"]),
            "Market Score": fmt(p["market_score"]),
            "Sector Score": fmt(p["sector_score"]),
            "Ownership Score": fmt(p["ownership_score"]),
            "Event Risk Score": fmt(p["event_score"]),
            "Confidence Score": fmt(p["confidence"]),
            "Setup Reason": p["setup_reason"],
            "Market Alignment": p["market_alignment"],
            "Ownership Confirmation": p["ownership_confirmation"],
            "Earnings Risk": p["earnings_risk"],
            "Risk/Reward": fmt(p["rr"]),
            "Status": "watchlist",
            "Added to Portfolio?": "No",
        })

    learning_rows = learning_summary(updated_portfolio, analyses)
    put_values(service, "'Portfolio'!A1:Z1000", dicts_to_rows(updated_portfolio, PORTFOLIO_HEADERS))
    put_values(service, "'Daily Review Log'!A1:T5000", dicts_to_rows(filtered_log, REVIEW_LOG_HEADERS))
    put_values(service, "'New Picks'!A1:S200", dicts_to_rows(pick_rows, NEW_PICKS_HEADERS))
    put_values(service, "'Learning Summary'!A1:B100", learning_rows)
    put_values(service, "'Market Pulse'!A1:I200", pulse_rows)

    payload = {
        "date": TODAY_STR,
        "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit",
        "market_context": market_note,
        "active_reviewed": len(active_symbols),
        "summary": summary_lines,
        "new_picks": [
            f"{p['symbol']} ({p['sector']}) entry {p['entry_zone']} stop {p['stop_loss']} conf {p['confidence']:.1f}/10 rr {p['rr']:.2f}"
            for p in picks
        ],
        "notes": [
            "Ownership and event-risk layers are active. Fill/update the 'Ownership Signals' and 'Event Calendar' tabs to improve the daily calls.",
            "The learning summary now reflects multi-stage scoring, not just price movement."
        ]
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
