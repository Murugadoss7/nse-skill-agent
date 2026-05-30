     1|---
     2|name: nse-research-orchestrator
     3|description: Unified evening brain — reads ALL signal + portfolio + market data, makes informed BUY/HOLD/SELL calls, produces comprehensive post-analysis Telegram report with learnings.
     4|category: software-development
     5|version: 3.0
     6|---
     7|
     8|# NSE Evening Brain — Unified Post-Market Intelligence
     9|
    10|> **⚠️ THIS SKILL LOADS `nse-trading-sme` SKILL FIRST**
    11|> The SME skill provides: expert knowledge, tool orchestration map, obsidian vault integration,
    12|> signal synthesis framework, and self-improvement loop. Load it first before proceeding.
    13|
    14|## What This Is
    15|
    16|## What This Is
    17|
    18|The **central intelligence agent** that runs at 4:30 PM IST (market close). It is the SINGLE evening brain that:
    19|
    20|1. **Reads all data sources** — signal accuracy, factor performance, portfolio holdings, past research, event calendar
    21|2. **Fetches fresh market data** — yfinance for Nifty, stocks, macros (no more relying on stale script outputs)
    22|3. **Makes informed calls** — BUY/HOLD/SELL with price targets, factoring in signal accuracy trends
    23|4. **Generates ONE unified Telegram report** — signal post-analysis + factor temperature + research calls + learnings
    24|
    25|## Architecture
    26|
    27|```
    28|  Google Sheet
    29|   ├── Portfolio           (read: current holdings, P&L)
    30|   ├── Prediction Log      (read: was morning bias correct?)
    31|   ├── Factor Performance  (read: which factors are reliable?)
    32|   ├── Learning Log        (read + write: root causes, learnings)
    33|   ├── Daily Review Log    (read: past reviews)
    34|   ├── New Picks           (read: watchlist candidates)
    35|   ├── Event Calendar      (read: upcoming events)
    36|   ├── Research Log        (read + write: past + new calls)
    37|   └── Trade Ideas         (read: today's morning calls)
    38|           │
    39|           ▼
    40|  Evening Brain Agent (gpt-5.3-codex via openai-codex)
    41|           │
    42|           ├── yfinance    (fetch stock data, macro, ownership)
    43|           ├── Browser     (fetch news/sentiment if needed)
    44|           └── Sheets API  (read all tabs + write calls/learnings)
    45|           │
    46|           ▼
    47|         Telegram — ONE unified report (4:30 PM IST)
    48|```
    49|
    50|## What This Replaces
    51|
    52|| Cancelled Cron | Why |
    53||----------------|-----|
    54|| `nse-macro-monitor` (7:30AM) | Orchestrator fetches its own macro data via yfinance |
    55|| `nse-ownership-scan` (3:00PM) | Orchestrator checks insider data via yfinance directly |
    56|| `nse-post-analysis` (4:25PM) | Merged into this agent's Telegram report |
    57|
    58|## SME Skill Integration (Load Before Starting)
    59|
    60|> **CRITICAL:** Before any phase, load the `nse-trading-sme` skill via `skill_view(name='nse-trading-sme')`
    61|> to get the shared SME knowledge, tool orchestration map, vault patterns, and signal synthesis rules.
    62|
    63|### Step 0 — Load SME Knowledge + Vault Context
    64|
    65|**A. Load the SME skill:**
    66|1. `skill_view(name='nse-trading-sme')` — loads the full SME brain (knowledge, orchestration, vault patterns)
    67|2. Use SME section ① for expert knowledge reference during research
    68|3. Use SME section ② to determine which scripts to run/read
    69|4. Use SME section ③ for vault read/write patterns
    70|
    71|**B. Read Obsidian vault (always do this BEFORE making calls):**
    72|```
    73|Essential reads (always):
    74|  ├── INDEX.md                    → quick-reference: open proposals, active techniques, factor snapshot
    75|  ├── 06-Learnings/<today>.md     → today's learnings (if exists)
    76|  ├── 03-Factors/<factor>.md      → one per factor that had non-zero score today
    77|  └── daily_review_YYYY-MM-DD.md  → yesterday's review (most recent)
    78|
    79|Conditional reads:
    80|  ├── 02-Backtests/               → if using a technique (check its backtest result)
    81|  ├── 05-Proposals/               → check if any approved change affects today's methodology
    82|  └── 04-History/                 → if accuracy trend is unclear (cross-check 7+ days)
    83|```
    84|
    85|**C. Run/schedule the signal synthesis framework:**
    86|1. After loading all data, apply SME section ④ (Signal Decision Tree)
    87|2. After making calls, apply SME section ⑤ (write metadata to signal_history.json)
    88|3. Flag any suspicious calls for SME section ⑥ (Failure Analysis) follow-up
    89|
    90|### Phase 0 — SME Environment Assessment
    91|
    92|Before reading sheet data, first assess the trading environment using SME knowledge:
    93|
    94|1. **Macro context** (from `pre_market.json` and yfinance):
    95|   - Crude below/above $100? → SME Macro Interconnections
    96|   - USD/INR trending? → SME Indian Market Specifics (FII/DII flow)
    97|   - VIX regime? → SME VIX Regime Interpretation
    98|   - DXY above/below 104? → SME Global Macro (EM fund flows)
    99|
   100|2. **Volatility regime** (from SME Risk Management):
   101|   - Run `python3 ~/.hermes/scripts/nse_volatility_regime.py --history`
   102|   - Adjust position sizing based on ATR percentile
   103|
   104|3. **Sector positioning** (from SME Sector Rotation):
   105|   - Which phase of the cycle are we in? (Early/Mid/Late/Recession)
   106|   - Which sectors should lead/lag?
   107|   - Cross-check with today's portfolio holdings
   108|
   109|Log these assessments — they feed into every call's reasoning chain.
   110|
   111|### Phase 1 — Read ALL Sheet Data
   112|Read EVERY relevant tab:
   113|- **Portfolio** — holdings, entry prices, current P&L, stop losses
   114|- **Prediction Log** — last 7 days of morning bias vs actual, accuracy trend
   115|- **Factor Performance** — which factors (crude, USD/INR, VIX) are most reliable
   116|- **Learning Log** — past root causes, what was fixed, what to watch
   117|- **Daily Review Log** — past reviews
   118|- **New Picks** — stocks on watchlist
   119|- **Event Calendar** — upcoming results, board meetings, ex-dates
   120|- **Research Log** — past calls and outcomes
   121|- **Trade Ideas** — today's morning trade calls (if any)
   122|
   123|**Local fallback (sheets unavailable):** When Sheets calls fail, read from local files instead of aborting:
   124|- Signal accuracy history: `~/.hermes/data/nse_signals/signal_history.json`
   125|- Today's morning calls: `~/.hermes/data/nse_signals/morning_calls_YYYY-MM-DD.md`
   126|- Recent learnings: `~/.hermes/data/trading_research/learning_log_YYYY-MM-DD.md` (or most recent)
   127|- Yesterday's review: `~/.hermes/data/trading_research/daily_review_YYYY-MM-DD.md` (or most recent)
   128|- Symbol universe: hard-coded liquid basket (same as nse-morning-trader Hermetic Fallback)
   129|
   130|### Phase 2 — Calculate Signal Accuracy Summary
   131|From Prediction Log + Factor Performance tabs, compute:
   132|- Today's bias vs actual → correct or wrong?
   133|- Running accuracy (overall, by bias type, by confidence band)
   134|- Factor temperature — which factors are hot/cold
   135|- Confusion matrix (e.g., "bearish call → mild_bearish actual = close match")
   136|- Learning items triggered
   137|
   138|If Sheets Prediction Log is unavailable, read local fallback: `~/.hermes/data/nse_signals/signal_history.json`
   139|
   140|### Phase 2b — WRITE Signal Accuracy (CLOSE THE LOOP) ⚠️ MANDATORY
   141|
   142|After computing today's bias vs actual, **always write verified data to `~/.hermes/data/nse_signals/signal_history.json`**. This is the critical feedback loop. Sessions have gone 7+ days with blank accuracy data because this step was skipped.
   143|
   144|1. Load `~/.hermes/data/nse_signals/signal_history.json`
   145|2. Update last entry (today's date) with: `actual.close`, `actual.change_pct`, `actual.bias` (BULLISH/BEARISH/NEUTRAL), `direction_correct` (boolean), `accuracy_score` (0-5)
   146|3. Save file. Verify round-trip.
   147|
   148|Write to Sheets Prediction Log too if possible — but **do not wait for Sheets** to block the local write. The signal accuracy dashboard went blank in multiple sessions because this step was not mandatory.
   149|
   150|### VIX Regime Interpretation (integrate into Phase 2 analysis)
   151|
   152|VIX level ≠ safety indicator. Low VIX means corrections happen faster, not that they won't happen:
   153|- **VIX < 14:** "Dead calm" — corrections can be sharp and gap-driven; don't assume stability
   154|- **VIX 14-18:** "Quiet water" — routine intraday noise; oversold bounces work well; don't overtrade
   155|- **VIX 18-22:** "Normal volatility" — standard ranges; follow signals as usual
   156|- **VIX 22-28:** "Elevated" — wider ranges; tighten stops, scale positions
   157|- **VIX > 28:** "Storm" — risk-off regime; focus on capital preservation, reduce exposure
   158|
   159|Key lesson: VIX < 16 does NOT prevent 1.5%+ single-day drops. It means they happen faster and with less warning. Position sizing should account for occasional big moves even in calm regimes.
   160|
   161|### Phase 3 — Pick Stocks for Research
   162|Select 5-7 portfolio stocks. Prioritize:
   163|- Stocks with biggest P&L swings (gains or losses)
   164|- Stocks approaching events (earnings, ex-date)
   165|- Stocks with conflicting signals (bullish research but falling price)
   166|- Stocks from today's Trade Ideas that need follow-up
   167|
   168|### Phase 4 — Deep Research
   169|For each stock:
   170|- **Technical**: yfinance for RSI, SMA-5/20/50, support/resistance
   171|- **Fundamental**: PE, PB, market cap, sector comparison
   172|- **News**: Browser or web search for recent developments
   173|- **Ownership**: Check insider transactions via yfinance institutional data
   174|- **Macro fit**: How does the stock fit in current crude/USD/VIX environment?
   175|
   176|### Phase 5 — Make Calls using SME Signal Synthesis Framework
   177|
   178|**Apply the SME Signal Decision Tree (SME section ④):**
   179|
   180|```
   181|STEP 1 — Environment Scorecard (from Phase 0)
   182|STEP 2 — Raw Signal Grid (from all tools + vault)
   183|STEP 3 — Apply Combination Rules (SME section ②):
   184|  ├── Rule 1: Core Bias is FOUNDATION
   185|  ├── Rule 2: Technique Signals MODULATE (FVG, VCP, VWAP, etc.)
   186|  ├── Rule 3: Vault Knowledge OVERRIDES weights
   187|  ├── Rule 4: Portfolio Context ADJUSTS the call
   188|  └── Rule 5: Conflicting Signals resolve via hierarchy
   189|STEP 4 — Risk Size (SME section ① Risk Management)
   190|STEP 5 — Package into unified signal format
   191|```
   192|
   193|For each stock, produce:
   194|- **Decision**: BUY / HOLD / SELL / WATCH / ADD
   195|- **Entry Zone** (if BUY/ADD)
   196|- **Target Price** + Stop Loss (apply volatility regime adjustment from SME Risk Management)
   197|- **Conviction**: 1-10 (use SME combination rules for consistency)
   198|- **Reasoning Chain**: Link each decision back to:
   199|  - SME macro/environment assessment (Phase 0)
   200|  - Tool outputs (which scripts agreed/disagreed)
   201|  - Vault knowledge (what past learnings said)
   202|  - Signal combination rules applied
   203|- **Alternative Scenario**: What would invalidate this call?
   204|
   205|Also call `nse_vps_scanner.py` and `nse_fvg_signal.py` if you need additional signal data for the synthesis.
   206|
   207|Write to:
   208|- **Research Log** tab with all calls
   209|- **Learning Log** if any root cause or new insight
   210|- **Daily Review Log** for review entries
   211|
   212|### Phase 5b — Local File Fallback Writes (always execute)
   213|
   214|When Sheets are unavailable (token expired/revoked — common), write outputs to local markdown files in `~/.hermes/data/trading_research/`:
   215|- `research_log_YYYY-MM-DD.md` — all research calls with reasoning chain, alternative scenario
   216|- `learning_log_YYYY-MM-DD.md` — new learnings with category, severity, root cause, fix, status
   217|- `daily_review_YYYY-MM-DD.md` — daily review with signal verification, macro table, key observations, tomorrow's triggers
   218|
   219|**ALSO write SME metadata to signal_history.json:**
   220|Append (or update the last entry with) `sme_metadata`:
   221|```json
   222|"sme_metadata": {
   223|  "sme_techniques_used": ["FVG", "volatility_regime"],
   224|  "sme_tools_used": ["signal_engine", "fvg_signal", "vcp_scanner"],
   225|  "sme_vault_refs": ["FVG accuracy 74%", "Crude factor 3/3"],
   226|  "sme_conviction": 7,
   227|  "sme_horizon": "swing",
   228|  "failure_analysis": null,
   229|  "failure_root_cause": null,
   230|  "failure_proposal_ref": null
   231|}
   232|```
   233|
   234|These are read by:
   235|- Next day's morning trader (daily_review + learning_log → context for calls)
   236|- The evening orchestrator itself (check accuracy gap)
   237|- The Sunday failure analysis (read MISS signals)
   238|- Session-search for retrospective analysis
   239|- Self-improvement loop (SME section ⑤-⑥)
   240|
   241|**ALWAYS write these regardless of Sheets status.** They are the durable record. Never skip.
   242|
   243|### Phase 6 — Deliver ONE Unified Telegram Report
   244|
   245|Generate a SINGLE comprehensive message:
   246|
   247|```
   248|📊 **Evening Market Intelligence — May 22**
   249|
   250|━━━ SIGNAL POST-ANALYSIS ━━━
   251|🟢 Bias: MILD_BULLISH → Actual: MILD_BULLISH ✅ CORRECT
   252|   Nifty: +0.17% | Accuracy Score: 4.7/5
   253|
   254|📈 Season Stats: 3/3 (100%) | Last 3: 3/3 (100%)
   255|   🔥 Crude Oil: 3/3 | USD/INR: 3/3 | 🧊 VIX: 0/3
   256|
   257|━━━ RESEARCH CALLS ━━━
   258|🟢 BUY RELIANCE @ 1359 | Target: 1450 | SL: 1320
   259|   RSI 33 oversold + crude drop supports + strong buy signal
   260|   Conviction: 8/10
   261|
   262|⚪ HOLD TCS @ 2327 | Near SMA-50 support
   263|   IT sector mixed, wait for earnings trigger
   264|   Conviction: 5/10
   265|
   266|━━━ LEARNINGS ━━━
   267|💡 VIX threshold (22) too high for current 18-19 regime
   268|💡 Gift Nifty data source still broken (20% weight unused)
   269|
   270|━━━ TOMORROW'S WATCH ━━━
   271|🔭 Crude < $105, USD/INR > 96.60, Nifty support at 23500
   272|```
   273|
   274|## Key Differences from v1
   275|
   276|| v1 (old) | v2 (new) |
   277||----------|----------|
   278|| Relied on script-produced Sheet tabs for macro/ownership | Fetches its own data via yfinance |
   279|| Separate post-analysis agent for signal accuracy | Signal accuracy INCLUDED in this report |
   280|| Multiple Telegram messages per day | ONE unified evening message |
   281|| Didn't know if morning bias was correct | Reads Prediction Log → factors accuracy into calls |
   282|| Ran at 4:00 PM (before data was ready) | Runs at 4:30 PM (after verify + analyzer complete) |
   283|
   284|## Cron Job
   285|
   286|- **Job ID**: `58d56d3f026e`
   287|- **Name**: `nse-research-orch`
   288|- **Schedule**: `00 11 * * 1-5` (11:00 UTC = **4:30 PM IST**, weekdays)
   289|- **Model**: `gpt-5.3-codex` via `openai-codex` provider
   290|- **Skill**: `nse-research-orchestrator` (this skill)
   291|- **Delivery**: Telegram
   292|
   293|## Auth Architecture (Two Independent Systems)
   294|
   295|| Auth System | File | Scope | Recovery |
   296||-------------|------|-------|----------|
   297|| LLM Provider (openai-codex) | `~/.hermes/auth.json` | GPT-5.3-codex model access | See `hermes-setup-troubleshooting` |
   298|| Google Sheets API | `~/.hermes/google_token.json` + `google_client_secret.json` | Sheets read/write | See `references/google-sheets-oauth-recovery.md` |
   299|
   300|These are **completely independent**. Failure of one does not imply failure of the other. If Sheets calls return `invalid_grant` 400 errors, check `google_token.json` — the LLM provider auth may be fine.
   301|
   302|## Sheet Tabs Used
   303|
   304|| Tab | Read | Write | Purpose |
   305||-----|------|-------|---------|
   306|| Portfolio | ✅ | ❌ | Current holdings |
   307|| Prediction Log | ✅ | ❌ | Signal accuracy history |
   308|| Factor Performance | ✅ | ❌ | Factor reliability |
   309|| Learning Log | ✅ | ✅ | Root causes + learnings |
   310|| Daily Review Log | ✅ | ✅ | Daily review entries |
   311|| New Picks | ✅ | ❌ | Watchlist |
   312|| Event Calendar | ✅ | ❌ | Upcoming events |
   313|| Research Log | ✅ | ✅ | Store new calls |
   314|| Trade Ideas | ✅ | ❌ | Today's morning calls |
   315|| Cron Reference | ✅ | ❌ | Cron job documentation |
   316|
   317|## Reference Files
   318|
   319|- `references/nse-yfinance-ticker-format.md` — NSE stock ticker suffixes for yfinance
   320|- `references/google-sheets-oauth-recovery.md` — Recovery procedure when Google OAuth tokens are revoked (requires human browser auth)
   321|- `references/signal-data-contracts.md` — Cross-skill data contracts: signal_history.json format, pre_market.json format, morning_calls format, local fallback paths, VIX regime thresholds
   322|
   323|## Pitfalls
   324|
   325|- **NSE stocks need `.NS` suffix for yfinance.** Always append `.NS` for NSE stocks, `.BO` for BSE.
   326|- **Google Sheets writes are side-effects.** Wrap sheet API calls in try/except so a transient Google error doesn't kill the Telegram delivery.
   327|- **Google Sheets OAuth is SEPARATE from LLM provider auth.** The Sheets API uses Google OAuth2 (token at `~/.hermes/google_token.json`, client secret at `~/.hermes/google_client_secret.json`), NOT the LLM provider (openai-codex). If Sheets reads/writes fail with `invalid_grant` or `refresh_token` revoked, the LLM provider may be fine — these are two independent auth systems.
   328|- **Google OAuth revocation = no automatic recovery.** When `invalid_grant` fires with a revoked refresh token, `creds.refresh()` always fails. Only fix: human-driven browser OAuth re-auth. See `references/google-sheets-oauth-recovery.md` for the flow.
   329|- **Full Sheets outage (token expired + refresh revoked) → report without Sheet data.** If all Sheets calls fail, the agent should proceed with yfinance research using known portfolio tickers (from session history or hard-coded defaults from recent runs), and clearly flag in the report that Sheet-backed analysis (signal accuracy, past predictions, factor performance) is unavailable. Do not crash. See `references/signal-data-contracts.md` for local fallback paths.
   330|- **Market closed days**: On NSE holidays, data may be stale. Check if markets were open before making fresh calls.
   331|- **Prediction Log may have gaps** on holidays — don't assume daily entries.
   332|- **Factor Performance with <3 data points** is anecdotal, not statistical. Flag this in the report.
   333|- **Accuracy score is 0-5**, not 0-100. 5 = perfect match, 3 = close, 1 = completely wrong.
   334|- **Signal accuracy write (Phase 2b) is mandatory.** Never skip writing actual close data to `signal_history.json`. Sessions have gone 9+ days with blank accuracy because this was treated as optional.
   335|- **Low VIX ≠ safe.** VIX below 16 doesn't prevent 1.5%+ single-day drops — it means corrections happen faster. See Phase 2b VIX interpretation.
   336|