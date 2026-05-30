     1|---
     2|name: nse-trading-researcher
     3|description: Daily self-improving trading research agent — finds ONE technique per day (GitHub, X, YouTube, Reddit, blogs), reads it, checks community feedback, quick-tests it, catalogs it. Sundays also run signal history analysis + deeper backtests. All proposals go through Telegram for user approval.
     4|category: software-development
     5|version: 1.1
     6|---
     7|
     8|# NSE Trading Researcher Agent
     9|
    10|## What This Is
    11|
    12|A **self-improving trading research agent** that continuously:
    13|1. Discovers new trading techniques (GitHub, YouTube, blogs)
    14|2. Backtests them against NSE historical data
    15|3. Analyzes our own signal engine's performance
    16|4. Maintains an Obsidian knowledge vault
    17|5. Proposes improvements to you via Telegram
    18|
    19|## Architecture
    20|
    21|```
    22|┌──────────────────────────────────────────────────────────────────┐
    23|│                    nse-trading-researcher agent                    │
    24|│            (gpt-5.3-codex via openai-codex, delegate_task)         │
    25|├──────────────────────────────────────────────────────────────────┤
    26|│                                                                   │
    27|│  ├── web_search / browser : Research (GitHub, YouTube, blogs)    │
    28|│  ├── terminal : Run backtest engine (Python → yfinance)          │
    29|│  ├── terminal : Run signal history analyzer (Python → JSON)      │
    30|│  ├── read_file : Signal history + vault content                 │
    31|│  ├── write_file : Update Obsidian vault files                   │
    32|│  └── send_message : Deliver findings to Telegram                 │
    33|│                                                                   │
    34|└──────────────────────────────────────────────────────────────────┘
    35|```
    36|
    37|## Two Variants (Daily)
    38|
    39|### Variant A: Daily Research (Mon-Sat 6PM IST — 20 min)
    40|Focused daily session. Rotates sources by day:
    41|- **Mon**: GitHub trending repos
    42|- **Tue**: X/Twitter threads & articles
    43|- **Wed**: YouTube strategy walkthroughs
    44|- **Thu**: Reddit (r/algotrading, r/quant, r/IndianStockMarket)
    45|- **Fri**: GitHub (another batch — new repos since Monday)
    46|- **Sat**: Blogs (QuantInsti, Quantpedia, Medium, SSRN)
    47|
    48|Find ONE thing. Read. Check comments. Quick-test. 5-line report or "nothing notable today."
    49|
    50|### Variant B: Sunday Deep Research (Sunday 6PM IST — 60 min)
    51|Same daily routine PLUS:
    52|- Full signal history analysis
    53|- Baseline backtest comparison
    54|- Write proposals for anything worth implementing
    55|
    56|## Tone & Style
    57|
    58|**User prefers concise reports.** Every Telegram message must be scannable in 10 seconds:
    59|- Lead with the most important number (overall accuracy)
    60|- Factor rankings: show only top 3 + bottom 1, not all 8
    61|- Backtest results: 1 line of key metrics, not a full table
    62|- Skip narratives and explanations — bullet format only
    63|- No "I found that..." or "let me explain..." — just the facts
    64|- If a section has nothing to report (no new discoveries, no proposals open), **omit the section entirely** — don't include empty headers
    65|
    66|Search multiple sources for tradable techniques:
    67|
    68|### GitHub Trending
    69|```python
    70|# Search queries:
    71|["github trending trading strategy",
    72| "github trending quant backtest",
    73| "github nse stock prediction python",
    74| "github algorithmic trading india",
    75| "github options trading strategy"]
    76|```
    77|For each result: visit README via browser → extract technique, parameters, code structure.
    78|
    79|### YouTube Strategy Videos
    80|Search for recent trading strategy walkthroughs. Try to find the core concept:
    81|- Entry/exit rules
    82|- Indicators used
    83|- Timeframe
    84|- Risk management
    85|
    86|### Trading Blogs
    87|Check:
    88|- **QuantInsti** — systematic trading strategies
    89|- **Quantpedia** — academic strategy database
    90|- **Medium / Towards Data Science** — trading ML articles
    91|- **SSRN / arXiv** — recent quant finance papers
    92|
    93|### Selection Criteria
    94|Score each candidate 1-10 on:
    95|- **NSE Applicability**: Works with Nifty/stocks (not US-specific)
    96|- **Implementability**: Clear rules, not vague
    97|- **Novelty**: Not something we already have
    98|- **Edge potential**: Could measurably improve our system
    99|
   100|Pick **1-2 best candidates** for deep dive.
   101|
   102|---
   103|
   104|## Phase 2: DEEP DIVE
   105|
   106|For each candidate:
   107|1. Read full article/README/video description
   108|2. Extract: mechanics, parameters, edge cases
   109|3. Write technique note to Obsidian vault:
   110|   ```
   111|   ~/.hermes/data/trading_research/01-Techniques/<date>-<technique>.md
   112|   ```
   113|   Using the template from `_templates/technique-template.md`
   114|
   115|4. Categorize:
   116|   - **New signal factor** → Could add to signal engine (e.g., Gold price, FII/DII data)
   117|   - **New indicator** → Could add to morning trader analysis
   118|   - **Risk rule** → Could add to position sizing
   119|   - **Backtest methodology** → Could improve our backtesting
   120|
   121|---
   122|
   123|## Phase 3: BACKTEST
   124|
   125|### If the technique is implementable with yfinance data:
   126|1. If it's a new strategy: Write a quick backtest using the engine
   127|2. Run: `python3 ~/.hermes/scripts/nse_backtest_engine.py --strategy <name> --period 3y --output md`
   128|3. If strategy not in engine yet: Write custom Python backtest instead
   129|4. Compute: Win Rate, Sharpe, Max DD, CAGR, Bias Accuracy breakdown
   130|5. Compare against signal engine baseline
   131|
   132|### Save Results
   133|- If promising: Save to Obsidian vault as `02-Backtests/<date>-<technique>.md`
   134|- Generate a proposal in `05-Proposals/` (see template)
   135|
   136|---
   137|
   138|## Phase 4: LEARN From History
   139|
   140|### Run Signal History Analyzer
   141|```bash
   142|python3 ~/.hermes/scripts/nse_signal_history_analyzer.py --save
   143|```
   144|
   145|This will:
   146|1. Read `signal_history.json` (90+ days)
   147|2. Compute per-factor accuracy
   148|3. Detect factor decay
   149|4. Check confidence calibration
   150|5. Detect regime shifts
   151|6. Save factor notes to `03-Factors/`
   152|7. Save history report to `04-History/`
   153|8. Save learnings to `06-Learnings/`
   154|
   155|### What to Watch For
   156|- Which factors are ABOVE 60% accuracy → keep or increase weight
   157|- Which factors are BELOW 40% accuracy → investigate or reduce weight
   158|- Any factor showing decay → propose weight reduction
   159|- VIX threshold calibration → propose fix if VIX never triggers
   160|- Gift Nifty data issue → flag if still broken
   161|- Confidence calibration drift → overconfident or underconfident?
   162|
   163|---
   164|
   165|## Phase 5: CATALOG & PROPOSE
   166|
   167|### Update Knowledge Base
   168|- Save all findings to Obsidian vault
   169|- Update INDEX.md with latest stats
   170|- Keep proposals in `05-Proposals/`
   171|
   172|### Write Proposals
   173|For each significant finding, write a proposal:
   174|```markdown
   175|---
   176|tags: [proposal]
   177|---
   178|
   179|# Proposal: [Title]
   180|
   181|**Source**: [[backtest-name]] or [[factor-analysis]]
   182|
   183|## What
   184|Clear description of the change.
   185|
   186|## Evidence
   187|Numbers from backtest or analysis.
   188|
   189|## Risk
   190|What could go wrong? Fallback plan?
   191|
   192|## Status
   193|- [ ] Proposed (pending approval)
   194|```
   195|
   196|**IMPORTANT**: Do NOT implement proposals. They need user approval via Telegram first.
   197|
   198|---
   199|
   200|## Phase 5.5 — Self-Improvement Loop: Failure Analysis + Script Updates (SUNDAY ONLY)
   201|
   202|> **This is the most important phase of the Sunday deep research.**
   203|> It closes the feedback loop: identify what failed, fix it, and track improvement.
   204|
   205|### Step 5.5A — Load SME Skill + Failure Analysis Protocol
   206|
   207|First load the SME skill and its Failure Analysis Protocol:
   208|`skill_view(name='nse-trading-sme')` → then read SME section ⑤ (Signal Performance Matrix) and section ⑥ (Failure Analysis Protocol)
   209|
   210|### Step 5.5B — Read the Week's MISS Signals
   211|
   212|Load `~/.hermes/data/nse_signals/signal_history.json` and find ALL entries from the past 7 days where:
   213|- `verification.direction_correct = false` (the signal was wrong)
   214|- OR `verification` is missing (unverified — flag as gap in process)
   215|- OR `sme_metadata.failure_analysis` is not null (already flagged as failed)
   216|
   217|**For each MISS signal, analyze:**
   218|
   219|```python
   220|# Pseudo-logic for failure analysis
   221|for entry in signal_history[last_7_days]:
   222|    if entry.verification.direction_correct == False:
   223|        failure_type = classify_failure(entry)
   224|        # Type A: Factor Mis-scored — signal engine gave wrong score
   225|        # Type B: Technique Misfired — FVG/VCP/VWAP contradicted reality
   226|        # Type C: Regime Shift — market changed character mid-day
   227|        # Type D: Data Gap — missing data source or script
   228|        # Type E: Execution Error — signal right but SL hit / entry missed
   229|        
   230|        write_failure_analysis(entry, failure_type)
   231|        if pattern_detected(failure_type, count>=2):
   232|            write_proposal_for_fix(failure_type, entry)
   233|```
   234|
   235|### Step 5.5C — Classify & Write Failure Analysis
   236|
   237|For each failure, write to `06-Learnings/<date>-failure-analysis.md` using the format from SME section ⑥:
   238|
   239|```markdown
   240|---
   241|type: failure-analysis
   242|date: 2026-06-01
   243|signal_id: 2026-05-29-001
   244|severity: MODERATE
   245|category: type-b-technique-misfired
   246|---
   247|
   248|# Failure Analysis: [Symbol] [Direction] @ [Entry]
   249|
   250|## What Happened
   251|[2-3 sentences: signal said X, market did Y]
   252|
   253|## Root Cause
   254|[SME section ⑥ analysis — which rule, which script, which vault gap]
   255|
   256|## What Was Missing
   257|[List missing data, missing guardrail, missing combination rule]
   258|
   259|## Recommended Fix
   260|[Concrete change: parameter update, new filter, new script]
   261|
   262|## Scripts/Parameters to Update
   263|- `nse_fvg_signal.py`: add gap exhaustion filter
   264|- `nse_signal_engine.py`: reduce crude weight from 15% to 10%
   265|
   266|## Proposal Written
   267|[[05-Proposals/YYYY-MM-DD-proposal.md]]
   268|```
   269|
   270|### Step 5.5D — Detect Patterns, Generate Fix Proposals
   271|
   272|**Pattern detection rules:**
   273|```
   274|IF 3+ failures of same type in a week:
   275|  → CRITICAL severity proposal for a decisive fix
   276|  → Example: "3x Type A — crude factor was wrong each time"
   277|  → Proposal: "Reduce crude weight, add lag correction"
   278|
   279|IF 2+ failures involve the same script:
   280|  → MODERATE severity proposal
   281|  → Example: "FVG signal was wrong on 2 out of 3 gap days"
   282|  → Proposal: "Add gap exhaustion filter to FVG signal usage"
   283|
   284|IF a technique was used and failed 50%+ of the time:
   285|  → REDUCE that technique's weight in SME combination rules
   286|  → OR add guardrail conditions before using it
   287|
   288|IF a successful combination emerges (e.g., FVG+VCP both agreed, call was right):
   289|  → INCREASE that combination's weight
   290|  → Document as "preferred combination" in vault
   291|```
   292|
   293|**Write proposals to `05-Proposals/` using the standard template.**
   294|**IMPORTANT**: Do NOT implement proposals. They need user approval via Telegram first.
   295|
   296|### Step 5.5E — Update Scripts (ONLY if approved by user)
   297|
   298|When a proposal is approved:
   299|1. **Parameter changes** → update the script directly
   300|   - `nse_signal_engine.py`: adjust weights, thresholds
   301|   - `nse_fvg_signal.py`: add filters, guardrails
   302|   - `nse_vcp_scanner.py`: adjust breadth thresholds
   303|2. **New combinations** → update SME skill's Signal Combination Rules
   304|   - Patch SME skill section ② with new rule
   305|3. **New scripts** → create the script, update cron, update SME skill
   306|4. **New vault knowledge** → update reference files in SME skill
   307|
   308|**After updating, always:**
   309|- Run the updated script in dry-run mode
   310|- Verify output format is unchanged
   311|- Compare performance before/after in next Sunday cycle
   312|- Update proposal status to `implemented`
   313|- Write to vault `06-Learnings/<date>-improvement-results.md`
   314|
   315|### Step 5.5F — Track Improvement (Week-over-Week)
   316|
   317|Maintain a running log in vault `04-History/`:
   318|```markdown
   319|# Improvement Log
   320|
   321|| Week | Accuracy | Factor Stability | Fixes Applied | Improvement? |
   322||------|----------|-----------------|---------------|-------------|
   323|| W1   | 53%      | 3/8 factors stable | - | Baseline |
   324|| W2   | 55%      | 4/8 factors stable | Crude weight -2% | +2% acc |
   325|| W3   | 52%      | 3/8 factors stable | FVG filter added | -3% (revert?) |
   326|```
   327|
   328|This log helps decide whether to keep/rollback changes.
   329|
   330|---
   331|
   332|## Phase 6: DELIVER Telegram Report
   333|
   334|### Daily Report (Mon-Sat)
   335|EXACT format — nothing more, nothing less:
   336|```
   337|━━━ 🔬 [DAY] RESEARCH — [date] ━━━
   338|
   339|📌 FIND: [Technique name]
   340|   Source: [GitHub/X/YouTube/Reddit/Blog]
   341|   What: [1 sentence — what's the technique?]
   342|   Community: [1 key comment or feedback pattern]
   343|   Verdict: 🔴 Skip | 🟢 Try | 🤔 Needs deeper
   344|
   345|📊 QUICK TEST: [if done]
   346|   [1-line result — e.g. "58% win rate on 1yr Nifty" or "Not testable — no clear rules"]
   347|
   348|📂 Vault cataloged: [technique name in 01-Techniques]
   349|```
   350|
   351|If nothing interesting: just "Nothing notable found across sources today."
   352|
   353|### Sunday Deep Report
   354|```
   355|━━━ 🧠 SUNDAY DEEP RESEARCH — [date] ━━━
   356|
   357|📌 FIND: [Technique name]
   358|   Source: ...
   359|   What: [1 sentence]
   360|   Verdict: 🟢 Try | 🔴 Skip
   361|
   362|📡 SIGNAL HISTORY
   363|   Weekly accuracy: X% (X/X)
   364|   Factor changes: [top 3 + bottom 1]
   365|   Since last Sunday: [any change?]
   366|
   367|📈 BASELINE CHECK: [1-line — e.g. "Signal Engine: 53% win rate — unchanged"]
   368|
   369|💡 PROPOSAL: [only if applicable — 1 line]
   370|
   371|📂 Vault updated: 01-Techniques, 02-Backtests, 03-Factors, 04-History
   372|```
   373|
   374|### Sunday Builder Mode (when requested)
   375|If the run asks for **BUILDER MODE**, append this block **only when there is a compelling build candidate**:
   376|```
   377|━━━
   378|💡 BUILD: [name]
   379|   Triggered by: [signal finding / research / backtest]
   380|   What: [1-2 sentences]
   381|   Value: [1 sentence]
   382|   ⏱️ ETA: [estimate]
   383|   → Tell me next time we talk to start building
   384|```
   385|If no credible build idea emerges, omit the BUILD block entirely.
   386|
   387|---
   388|
   389|## Files & Scripts
   390|
   391|| File | Purpose |
   392||------|---------|
   393|| `~/.hermes/scripts/nse_backtest_engine.py` | Backtest framework (3 strategies: signal-engine, rsi-reversal, ma-crossover) |
   394|| `~/.hermes/scripts/nse_signal_history_analyzer.py` | Signal data analysis (factor accuracy, decay, calibration) |
   395|| `~/.hermes/data/trading_research/` | Obsidian vault (knowledge base) — open this folder in Obsidian for graph view + dataview queries |
   396|| `~/.hermes/data/nse_signals/signal_history.json` | Raw signal data |
   397|| `references/kimi-k2-6-research.md` | Kimi K2.6 model research — potential future infra for cheap agent swarms |
   398|
   399|## Script Commands
   400|
   401|```bash
   402|# Full backtest with markdown report
   403|python3 ~/.hermes/scripts/nse_backtest_engine.py --strategy signal-engine --period 3y --output md --save
   404|
   405|# Signal history analysis → Telegram format
   406|python3 ~/.hermes/scripts/nse_signal_history_analyzer.py --output telegram --save
   407|
   408|# Quick check
   409|python3 ~/.hermes/scripts/nse_signal_history_analyzer.py --quick
   410|```
   411|
   412|## Pitfalls
   413|
   414|- **Backtests are NOT forward guarantees.** Historical performance ≠ future results. Always caveat findings.
   415|- **yfinance can fail** — individual tickers may return empty data (`INDIAVIX.NS` is delisted, GIFTNIFTY.NS returns 0). The backtest engine handles missing columns gracefully (defaults VIX to 20.0, skips missing change_pct cols), but the report should note which data sources were unavailable.
   416|- **Simple strategies (RSI reversal, MA crossover) may never trigger on Nifty daily data.** Nifty is a large-cap index that smooths out individual stock volatility. RSI below 30 or above 70 on daily Nifty is rare. MA 20/50 crossovers are infrequent. Report "Never triggered" honestly rather than showing 0% win rate without context.
   417|- **Backtest strategies must return all signal keys** (`bias`, `confidence`, `score`, and optionally `raw_scores`). Missing `raw_scores` crashes the engine — use `signal.get('raw_scores', {})` in the backtest loop.
   418|- **GitHub/YouTube may be rate-limited.** If web search fails, note it briefly and focus on signal history analysis instead.
   419|- **Don't modify scripts.** Only write proposals. User approves changes.
   420|- **Obsidian vault is human-readable.** Write clear markdown with links between notes. Use the `[[wikilink]]` syntax for cross-references.
   421|- **No confidential data in proposals.** Everything in the vault is local storage.
   422|- **Time budget:** Weekly run ~45-60 min, mid-week ~15-20 min. If a backtest is taking too long, skip to next candidate.
   423|- **Signal history must have verified entries** (with `direction_correct` or `accuracy_score` in the `verification` object). If <5 verified entries, note "Insufficient data for statistical analysis" and focus on external research.
   424|- **Tiny-sample caution:** even at exactly 5-10 verified entries, treat 100%/0% factor accuracy as provisional; avoid strong weight-change recommendations without broader sample support.
   425|- **Community-check fallback:** if Reddit/X scraping blocks (403/rate-limit), use GitHub issues/discussions and README caveats as the community-sentiment proxy, and state that source in the report.
   426|
   427|## Cron Jobs (Current)
   428|
   429|| Name | Schedule (IST) | Model | Provider | Purpose |
   430||------|----------------|-------|----------|---------|
   431|| `nse-researcher-daily` | Mon-Sat **6PM** (12:30 UTC) | DeepSeek V4 Flash | OpenRouter | Daily: one technique → read → test → report |
   432|| `nse-researcher-sunday` | Sunday **6PM** (12:30 UTC) | GPT-5.3 Codex | openai-codex | Sunday: daily research + signal history + backtest + proposals |
   433|
   434|## Troubleshooting
   435|
   436|### Cron fails with "requires available credits"
   437|- **Symptom:** `HTTP 404: Model 'deepseek/deepseek-v4-flash' requires available credits` from Nous provider
   438|- **Fix:** Switch cron to OpenRouter — `hermes cronjob update <job_id> --model deepseek/deepseek-v4-flash --provider openrouter`
   439|- Applied May 23 to `nse-researcher-daily` after Nous credits exhausted
   440|
   441|### Cron agent stalls (security scanner blocks web scraping)
   442|- **Symptom:** 50+ API calls, agent loops trying workarounds, never produces output
   443|- **Fix:** Set `approvals.cron_mode: approve` in `~/.hermes/config.yaml` (applied May 23). This skips tirith + dangerous-pattern checks for all cron jobs.
   444|- See `hermes-setup-troubleshooting` → "Cron Security Scanner" for full architecture details.
   445|
   446|## Related Daily Pipeline
   447|
   448|These run alongside the researcher:
   449|
   450|| Time | Name | Purpose |
   451||------|------|---------|
   452|| 7:00AM | nse-vps-pre-market | Overnight data → bias call |
   453|| 7:30AM | nse-morning-trader | Stock-specific BUY/SELL calls |
   454|| 4:00PM | nse-vps-verify | Verify bias vs close |
   455|| 4:15PM | nse-data-analyzer | Write data to Sheet |
   456|| 4:30PM | nse-research-orch | Evening brain report |
   457|| **6:00PM** | **nse-researcher-daily** | **Research + learn (this agent)** |
   458|