     1|---
     2|name: nse-proactive-signal-scanner
     3|description: Proactive market signal scanner for NSE — generates directional bias calls BEFORE the market opens by analyzing pre-market cues (Asian peers, crude, USD/INR, VIX, futures).
     4|category: software-development
     5|version: 2.1
     6|---
     7|
     8|# NSE Proactive Trading System (Tier 1 + Tier 2)
     9|
    10|## What This Is
    11|
    12|A **proactive** trading intelligence system that generates directional bias calls **before the market opens** — not after it moves.
    13|
    14|Unlike reactive analysis ("markets fell because X"), this system:
    15|- Scans pre-market signals before 9:15 AM IST — generates a **BUY/SELL/NEUTRAL bias** with **confidence score 1-10**
    16|- **Verifies each call** vs actual Nifty close at 4:00 PM — tracks accuracy over time
    17|- Computes **key technical levels** (pivot points, S/R, moving averages)
    18|- Generates **weekly outlook** on Sundays looking forward
    19|
    20|### GitHub Backup
    21|
    22|All scripts at: https://github.com/Murugadoss7/nse-trading-system (private repo)
    23|
    24|To update backup:
    25|```bash
    26|cp ~/.hermes/scripts/nse_signal_engine.py ~/nse-trading-system/
    27|cd ~/nse-trading-system && git add -A && git commit -m "update" && git push
    28|```
    29|
    30|### Related Skills
    31|
    32|- **`nse-research-orchestrator`** — agent-driven evening portfolio review (4 PM IST). This skill reads the same Google Sheet, researches 5-7 stocks, and generates BUY/HOLD/SELL calls. The morning signal from this skill feeds into the evening review as market-context input.
    33|- **`nse-post-analysis`** — agent-driven post-market analysis (4:25 PM IST). Consumes `signal_history.json` via `nse_prediction_analyzer.py`, computes accuracy stats, writes to Google Sheet tabs (Prediction Log, Factor Performance, Learning Log), and delivers an educational Telegram report with root-cause analysis.
    34|- **`nse-trading-researcher`** — weekly self-improving research agent that analyzes this signal engine's history, backtests strategies, and proposes improvements. Strategic layer above this operational system.
    35|
    36|The four skills form a complete cycle: `[7AM] daily signal → [4PM] verify → [4:25PM] analyze → [Sun 6PM] research & improve → feedback into weights/thresholds`.
    37|
    38|## Reference Files
    39|
    40|- `references/data-flow-and-calibration.md` — detailed data pipeline documentation, scoring calibration rationale, Yahoo API constraint notes, and threshold tuning guide.
    41|- `references/vps-cron-migration-state.md` — actual cron job IDs, delivery configs, and migration status when moving NSE crons between machines.
    42|- `references/cron-script-resilience.md` — pattern for making no_agent cron scripts resilient (wrapping Google Sheets writes in try/except so the Telegram report still delivers even if side-effects fail).
    43|- `references/prediction-analyzer-data-flow.md` — schema and flow for the 4:15 PM prediction analyzer + 4:25 PM LLM post-analysis pipeline.
    44|
    45|## System Architecture
    46|
    47|```
    48|┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
    49|│ Browser-based   │────▶│ Signal Engine v2     │────▶│ User via Telegram│
    50|│ Data Harvester  │     │ nse_signal_engine.py │     │                  │
    51|│ (Yahoo Finance) │     │                      │     │ - 7AM: Bias call │
    52|└─────────────────┘     │ • Tier 1: Bias calc  │     │ - 4PM: Verify    │
    53|                        │ • Tier 2: Verify     │     │ - 4:25PM: Post-  │
    54|  8 data sources        │ • Tier 2: Levels     │     │   analysis       │
    55|  (Nifty, Nikkei,       │ • Tier 2: Weekly     │     │ - Sun: Weekly    │
    56|  Hang Seng, Crude,     └──────────────────────┘     └──────────────────┘
    57|  USD/INR, VIX, etc.)          │                          ▲
    58|                                ▼                          │
    59|                      ┌──────────────────┐         ┌──────────────────────┐
    60|                      │ signal_history   │────────▶│ nse_prediction_      │
    61|                      │ .json (90 days)  │         │ analyzer.py          │
    62|                      └──────────────────┘         │ → Google Sheet tabs │
    63|                                                    │ → LLM post-analysis │
    64|                                                    └──────────────────────┘
    65|```
    66|
    67|## Data Sources & Weights
    68|
    69|| Factor | Weight | What It Tells Us |
    70||--------|--------|-----------------|
    71|| Gift Nifty (overnight) | 20% | Overnight sentiment on India |
    72|| Asian Peers (Nikkei + Hang Seng) | 15% | Regional mood (trade before India) |
    73|| Crude Oil (Brent) | 15% | Huge impact on India's macros |
    74|| India VIX | 15% | Fear gauge — above 20 = panic |
    75|| US Futures (S&P) | 10% | Wall Street direction |
    76|| USD/INR | 10% | FII flow indicator (weak rupee = outflows) |
    77|| Bank Nifty vs Nifty | 10% | Leading sector performance |
    78|| DXY (Dollar Index) | 5% | EM pressure indicator |
    79|
    80|## Scoring System
    81|
    82|Each factor scored -2 to +2. Weighted average gives final bias:
    83|- **>= +1.0**: BULLISH (conf 7-10), **+0.3 to +1.0**: MILD BULLISH (conf 4-7)
    84|- **-0.3 to +0.3**: NEUTRAL (conf 3-5)
    85|- **-1.0 to -0.3**: MILD BEARISH (conf 4-7), **<= -1.0**: BEARISH (conf 7-10)
    86|
    87|## Files
    88|
    89|- **Signal Engine**: `~/.hermes/scripts/nse_signal_engine.py`
    90|  - `--preview` — demo with sample data
    91|  - `--from-json FILE` — process real market data
    92|  - `--verify PATH CLOSE` — verify morning bias vs actual close
    93|  - `--levels` — compute Nifty key technical levels
    94|  - `--weekly` — generate weekly outlook
    95|  - `--history` — show signal accuracy
    96|
    97|- **Data dir**: `~/.hermes/data/nse_signals/`
    98|  - `pre_market.json` — latest morning data (overwritten daily)
    99|  - `signal_history.json` — chronological signal + verification log
   100|
   101|## Cron Jobs
   102|
   103|All three jobs use **`no_agent=True`** — they run standalone Python scripts directly (no LLM inference), which keeps them free and fast.
   104|
   105|| Name | Script | Schedule (IST) | Purpose |
   106||------|--------|----------------|---------|
   107|| `nse-vps-pre-market` | `nse_vps_scanner.py` | Weekdays **7:00 AM** | Pre-market bias call |
   108|| `nse-vps-verify` | `nse_vps_verify.py` | Weekdays **4:00 PM** | Compare bias vs actual close |
   109|| `nse-vps-weekly` | `nse_vps_weekly.py` | **Sunday 7:30 PM** | Forward-looking week ahead |
   110|| `nse-data-analyzer` | `nse_prediction_analyzer.py` | Weekdays **4:15 PM** | Compute stats, write to Google Sheet (no_agent, deliver=local) |
   111|| `nse-post-analysis` | (agent-driven, skill) | Weekdays **4:25 PM** | LLM educational report → Telegram (context_from data-analyzer) |
   112|
   113|All deliver to Telegram home chat. Legacy/internal names (from earlier versions): `nse-proactive-signal-scanner`, `nse-signal-verification`, `nse-weekly-outlook`.
   114|
   115|## Daily Workflow
   116|
   117|1. **7:00 AM**: `nse_vps_scanner.py` → fetches 9 Yahoo Finance tickers via yfinance → signal engine `nse_signal_engine.py` → bias call delivered to Telegram
   118|2. **9:15 AM**: Market opens — you know whether bias says bullish/bearish
   119|3. **4:00 PM**: `nse_vps_verify.py` → fetches actual Nifty close → compares morning bias → logs accuracy to `signal_history.json`
   120|4. **4:15 PM**: `nse_prediction_analyzer.py` → reads `signal_history.json`, writes accuracy data to Google Sheet (Prediction Log, Factor Performance, Learning Log tabs)
   121|5. **4:25 PM**: `nse-post-analysis` agent → reads the analyzer output via `context_from`, generates educational Telegram report with stats, root cause, and learnings
   122|6. **Sunday 7:30 PM**: `nse_vps_weekly.py` → aggregates the week's signals, generates weekly outlook
   123|
   124|## Cron Migration & Duplicate Prevention
   125|
   126|### no_agent Script Resilience
   127|
   128|All three jobs use `no_agent=True` — they run standalone Python scripts directly (no LLM inference), which keeps them free and fast. **Crucially, any unhandled exception causes the entire output to be discarded** — the Telegram report never arrives.
   129|
   130|If a script also writes to Google Sheets (best-effort side-effect), wrap the sheet call in try/except:
   131|
   132|```python
   133|try:
   134|    write_to_sheet(...)
   135|except Exception as e:
   136|    print(f"⚠ Sheet write failed: {e}", file=sys.stderr)
   137|# Text report still reaches Telegram
   138|```
   139|
   140|Without this, a transient Google API error kills the whole delivery. See `references/cron-script-resilience.md` for the full pattern.
   141|
   142|When migrating cron jobs between machines (e.g., local → VPS):
   143|
   144|1. **Pause** the jobs on the source machine first (`cronjob action='pause'`) — stops them from firing but preserves config
   145|2. **Recreate** the jobs on the destination machine with the same schedule, script paths, and delivery target
   146|3. **Verify** one full cycle on the destination (let the job fire and check Telegram)
   147|4. **Delete** the paused jobs from the source only after confirming the destination works
   148|
   149|**Never have the same cron job active on two machines** — `no_agent=True` scripts that deliver to Telegram will fire from every machine they're active on, causing duplicate messages.
   150|
   151|### Files needed on destination
   152|
   153|Copy these 5 files to `~/.hermes/scripts/` on the target machine:
   154|
   155|- `nse_vps_scanner.py` — pre-market scanner
   156|- `nse_vps_verify.py` — 4PM verification
   157|- `nse_vps_weekly.py` — weekly outlook
   158|- `nse_signal_engine.py` — shared signal engine (imported by all 3)
   159|- `nse_prediction_analyzer.py` — post-market analysis + Google Sheet writer
   160|
   161|### Dependencies
   162|
   163|- `yfinance` — fetch market data
   164|- `numpy` — signal engine computation
   165|- Python 3.8+
   166|
   167|## Key Technical Levels (--levels)
   168|
   169|Engine computes:
   170|- Pivot Point (PP) = (H + L + C) / 3
   171|- Support S1, S2 and Resistance R1, R2
   172|- SMA-5, SMA-20, SMA-50
   173|- Today's range and width
   174|- Alerts for level breaches
   175|
   176|## How to Read a Signal
   177|
   178|```
   179|🔴🔴 BEARISH — Expect negative day
   180|   Confidence: 7/10 | Score: -1.050
   181|
   182|📊 Context: Nifty at 23519 | Crude $110.49 | ₹96.26/$ | VIX 19.53
   183|
   184|Factor Breakdown:
   185|  🔴 Gift Nifty: -1    └ Overnight: Negative
   186|  🔴 Asian Peers: -2   └ Nikkei -0.97%, Hang Seng -1.35%
   187|  🔴 Crude Oil: -1     └ $110.49 (+1.13%) — Bad for India
   188|  🔴 USD/INR: -2       └ ₹96.26/$ — Weakening rupee = bearish
   189|  🔴 Bank Nifty: -1    └ Lagging
   190|  🔴 US Futures: -1    └ -0.59%
   191|```
   192|
   193|When to trust the signal:
   194|- **Confidence 7-10**: Strong conviction — act on it
   195|- **Confidence 4-7**: Lean — confirm in first 30 min of trading
   196|- **Confidence 1-4**: Mixed — wait for opening direction
   197|
   198|## Pitfalls
   199|
   200|- **Gift Nifty data is broken.** Yahoo Finance (`GIFTNIFTY.NS`) returns price=0. The scanner estimates it from Nifty change_pct × 0.7, but this is unreliable. Gift Nifty has 20% weight — the highest single factor — yet never contributes a real signal. The effective model weight is 80%. Fix: use an alternative data source (NSE website scraping, broker API) for Gift Nifty futures.
   201|- **VIX ticker `INDIAVIX.NS` is delisted from yfinance** (as of mid-2025). The scanner fetches it but gets empty data, so VIX always scores 0. Even if it did work, the current threshold (22 for bearish) is too high for the current 18-19 low-vol regime — VIX never triggers. Two fixes needed: (1) replace the yfinance ticker (try `^INDIAVIX` or scrape from NSE India website), (2) lower or adapt the VIX threshold to be percentile-based.
   202|- **`signal_history.json` is a concurrent-write hazard.** The verify script appends verification and `nse_prediction_analyzer.py` reads it at 4:15 PM — 15 min apart, so no race. But manual runs during debugging can corrupt the JSON. Always let cron orchestrate the timing.
   203|- **Variable shadowing in accuracy computation.** When writing analysis scripts that track accuracy, never reuse `correct` as a loop variable name — it shadows the aggregate `correct = sum(...)` and turns it into a boolean from the last iteration. Use `is_correct` or `entry_correct` for loop variables instead.
   204|