#!/usr/bin/env python3
"""
NSE Prediction Analyzer — Tracks morning bias accuracy, root causes, learnings.
Writes to Google Sheet tabs and outputs structured JSON for LLM analysis.

Usage:
  python3 nse_prediction_analyzer.py            # Full run: read, analyze, write
  python3 nse_prediction_analyzer.py --preview  # Preview only, no write

Mode: no_agent (stdout is consumed by the agent-driven cron via context_from)
"""

import json, os, sys, warnings
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter

warnings.filterwarnings('ignore')

# ── Config ──────────────────────────────────────────────────────────────
HERMES_HOME = os.path.expanduser("~/.hermes")
DATA_DIR = os.path.join(HERMES_HOME, "data", "nse_signals")
SIGNAL_FILE = os.path.join(DATA_DIR, "signal_history.json")
SHEET_ID = "1J2OpZyiiGnDMlXJgExR1HgnJmyIH2HjIC5siHoGFbZ4"
TOKEN_PATH = os.path.expanduser("~/.hermes/google_token.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TIMEZONE = ZoneInfo("Asia/Kolkata")

ALL_FACTORS = ["gift_nifty", "asian_peers", "us_futures", "crude_oil",
               "usd_inr", "dxy", "india_vix", "bank_nifty"]

FACTOR_LABELS = {
    "gift_nifty": "GIFT NIFTY", "asian_peers": "ASIAN PEERS",
    "us_futures": "US FUTURES", "crude_oil": "CRUDE OIL",
    "usd_inr": "USD/INR", "dxy": "DXY",
    "india_vix": "INDIA VIX", "bank_nifty": "BANK NIFTY"
}

FACTOR_WEIGHTS = {
    "gift_nifty": 0.20, "asian_peers": 0.15, "crude_oil": 0.15,
    "india_vix": 0.15, "us_futures": 0.10, "usd_inr": 0.10,
    "bank_nifty": 0.10, "dxy": 0.05
}

# ── Google Sheets Helpers ──────────────────────────────────────────────

def get_sheets_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)

def ensure_tab(service, tab_title, headers):
    """Create tab if it doesn't exist, write headers if empty."""
    sheet = service.spreadsheets()
    meta = sheet.get(spreadsheetId=SHEET_ID).execute()
    existing = [s["properties"]["title"] for s in meta.get("sheets", [])]
    
    if tab_title not in existing:
        body = {"requests": [{
            "addSheet": {"properties": {"title": tab_title}}
        }]}
        sheet.batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
        # Write headers
        sheet.values().update(
            spreadsheetId=SHEET_ID,
            range=f"'{tab_title}'!A1:{chr(64+len(headers))}1",
            valueInputOption="RAW",
            body={"values": [headers]}
        ).execute()
        return True  # new tab
    else:
        # Check if headers exist
        result = sheet.values().get(
            spreadsheetId=SHEET_ID,
            range=f"'{tab_title}'!A1:{chr(64+len(headers))}1"
        ).execute()
        if not result.get("values"):
            sheet.values().update(
                spreadsheetId=SHEET_ID,
                range=f"'{tab_title}'!A1:{chr(64+len(headers))}1",
                valueInputOption="RAW",
                body={"values": [headers]}
            ).execute()
        return False

def append_row(service, tab_title, row):
    """Append a row to the end of a tab."""
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"'{tab_title}'!A:A",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]}
    ).execute()

def read_tab(service, tab_title):
    """Read all data from a tab."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"'{tab_title}'!A:Z"
    ).execute()
    return result.get("values", [])

# ── Analysis Functions ─────────────────────────────────────────────────

def load_signals():
    if not os.path.exists(SIGNAL_FILE):
        return []
    try:
        with open(SIGNAL_FILE) as f:
            return json.load(f)
    except:
        return []

def analyze_factors(history):
    """Per-factor accuracy analysis."""
    factor_data = {f: {"total": 0, "correct": 0, "wrong": 0,
                       "contributions": [], "directions": []}
                   for f in ALL_FACTORS}
    
    for entry in history:
        v = entry.get("verification")
        if not v:
            continue
        morning = entry.get("signal", {})
        raw_scores = morning.get("raw_scores", {})
        direction_correct = v.get("direction_correct", False)
        
        for factor in ALL_FACTORS:
            score = raw_scores.get(factor, 0)
            if score == 0:
                continue  # neutral/no contribution
            factor_data[factor]["total"] += 1
            factor_data[factor]["contributions"].append(score)
            factor_data[factor]["directions"].append(score)
            if direction_correct:
                factor_data[factor]["correct"] += 1
            else:
                factor_data[factor]["wrong"] += 1
    
    results = []
    for f in ALL_FACTORS:
        d = factor_data[f]
        total = d["total"]
        acc = round(d["correct"] / total * 100, 1) if total > 0 else None
        avg_contribution = round(sum(d["contributions"]) / len(d["contributions"]), 2) if d["contributions"] else 0
        # Weight in the model
        weight = FACTOR_WEIGHTS.get(f, 0)
        
        # Last 5 directions
        recent = d["directions"][-5:] if d["directions"] else []
        
        results.append({
            "factor": f,
            "label": FACTOR_LABELS.get(f, f),
            "total": total,
            "correct": d["correct"],
            "wrong": d["wrong"],
            "accuracy": acc,
            "avg_contribution": avg_contribution,
            "weight": weight,
            "recent_directions": recent
        })
    
    return sorted(results, key=lambda x: x["total"] if x["total"] else 0, reverse=True)

def find_last_unanalyzed(history):
    """Find the most recent entry that has verification but hasn't been logged."""
    for entry in reversed(history):
        v = entry.get("verification")
        if not v:
            continue
        # Check if already analyzed by looking at date
        return entry
    return None

def root_cause_analysis(entry):
    """Script-based preliminary root cause — LLM will expand later."""
    v = entry.get("verification", {})
    morning = entry.get("signal", {})
    raw_scores = morning.get("raw_scores", {})
    breakdown = entry.get("breakdown", [])
    
    direction_correct = v.get("direction_correct", False)
    actual_bias = v.get("actual", {}).get("bias", "?")
    morning_bias = morning.get("bias", "?")
    
    if direction_correct:
        # Find the factors that correctly predicted the direction
        correct_factors = [b for b in breakdown if b["score"] != 0 and (
            (morning_bias in ("BULLISH", "MILD_BULLISH") and b["score"] > 0) or
            (morning_bias in ("BEARISH", "MILD_BEARISH") and b["score"] < 0)
        )]
        misleading_factors = [b for b in breakdown if b["score"] != 0 and (
            (morning_bias in ("BULLISH", "MILD_BULLISH") and b["score"] < 0) or
            (morning_bias in ("BEARISH", "MILD_BEARISH") and b["score"] > 0)
        )]
        return {
            "type": "correct",
            "summary": "Prediction was correct",
            "supporting_factors": [b["factor"] for b in correct_factors],
            "contradicting_factors": [b["factor"] for b in misleading_factors],
            "confidence": morning.get("confidence", 0),
        }
    else:
        # WRONG — find which factors misled
        misleading = []
        neutral_missed = []
        for b in breakdown:
            if b["score"] != 0:
                misleading.append(b)
            else:
                neutral_missed.append(b)
        
        # Key question: bias was X but actual was opposite
        return {
            "type": "wrong",
            "summary": f"Predicted {morning_bias} but actual was {actual_bias}",
            "misleading_factors": [b["factor"] for b in misleading],
            "neutral_factors_that_should_have_signaled": [b["factor"] for b in neutral_missed],
            "confidence": morning.get("confidence", 0),
            "accuracy_score": v.get("accuracy_score", 0),
        }

def compute_stats(history):
    """Compute overall accuracy stats."""
    verified = [h for h in history if "verification" in h]
    correct = sum(1 for v in verified if bool(v["verification"].get("direction_correct")))
    total = len(verified)
    
    # By bias type
    by_bias = defaultdict(list)
    for h in verified:
        mb = h.get("signal", {}).get("bias", "UNKNOWN")
        by_bias[mb].append(h)
    
    bias_accuracy = {}
    for bias, entries in by_bias.items():
        b_total = len(entries)
        b_correct = sum(1 for e in entries if e["verification"].get("direction_correct"))
        bias_accuracy[bias] = {
            "total": b_total,
            "correct": b_correct,
            "accuracy": round(b_correct / b_total * 100, 1) if b_total > 0 else 0
        }
    
    # By confidence band
    by_conf = {"low": {"total": 0, "correct": 0},      # 1-4
               "medium": {"total": 0, "correct": 0},   # 5-7
               "high": {"total": 0, "correct": 0}}     # 8-10
    for h in verified:
        conf = h.get("signal", {}).get("confidence", 0)
        is_correct = h["verification"].get("direction_correct", False)
        if conf <= 4:
            key = "low"
        elif conf <= 7:
            key = "medium"
        else:
            key = "high"
        by_conf[key]["total"] += 1
        if is_correct:
            by_conf[key]["correct"] += 1
    
    for k in by_conf:
        t = by_conf[k]["total"]
        by_conf[k]["accuracy"] = round(by_conf[k]["correct"] / t * 100, 1) if t > 0 else 0
    
    # Running accuracy trend (last N entries)
    trend_window = min(10, len(verified))
    recent = verified[-trend_window:] if trend_window > 0 else []
    recent_correct = sum(1 for v in recent if v["verification"].get("direction_correct"))
    
    # Confusion matrix
    confusion = defaultdict(lambda: {"correct": 0, "total": 0})
    for h in verified:
        mb = h.get("signal", {}).get("bias", "UNKNOWN")
        ab = h["verification"].get("actual", {}).get("bias", "UNKNOWN")
        key = f"{mb}→{ab}"
        confusion[key]["total"] += 1
        if h["verification"].get("direction_correct"):
            confusion[key]["correct"] += 1
    
    # Average accuracy score
    acc_scores = [v["verification"].get("accuracy_score", 0) for v in verified]
    avg_acc_score = round(sum(acc_scores) / len(acc_scores), 1) if acc_scores else 0
    
    
    return {
        "total_signals": len(history),
        "total_verified": total,
        "total_correct": int(correct),
        "overall_accuracy": round(correct / total * 100, 1) if total > 0 else 0,
        "overall_accuracy_score": float(avg_acc_score),
        "bias_accuracy": bias_accuracy,
        "confidence_accuracy": dict(by_conf),
        "recent_trend": {
            "window": trend_window,
            "correct": recent_correct,
            "accuracy": round(recent_correct / trend_window * 100, 1) if trend_window > 0 else 0
        },
        "confusion": dict(confusion),
    }

# ── Main ──────────────────────────────────────────────────────────────

def main():
    preview = "--preview" in sys.argv
    
    # 1. Load signals
    history = load_signals()
    if not history:
        print(json.dumps({"error": "No signal history found"}))
        return
    
    # 2. Compute stats
    stats = compute_stats(history)
    factor_perf = analyze_factors(history)
    
    # 3. Find latest verified entry
    latest = history[-1] if history else None
    latest_v = latest.get("verification") if latest else None
    
    # 4. Root cause for latest
    rc = root_cause_analysis(latest) if latest_v else None
    
    # 5. Check what's already in the sheet
    if not preview:
        try:
            service = get_sheets_service()
            
            # Ensure tabs exist
            ensure_tab(service, "Prediction Log", [
                "Date", "Morning Bias", "Confidence", "Score", 
                "Actual Bias", "Actual Change%", "Direction Correct",
                "Accuracy Score", "GIFT_NIFTY", "ASIAN_PEERS", "US_FUTURES",
                "CRUDE_OIL", "USDINR", "DXY", "INDIA_VIX", "BANK_NIFTY",
                "Root Cause", "Learning", "Data Sources"
            ])
            
            ensure_tab(service, "Factor Performance", [
                "Factor", "Label", "Total", "Correct", "Wrong",
                "Accuracy%", "Avg Contribution", "Model Weight",
                "Last 5 Directions"
            ])
            
            ensure_tab(service, "Learning Log", [
                "Date", "Type", "Morning Bias", "Actual Bias",
                "Root Cause Summary", "Learning", "Action Taken"
            ])
            
            # Read existing Prediction Log to avoid duplicates
            existing = read_tab(service, "Prediction Log")
            existing_dates = set()
            for row in existing[1:]:  # skip header
                if row:
                    existing_dates.add(row[0])
            
            # Append new entries
            appended_count = 0
            for entry in history:
                v = entry.get("verification")
                if not v:
                    continue
                    
                entry_date = entry.get("timestamp", "")[:10]
                if entry_date in existing_dates:
                    continue  # already logged
                
                morning = entry.get("signal", {})
                raw_scores = morning.get("raw_scores", {})
                actual = v.get("actual", {})
                rc_entry = root_cause_analysis(entry)
                
                root_cause_str = rc_entry.get("summary", "")
                if rc_entry["type"] == "wrong":
                    misleading = ", ".join(rc_entry.get("misleading_factors", []))
                    root_cause_str = f"Misled by: {misleading}" if misleading else root_cause_str
                
                row = [
                    entry_date,
                    morning.get("bias", "?"),
                    str(morning.get("confidence", "?")),
                    str(morning.get("score", "?")),
                    actual.get("bias", "?"),
                    f"{actual.get('change_pct', 0):+.2f}%",
                    "✅ CORRECT" if v.get("direction_correct") else "❌ WRONG",
                    str(v.get("accuracy_score", "?")),
                    str(raw_scores.get("gift_nifty", 0)),
                    str(raw_scores.get("asian_peers", 0)),
                    str(raw_scores.get("us_futures", 0)),
                    str(raw_scores.get("crude_oil", 0)),
                    str(raw_scores.get("usd_inr", 0)),
                    str(raw_scores.get("dxy", 0)),
                    str(raw_scores.get("india_vix", 0)),
                    str(raw_scores.get("bank_nifty", 0)),
                    root_cause_str,
                    "",  # Learning — LLM fills this
                    f"{entry.get('data_sources', {}).get('available', 0)}/{entry.get('data_sources', {}).get('total', 0)}"
                ]
                append_row(service, "Prediction Log", row)
                
                # Append to Learning Log if wrong
                if not v.get("direction_correct"):
                    append_row(service, "Learning Log", [
                        entry_date,
                        "WRONG_PREDICTION",
                        morning.get("bias", "?"),
                        actual.get("bias", "?"),
                        root_cause_str,
                        "",  # Learning — LLM fills
                        "Pending LLM analysis"
                    ])
                appended_count += 1
            
            # Update Factor Performance tab (rewrite)
            factor_rows = [["Factor", "Label", "Total", "Correct", "Wrong",
                           "Accuracy%", "Avg Contribution", "Model Weight", "Last 5 Directions"]]
            for fp in factor_perf:
                recent_str = ", ".join([f"{'+' if s>0 else ''}{s}" for s in fp["recent_directions"]])
                factor_rows.append([
                    fp["factor"],
                    fp["label"],
                    str(fp["total"]),
                    str(fp["correct"]),
                    str(fp["wrong"]),
                    str(fp["accuracy"]) if fp["accuracy"] is not None else "N/A",
                    f"{fp['avg_contribution']:+.2f}",
                    str(fp["weight"]),
                    recent_str
                ])
            
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range="'Factor Performance'!A1:I999",
                valueInputOption="RAW",
                body={"values": factor_rows}
            ).execute()
            
            print(f"✅ Wrote {appended_count} new entries to Prediction Log", file=sys.stderr)
            
        except Exception as e:
            print(f"⚠️ Sheet write failed: {e}", file=sys.stderr)
            # Continue — script still outputs data for LLM
    
    # 6. Output structured JSON for the LLM agent to consume
    output = {
        "analysis_date": datetime.now(TIMEZONE).isoformat(),
        "stats": stats,
        "factor_performance": factor_perf,
        "latest_signal": {
            "date": latest.get("timestamp", "")[:10] if latest else None,
            "bias": latest.get("signal", {}).get("bias") if latest else None,
            "confidence": latest.get("signal", {}).get("confidence") if latest else None,
            "score": latest.get("signal", {}).get("score") if latest else None,
            "market_context": latest.get("market_context") if latest else None,
        },
        "latest_verification": latest_v,
        "root_cause": rc,
    }
    
    print(json.dumps(output, indent=2, default=str))

if __name__ == "__main__":
    main()
