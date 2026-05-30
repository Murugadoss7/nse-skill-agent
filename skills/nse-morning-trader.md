     1|---
     2|name: nse-morning-trader
     3|description: Pre-market agent that reads overnight data + yesterday's analysis + portfolio, generates stock-specific BUY/SELL/HOLD calls with entry zones before market opens at 9:15 AM IST.
     4|category: software-development
     5|version: 1.0
     6|---
     7|
     8|# NSE Morning Trader — Pre-Market Stock Calls
     9|
    10|> **⚠️ THIS SKILL LOADS `nse-trading-sme` SKILL FIRST**
    11|> The SME skill provides: expert knowledge, tool orchestration map, obsidian vault integration,
    12|> signal synthesis framework, and self-improvement loop. Load it first before proceeding.
    13|
    14|## What This Is
    15|
    16|An **agent-driven** pre-market trading advisor that runs at **7:30 AM IST** — 1h45m before NSE opens. It synthesizes:
    17|
    18|1. **Overnight global data** (US close, Asian open, crude, USD/INR, VIX) — collected by the 7AM signal script
    19|2. **Yesterday's learnings** — from Prediction Log, Factor Performance, Learning Log
    20|3. **Current portfolio** — holdings, P&L, stop losses
    21|4. **Watchlist & event calendar** — upcoming catalysts
    22|5. **SME knowledge + vault insights** — from nse-trading-sme skill (regime, sector, factor accuracy)
    23|
    24|And produces **stock-specific BUY/SELL/HOLD calls with entry zones**, not just a market bias.
    25|
    26|## SME Integration (Load Before Starting)
    27|
    28|### Step 0 — Load SME Knowledge + Vault Context
    29|
    30|**A. Load the SME skill:**
    31|`skill_view(name='nse-trading-sme')` — get expert knowledge, signal combination rules, vault patterns
    32|
    33|**B. Assess the environment** using SME section ①:
    34|- What's the current macro regime? (crude, USD/INR, DXY, VIX)
    35|- What's the volatility regime? (run volatility_regime.py check)
    36|- Which sector rotation phase? (Early/Mid/Late/Recession)
    37|- Apply these to today's calls
    38|
    39|**C. Read vault for recent learnings:**
    40|```
    41|Essential:
    42|  ├── INDEX.md                       → open proposals, active techniques
    43|  ├── 06-Learnings/<most-recent>.md  → yesterday's learnings
    44|  └── daily_review_YYYY-MM-DD.md     → yesterday's review (if exists)
    45|
    46|Conditional:
    47|  ├── 03-Factors/<factor>.md         → for factors with directional scores
    48|  └── 02-Backtests/                  → if using a new technique today
    49|```
    50|
    51|**D. Use SME Signal Synthesis** (section ④):
    52|1. Start with core bias from pre_market.json
    53|2. Modulate with vault factor accuracy (SME Rule 3)
    54|3. Apply portfolio context (SME Rule 4)
    55|4. Resolve conflicts (SME Rule 5)
    56|5. Risk-size each call (SME Risk Management)
    57|
    58|And produces **stock-specific BUY/SELL/HOLD calls with entry zones**, not just a market bias.
    59|
    60|## Architecture
    61|
    62|```
    63|  Google Sheet
    64|   ├── Portfolio           (read: holdings, P&L)
    65|   ├── Prediction Log      (read: yesterday's accuracy)
    66|   ├── Factor Performance  (read: factor reliability trends)
    67|   ├── Learning Log        (read: open learnings)
    68|   ├── New Picks           (read: watchlist)
    69|   ├── Event Calendar      (read: upcoming catalysts)
    70|   ├── Research Log        (read: past calls and outcomes)
    71|   └── Trade Ideas         (write: today's calls)
    72|           │
    73|           ▼
    74|  Morning Agent (gpt-5.3-codex via openai-codex)
    75|           │
    76|           ├── yfinance    (fetch overnight data, stock prices)
    77|           ├── Signal engine output (pre_market.json for bias)
    78|           └── Sheets API  (read tabs + write Trade Ideas)
    79|           │
    80|           ▼
    81|         Telegram — stock-specific calls (7:30 AM IST)
    82|```
    83|
    84|## Input Data Sources
    85|
    86|### 1. Signal Engine Output (read from pre_market.json)
    87|The 7AM no_agent script has already run and produced:
    88|- Market bias (BULLISH/BEARISH/NEUTRAL)
    89|- Confidence score
    90|- Factor breakdown (crude, USD/INR, VIX, Asian peers, etc.)
    91|- Market context string
    92|
    93|### 2. Google Sheet Tabs
    94|- **Prediction Log** — yesterday's signal verification (was bias correct?)
    95|- **Factor Performance** — which factors have been reliable recently
    96|- **Learning Log** — active learnings that affect today's decisions
    97|- **Portfolio** — current holdings with P&L and stop losses
    98|- **New Picks** — watchlist candidates
    99|- **Event Calendar** — upcoming results, board meetings, ex-dates
   100|- **Research Log** — past research calls and their current status
   101|
   102|### 3. Overnight Data via yfinance
   103|Fetch fresh:
   104|- Nifty futures / Gift Nifty (via SGX Nifty approximation)
   105|- Asian market open (Nikkei, Hang Seng)
   106|- US futures (S&P 500)
   107|- Crude Oil (Brent)
   108|- USD/INR
   109|- DXY
   110|- India VIX
   111|- All portfolio stock prices (for pre-market levels)
   112|
   113|## Output: Stock-Specific Calls
   114|
   115|Generate 3-5 actionable calls:
   116|
   117|### Call Types
   118|| Type | Meaning | Requires |
   119||------|---------|----------|
   120|| **BUY** | Strong entry today | Entry zone, target, SL, conviction |
   121|| **ADD** | Accumulate on dips | Dip price, target, SL |
   122|| **HOLD** | Hold existing position | Stop loss level, rationale |
   123|| **SELL** | Exit today | Exit zone, rationale |
   124|| **WATCH** | Monitor, don't act | Trigger price, rationale |
   125|
   126|### Call Format
   127|Each call must include:
   128|- **Symbol** (NSE ticker)
   129|- **Direction** (BUY / ADD / HOLD / SELL / WATCH)
   130|- **Entry Zone** (price range for BUY/ADD)
   131|- **Target Price** (profit zone)
   132|- **Stop Loss** (exit if breached)
   133|- **Conviction** (1-10)
   134|- **Thesis** (1-2 sentences linking to signal data + overnight context)
   135|- **Time Horizon** (intraday / swing / positional)
   136|
   137|## Telegram Report Format
   138|
   139|```
   140|━━━ NSE PRE-MARKET CALLS — May 22 ━━━
   141|
   142|📊 Market Context
   143|   Global: US closed flat | Asia mixed | Crude $105.46 (-5.2%)
   144|   India: VIX 18.44 | USD/INR 96.57 | Bias: MILD BULLISH (4/10)
   145|
   146|📌 Today's Calls
   147|
   148|🟢 **BUY RELIANCE** @ 1350-1365
   149|   🎯 Target: 1420 | 🛑 SL: 1320
   150|   Conviction: 7/10 | Horizon: Swing
   151|   └ Crude drop supports OMCs, RSI oversold (33), yesterday's 
   152|     research confirmed strong fundamentals
   153|
   154|⚪ **HOLD TCS** @ 2320-2340
   155|   🛑 SL: 2280 (below SMA-50)
   156|   Conviction: 5/10
   157|   └ IT sector mixed, waiting for clarity on US Fed stance
   158|
   159|🔴 **SELL WHIRLPOOL** @ 860+
   160|   🎯 Target: 820 | 🛑 SL: 880
   161|   Conviction: 8/10 | Horizon: Intraday
   162|   └ Deal collapse news, RSI 19 (overbought reversal risk)
   163|
   164|━━━ SIGNAL CONTEXT ━━━
   165|📈 Yesterday: NEUTRAL → NEUTRAL ✅ (3/3 this week)
   166|🔥 Crude Oil 3/3 accurate | USD/INR 3/3 consistent bearish
   167|💡 Learnings: VIX threshold too high (22 vs current 18)
   168|
   169|━━━ WATCHLIST ━━━
   170|👀 ADVENZYMES — nearing SMA-50 support
   171|👀 AFCONS — strong buy from yesterday, check opening price
   172|```
   173|
   174|## Tone & Style
   175|
   176|- **Confident but realistic** — signal says what it says, with caveats
   177|- **Action-oriented** — every call has an entry price, target, SL
   178|- **Data-backed** — each thesis references signal data or overnight context
   179|- **Concise** — scannable in 10 seconds, readable in 30
   180|
   181|## Pitfalls
   182|
   183|- **Gift Nifty data is an estimate**, not a real ticker. The 7AM script approximates it from Nifty. Flag this as "estimated" if used.
   184|- **Overnight data can change** between 7AM and 9:15AM market open. Suggest confirming calls in first 15 min of trading.
   185|- **VIX may not trigger** if threshold (22) is too high. Cross-check actual VIX level. See VIX regime thresholds in `references/signal-data-contracts.md`.
   186|- **Never promise returns.** Use "signals suggest" / "indicates" / "points to" — never "will go up."
   187|- **Codex OAuth must be connected.** Same as the evening agent.
   188|- **The 7AM script runs first** — the morning agent reads its output. If the script fails, note "No fresh signal data" and work from yesterday's close data.
   189|- **Signal accuracy context may be stale.** `signal_history.json` requires Phase 2b writes from the evening orchestrator. If last verified entry is >3 days old, note "Accuracy data stale — last verified: [date]" in report. See `references/signal-data-contracts.md`.
   190|
   191|## Execution Guardrails (Operational)
   192|
   193|- **Read/Write Sheets via Google API when helper scripts are absent.** If no dedicated morning script exists, use `~/.hermes/google_token.json` with Sheets API directly and still complete all tab reads + Trade Ideas write.
   194|- **Sheet bootstrap rule (no guessing):** if sheet metadata is not explicitly passed in the prompt, first check the NSE umbrella skills/references for the canonical Sheet ID and token path, then use those values directly.
   195|- **Always verify all required tabs were read** by confirming headers/row counts for: Portfolio, Prediction Log, Factor Performance, Learning Log, New Picks, Event Calendar, Research Log, Trade Ideas.
   196|- **Symbol universe fallback rule:** build candidates from `Portfolio` + `New Picks` + recent `Research Log` symbols first; only then use a small liquid fallback basket.
   197|- **Unique-call rule:** final 3–5 calls must be **one row per unique symbol** (no duplicate symbol with conflicting directions in the same report).
   198|- **Trade Ideas write contract:** append a normalized 9-field row set (`Date, Symbol, Direction, Entry Zone, Target, Stop Loss, Conviction, Horizon, Thesis`) and verify success with returned `updatedRange/updatedRows`.
   199|- **Report integrity rule:** each call must include entry, target, SL, conviction, thesis tied to overnight/signal context, and explicit horizon — even for HOLD/WATCH.
   200|- **Post-open caution is mandatory:** include a one-line reminder to revalidate in first 15 minutes after open.
   201|
   202|## Hermetic Fallback (sheets unavailable)
   203|
   204|When the `pre_market.json` signal is available but Google Sheets is unreachable (expired token, wrong scopes, spreadsheet access denied), **do NOT abort** — generate the full report using only local data:
   205|
   206|1. **Signal data:** `~/.hermes/data/nse_signals/pre_market.json` (always available — produced by 7AM cron)
   207|2. **Signal history & accuracy:** `~/.hermes/data/nse_signals/signal_history.json` (read last 7-10 entries for factor accuracy, bias verification)
   208|3. **Learnings:** `~/.hermes/data/trading_research/06-Learnings/<today>.md` (or most recent)
   209|4. **Technical context:** fetch fresh via yfinance (stock prices, SMA20/SMA50, RSI) — this is the primary data source regardless of Sheets status
   210|5. **Symbol universe:** use a liquid Nifty 20-30 large-cap basket (top 10 NIFTY by sector weight if Portfolio unavailable):
   211|   - OMCs: RELIANCE, ONGC
   212|   - IT: TCS, INFY, WIPRO, HCLTECH
   213|   - Banks: HDFCBANK, SBIN, AXISBANK, KOTAKBANK
   214|   - Telecom: BHARTIARTL
   215|   - Auto: TATAMOTORS, MARUTI, M&M
   216|   - Pharma: SUNPHARMA, LUPIN
   217|   - Conglomerates: ADANIENT, TATAMOTORS
   218|   - FMCG: ITC, HITACHIAV, TATASTEEL
   219|   - NBFC: BAJFINANCE, ICICIBANK
   220|6. **Skip Sheets operations entirely** — no reads, no writes, no append.
   221|7. **Report the fallback** — append a one-line note: `📝 Sheets write failed — calls saved locally only.`
   222|8. **Still generate 3-5 calls** using signal context + yfinance technicals. The report quality should be nearly identical.
   223|