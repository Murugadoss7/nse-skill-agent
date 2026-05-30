     1|---
     2|name: nse-trading-sme
     3|description: The unified trading brain — SME-level knowledge + tool orchestration + Obsidian vault integration + signal synthesis + self-improvement loop. Loaded by all NSE agents to give them one shared intelligence.
     4|category: software-development
     5|version: 1.0
     6|---
     7|
     8|# 🧠 NSE Trading SME — The Unified Brain
     9|
    10|## What This Is
    11|
    12|The **single source of truth** for all trading intelligence in the NSE system. This skill is loaded by every NSE agent (morning trader, evening orchestrator, research agent) to give them:
    13|
    14|1. **SME-level trading knowledge** — technical analysis, fundamentals, Indian markets, global macro, sectors, risk management
    15|2. **Tool orchestration** — knows what each of the 17 scripts produces and how to combine their outputs
    16|3. **Obsidian vault integration** — reads accumulated knowledge before decisions, writes results back for compounding
    17|4. **Unified signal framework** — transforms scattered tool outputs into ONE BUY/SELL/HOLD call with reasoning chain
    18|5. **Self-improvement loop** — tracks every signal's outcome, analyzes failures, proposes script/combination changes
    19|
    20|## Architecture
    21|
    22|```
    23|         ┌──────────────────────────────────────────┐
    24|         │            LOADING AGENT                  │
    25|         │  (Morning Trader / Evening Orchestrator   │
    26|         │   / Researcher / Custom)                  │
    27|         └──────────────┬───────────────────────────┘
    28|                        │ loads this skill
    29|                        ▼
    30|         ┌──────────────────────────────────────────┐
    31|         │         NSE TRADING SME SKILL             │
    32|         ├──────────────────────────────────────────┤
    33|         │ ① SME Knowledge Base (this file)          │
    34|         │ ② Tool Orchestration Map                  │
    35|         │ ③ Vault Integration (read/write patterns) │
    36|         │ ④ Unified Signal Synthesis Framework      │
    37|         │ ⑤ Signal Performance Matrix + Feedback    │
    38|         │ ⑥ Failure Analysis Protocol               │
    39|         └──────────────┬───────────────────────────┘
    40|                        │
    41|          ┌─────────────┼─────────────┐
    42|          │             │             │
    43|          ▼             ▼             ▼
    44|   ┌──────────┐  ┌──────────┐  ┌──────────┐
    45|   │ 17       │  │ Obsidian │  │ signal_  │
    46|   │ Scripts  │  │ Vault    │  │ history  │
    47|   │ (tools)  │  │ (37+n)   │  │ .json    │
    48|   └──────────┘  └──────────┘  └──────────┘
    49|```
    50|
    51|## ① SME Knowledge Base
    52|
    53|### When to Load Reference Files
    54|
    55|The SKILL.md is always in the agent's context (loaded as the primary brain). For **detailed reference material**, load via `skill_view(name='nse-trading-sme', file_path='references/<file>.md')`:
    56|
    57|| When | Load | File |
    58||------|------|------|
    59|| Deep-dive technical analysis | Candlestick patterns, MA combos, RSI regimes, MACD, Bollinger Bands | `references/trading-knowledge-base.md` |
    60|| Fundamental stock analysis | Sector PE ranges, ratio cross-checks, earnings checklist | `references/trading-knowledge-base.md` |
    61|| Sector positioning | Sector-specific analysis templates (banks, IT, auto) | `references/trading-knowledge-base.md` |
    62|| Macro environment check | US10Y regime map, crude sensitivity, global indicator thresholds | `references/trading-knowledge-base.md` |
    63|| Writing signal metadata | signal_history.json extended schema, write rules | `references/signal-schema.md` |
    64|| Writing failure analysis | Template with evidence table, root cause, pattern detection | `templates/failure-analysis-template.md` |
    65|| Risk sizing | ATR volatility sizing tables, correlation matrix, SL adjustment | `references/trading-knowledge-base.md` |
    66|
    67|### Quick-Reference: Key Knowledge Areas
    68|
    69|**Technical Analysis Framework**
    70|```
    71|Trend (SMA/EMA/MACD/ADX)
    72|  → Determine primary trend (daily + weekly)
    73|  → If ADX > 25: strong trend, trade in trend direction
    74|  → If ADX < 20: ranging, use mean-reversion strategies
    75|  
    76|Momentum (RSI/Stochastic/CCI)
    77|  → RSI 30-70: neutral range, follow trend
    78|  → RSI < 30: oversold (potential bounce, but trend is your friend)
    79|  → RSI > 70: overbought (potential pullback, but strong trends stay overbought)
    80|  
    81|Volatility (Bollinger Bands/ATR)
    82|  → BB width contracting → breakout imminent (VCP pattern)
    83|  → ATR percentile > 80%: wide stops, reduced position size
    84|  → ATR percentile < 20%: tight stops, potential for expansion
    85|  
    86|Volume (OBV/VWAP/Volume Profile)
    87|  → Price confirming with volume = valid move
    88|  → Price up + Volume down = weak move, possible reversal
    89|  → VWAP: above = bullish bias, below = bearish bias
    90|  
    91|Candlestick Patterns
    92|  → Doji at resistance/support = indecision, possible reversal
    93|  → Engulfing = strong reversal signal (bullish/bearish)
    94|  → Hammer at support = bounce potential
    95|  → Shooting Star at resistance = rejection, possible drop
    96|```
    97|
    98|**Fundamental Analysis Framework**
    99|```
   100|Valuation Check (sector-relative):
   101|  PE vs sector median:
   102|    < 0.8x sector = undervalued (if earnings stable)
   103|    > 1.5x sector = overvalued (unless high growth)
   104|  PB < 1.5 for cyclical, < 3 for stable, < 5 for growth
   105|  EV/EBITDA < 10 = reasonable, < 7 = value
   106|
   107|Quality Check:
   108|  ROCE > 15% (consistent 5yr) = quality business
   109|  ROE > 12% (consistent 5yr) = good capital efficiency
   110|  D/E < 1 (ex-banks) = manageable debt
   111|  Interest Coverage > 3x = safe
   112|  OCF/FCF positive (consistent) = real earnings
   113|
   114|Growth Check:
   115|  Revenue CAGR > 10% (5yr) = growing
   116|  Profit CAGR > 15% (5yr) = compounding
   117|  If revenue growing but profit flat → margin pressure → check
   118|```
   119|
   120|**Indian Market Specifics**
   121|```
   122|FII/DII Flow:
   123|  FII selling + DII buying = market usually holds (DII absorbs)
   124|  FII selling + DII also selling = crash risk
   125|  Consecutive 5-day FII selling = defensive posture
   126|  FII buying > $500M/day = strong rally sign
   127|
   128|RBI Policy:
   129|  Rate cut cycle = bullish for Banks, Auto, Real Estate, NBFCs
   130|  Rate hold = stock-specific, focus on earnings
   131|  Rate hike = bearish for leveraged sectors, bullish for FMCG/IT
   132|  2-3 month lag between rate change and actual economic impact
   133|
   134|Budget Impact:
   135|  Capex push = Infrastructure, Construction, Cement, Steel
   136|  Rural focus = Agri, FMCG, Tractors, Fertilizers
   137|  Tax relief = Consumption, Auto, Consumer Durables
   138|  Defence spend = Defence, Aerospace
   139|
   140|Election Cycles:
   141|  Pre-election (6 months) = populist spending, market up
   142|  Post-election (3 months) = policy clarity, volatile
   143|  Stable majority = infrastructure + reform plays rally
   144|  Coalition = defensive sectors, gold, FMCG
   145|
   146|Monsoon:
   147|  Normal monsoon = Rural demand boost → Auto, FMCG, Agri
   148|  Deficient monsoon = Rural stress → avoid agri-linked
   149|  GST collections > ₹1.8L Cr = economic momentum strong
   150|```
   151|
   152|**Global Macro Interconnections**
   153|```
   154|US 10Y Yield → India:
   155|  < 4% = Risk-on for EM, FII flows into India
   156|  4-4.5% = Neutral, carry trade still works
   157|  > 4.5% = Risk-off, FII outflows from EM
   158|  > 5% = EM crisis mode, USD dominance
   159|
   160|Crude Oil → India:
   161|  < $80/bbl = Positive for India (import bill down, CAD narrows)
   162|  $80-100 = Neutral/manageable
   163|  > $100 = Negative (CAD widens, inflation up, RBI constrained)
   164|  > $120 = Crisis (rupee weakens, fuel subsidies strain fiscal)
   165|  Impact order: OMCs > Aviation > Paints > Tyres > FMCG
   166|
   167|DXY (Dollar Index):
   168|  < 100 = Strong EM, FII flows to India
   169|  100-104 = Neutral EM
   170|  > 104 = USD strength, EM outflows
   171|  > 108 = EM stress, capital flight to USD
   172|
   173|Fed Rate Cycle → RBI:
   174|  Fed cut → RBI follows (lag 1-3 months)
   175|  Fed hold → RBI independent if domestic inflation under control
   176|  Fed hike → RBI follows or rupee depreciates (worse)
   177|```
   178|
   179|**Sector Rotation Playbook**
   180|```
   181|EARLY CYCLE (RBI cut cycle, GDP accelerating):
   182|  LEAD: Banks, Auto, Real Estate, Consumer Durables
   183|  LAG: IT, Pharma, FMCG, Gold
   184|  Best trades: HDFCBANK, MARUTI, DLF, TITAN
   185|
   186|MID CYCLE (Stable growth, moderate inflation):
   187|  LEAD: IT, Pharma, FMCG, Healthcare
   188|  LAG: Commodities, Energy, Utilities
   189|  Best trades: TCS, SUNPHARMA, ITC, DIVISLAB
   190|
   191|LATE CYCLE (Inflation high, rates peaking):
   192|  LEAD: Energy, Commodities, Utilities, Metals
   193|  LAG: Banks, Auto, Real Estate (rate-sensitive)
   194|  Best trades: ONGC, RELIANCE, TATASTEEL, NTPC
   195|
   196|RECESSION (GDP slowing, earnings downgrades):
   197|  DEFENSIVE: Pharma, FMCG, IT, Gold
   198|  AVOID: Banks, Auto, Real Estate, Metals
   199|  Best trades: CIPLA, HINDUNILVR, INFY, GOLDBEES
   200|
   201|HIGH INFLATION:
   202|  LEAD: Banks (NIM expansion), Energy, Commodities, Gold
   203|  LAG: Auto (demand destruction), Consumer (margin pressure)
   204|
   205|LOW INFLATION / DEFLATION:
   206|  LEAD: IT, Pharma, Consumer (cost + margin expansion)
   207|  LAG: Banks (NIM compression), Commodities
   208|```
   209|
   210|**Risk Management (Non-Negotiable)**
   211|```
   212|Position Sizing (per trade):
   213|  Conviction 8-10: max 10% of capital
   214|  Conviction 6-7: max 5% of capital
   215|  Conviction 4-5: max 3% of capital
   216|  Conviction < 4: skip or max 1%
   217|
   218|Portfolio Limits:
   219|  Single stock: max 15% of portfolio
   220|  Single sector: max 30% of portfolio
   221|  Max 8-12 positions (diversified)
   222|  Max 3 simultaneous intraday positions
   223|
   224|Stop Loss Rules:
   225|  Intraday: 0.5-1% from entry
   226|  Swing (1-5 days): 2-3% from entry
   227|  Positional (weeks): 5-8% or below key SMA-50/EMA-50
   228|  Never move SL wider after entry (only tighten)
   229|  If SL hit twice on same stock, delist for 1 month
   230|
   231|Drawdown Management:
   232|  Portfolio down 5%: reduce position sizes by 20%
   233|  Portfolio down 10%: stop trading, review all positions
   234|  Portfolio down 15%: cash out, only defensive holds
   235|  After recovery: step in gradually over 2 weeks
   236|```
   237|
   238|## ② Tool Orchestration Map
   239|
   240|### All 17 Scripts — What They Do & When to Use Them
   241|
   242|**Signal Generators (use in morning + evening)**
   243|
   244|| Script | What It Produces | Use When | Key Data |
   245||--------|-----------------|----------|----------|
   246|| `nse_signal_engine.py` | Core bias + 8-factor breakdown | ALWAYS — primary signal | JSON at `signal_history.json` |
   247|| `nse_vps_scanner.py` | Fresh pre-market data + bias | ONLY at 7AM cron | `pre_market.json` |
   248|| `nse_fvg_signal.py` | FVG factor score (-2 to +2) | Daily after market open | Run `--json` for factor |
   249|| `nse_vcp_scanner.py` | VCP count + breadth | Weekly/Swing analysis | Run `--universe nifty50` |
   250|| `nse_volatility_regime.py` | Regime detection (L/N/H/E) | Daily before calls | Run `--history` |
   251|| `nse_vwap_strategy.py` | VWAP cross signal | Intraday check | Import module |
   252|
   253|**Analysis Engines (use in evening + research)**
   254|
   255|| Script | What It Produces | Use When | Key Data |
   256||--------|-----------------|----------|----------|
   257|| `nse_backtest_engine.py` | Strategy backtest metrics | Sunday deep research | Run `--strategy X --period 3y` |
   258|| `nse_signal_history_analyzer.py` | Factor decay + calibration | Sunday + weekly check | Run `--save` writes to vault |
   259|| `nse_prediction_analyzer.py` | Accuracy tracking | Runs at 4:15PM daily | Sheet tabs + local data |
   260|
   261|**Portfolio Scripts (use in evening + Sunday)**
   262|
   263|| Script | What It Produces | Use When | Key Data |
   264||--------|-----------------|----------|----------|
   265|| `nse_portfolio_review.py` | Multi-factor position scoring | Evening review | Sheet tab "Portfolio" |
   266|| `nse_portfolio_drift.py` | Allocation deviation | Sunday | drift report |
   267|
   268|**Context Scripts (use as needed)**
   269|
   270|| Script | What It Produces | Use When | Key Data |
   271||--------|-----------------|----------|----------|
   272|| `nse_macro_monitor.py` | Economic indicators | Macro check (paused cron) | Sheet tab |
   273|| `nse_ownership_scanner.py` | Insider transactions | Position review (paused cron) | Sheet tab |
   274|
   275|**Verification (already cron-scheduled)**
   276|
   277|| Script | What It Produces | Use When |
   278||--------|-----------------|----------|
   279|| `nse_vps_verify.py` | Bias vs actual comparison | 4PM daily |
   280|| `nse_vps_weekly.py` | Weekly outlook | Sunday 7:30PM |
   281|
   282|### Signal Combination Rules
   283|
   284|**How to combine multiple signals into ONE call:**
   285|
   286|```
   287|Rule 1: Core Bias (signal_engine) is the FOUNDATION
   288|  → Always start with the 8-factor bias as baseline
   289|  → Unless: volatility regime is EXTREME → reduce weight 50%
   290|
   291|Rule 2: Technique Signals MODULATE the core bias
   292|  ┌────────────────┬──────────┬──────────┬──────────┐
   293|  │ Core Bias      │ FVG      │ VCP      │ VWAP     │
   294|  ├────────────────┼──────────┼──────────┼──────────┤
   295|  │ BULLISH +1.0+  │ +FVG+2   │ +VCP yes │ +VWAP+   │ → STRONG BUY (9/10)
   296|  │ BULLISH +0.5   │ +FVG+1   │ +VCP yes │ neutral  │ → BUY (7/10)
   297|  │ BULLISH +0.5   │ +FVG-1   │ no VCP   │ -VWAP-   │ → HOLD/WATCH (5/10)
   298|  │ NEUTRAL        │ +FVG+2   │ +VCP yes │ neutral  │ → WATCH (4/10)
   299|  │ BEARISH -1.0   │ no conf  │ no VCP   │ -VWAP-   │ → SELL (8/10)
   300|  └────────────────┴──────────┴──────────┴──────────┘
   301|
   302|Rule 3: Vault Knowledge overrides default weightings
   303|  → If vault says "FVG accuracy dropped to 48% → reduce FVG weight"
   304|  → If vault says "Crude factor 3/3 accurate → increase crude weight"
   305|  → If vault says "VIX below 16 regime → widen SL by 0.5%"
   306|
   307|Rule 4: Portfolio Context ADJUSTS the call
   308|  → Already holding 5% of stock → adjust to HOLD not fresh BUY
   309|  → Sector at 28% (near 30% limit) → skip additional same-sector BUY
   310|  → Stock down 8% from entry → check SL, consider SELL
   311|
   312|Rule 5: Conflicting Signals → resolve via hierarchy
   313|  ┌─────────────────────────────────────────┐
   314|  │ Priority: Macro > Technical > Technique │  
   315|  │                                         │
   316|  │ IF crude says BEARISH (-2) AND          │
   317|  │    FVG says BULLISH (+2):               │
   318|  │ → Weight by vault factor accuracy       │
   319|  │ → If crude 3/3 accurate = side with     │
   320|  │   crude (BEARISH bias, FVG is false     │
   321|  │   positive)                             │
   322|  │ → If FVG 5/5 accurate = side with FVG   │
   323|  │   (crude signal fading in accuracy)     │
   324|  └─────────────────────────────────────────┘
   325|```
   326|
   327|## ③ Obsidian Vault Integration
   328|
   329|### Read Patterns (what to load before making calls)
   330|
   331|```
   332|BEFORE morning calls (7:30AM):
   333|  Load: 06-Learnings/<most-recent>.md
   334|    → What did we learn yesterday? Any active warnings?
   335|  Load: 03-Factors/<factor>.md for factors with directional scores
   336|    → Which factors are currently accurate vs fading?
   337|  Load: INDEX.md
   338|    → Check open proposals, active techniques under test
   339|
   340|BEFORE evening calls (4:30PM):
   341|  Load: 06-Learnings/<today>.md (if exists)
   342|    → Today's learnings from analysis
   343|  Load: 02-Backtests/ for any technique used in today's call
   344|    → Does the backtest support this call?
   345|  Load: 04-History/<recent>.md
   346|    → What were last week's accuracy patterns?
   347|  Load: 05-Proposals/ active proposals
   348|    → Is there an approved change we should be using?
   349|
   350|BEFORE research (6PM):
   351|  Load: INDEX.md full
   352|    → Overview of what's cataloged and pending
   353|  Load: 03-Factors/ all
   354|    → Complete factor analysis for the week
   355|  Load: 05-Proposals/ open
   356|    → What needs user approval?
   357|
   358|BEFORE ANY call:
   359|  Quick-check INDEX.md for:
   360|    - Open proposals (may change methodology)
   361|    - Active techniques under test
   362|    - Recent learnings (lessons from last session)
   363|```
   364|
   365|### Write Patterns (what to save after decisions)
   366|
   367|```
   368|AFTER evening orchestrator (4:30PM):
   369|  WRITE: research_log_YYYY-MM-DD.md
   370|    → All calls made with: symbol, direction, entry, target, SL, conviction
   371|    → Reasoning chain: which tools agreed/disagreed, what vault said
   372|  WRITE: learning_log_YYYY-MM-DD.md
   373|    → Any new learnings: factor performance, regime observations, mistakes
   374|    → Category: [factor-precision] [regime-change] [script-bug] [new-pattern]
   375|    → Severity: CRITICAL / MODERATE / LOW
   376|    → Root cause + recommended fix
   377|
   378|AFTER signal verification (4PM):
   379|  WRITE: Update signal_history.json last entry
   380|    → Must add: actual.close, actual.change_pct, actual.bias
   381|    → direction_correct (boolean), accuracy_score (0-5)
   382|
   383|AFTER failure analysis:
   384|  WRITE: 05-Proposals/<proposal>.md
   385|    → What failed, what script/combination caused it
   386|    → Proposed fix, expected improvement
   387|  WRITE: 06-Learnings/<date>-failure-analysis.md
   388|    → Detailed root cause analysis
   389|```
   390|
   391|### Vault File Structure
   392|
   393|```
   394|~/.hermes/data/trading_research/
   395|├── INDEX.md                         ← Quick-reference hub (auto-updated)
   396|├── daily_review_YYYY-MM-DD.md       ← By agents
   397|├── research_log_YYYY-MM-DD.md       ← By orchestrator
   398|├── learning_log_YYYY-MM-DD.md       ← By orchestrator/researcher
   399|├── 01-Techniques/                   ← Cataloged techniques (by researcher)
   400|│   └── YYYY-MM-DD-technique.md
   401|├── 02-Backtests/                    ← Backtest results (by researcher)
   402|│   └── YYYY-MM-DD-backtest.md
   403|├── 03-Factors/                      ← Per-factor analysis
   404|│   ├── crude_oil.md
   405|│   ├── asian_peers.md
   406|│   ├── india_vix.md
   407|│   └── ... (1 per factor)
   408|├── 04-History/                      ← Signal performance history
   409|│   └── YYYY-MM-DD-signal-analysis.md
   410|├── 05-Proposals/                    ← Improvement proposals
   411|│   └── YYYY-MM-DD-proposal.md
   412|├── 06-Learnings/                    ← Lessons & failure analyses
   413|│   └── YYYY-MM-DD-learnings.md
   414|│   └── YYYY-MM-DD-failure-analysis.md
   415|├── 07-Reference/                    ← Methodology docs
   416|│   ├── backtest-methodology.md
   417|│   ├── metrics-definitions.md
   418|│   ├── glossary.md
   419|│   └── yfinance-tickers.md
   420|└── _templates/                      ← Templates for new entries
   421|```
   422|
   423|## ④ Unified Signal Synthesis Framework
   424|
   425|### The Signal Decision Tree
   426|
   427|```
   428|Input: All tool outputs + vault knowledge + portfolio + market data
   429|
   430|STEP 1 — Assess Environment
   431|├── Read macro regime (crude, USD/INR, VIX, DXY)
   432|├── Read volatility regime (ATR percentile)
   433|├── Read factor accuracy from vault (which factors are hot)
   434|├── Read market trend (weekly SMA-50, daily SMA-20)
   435|└── Output: Environment Scorecard
   436|
   437|STEP 2 — Read Tool Outputs
   438|├── Signal engine bias + factor breakdown
   439|├── FVG signal (if produced)
   440|├── VCP breadth (if produced)
   441|├── Volatility regime
   442|├── Portfolio positions + drift
   443|└── Output: Raw Signal Grid
   444|
   445|STEP 3 — Synthesize
   446|├── Apply Rule 1 (Core Bias Foundation)
   447|├── Apply Rule 2 (Technique Modulators)
   448|├── Apply Rule 3 (Vault Knowledge Override)
   449|├── Apply Rule 4 (Portfolio Context)
   450|├── Apply Rule 5 (Conflict Resolution)
   451|└── Output: Adjusted Signal Per Stock
   452|
   453|STEP 4 — Risk Size
   454|├── Apply position sizing rules
   455|├── Check portfolio limits
   456|├── Set stop losses based on ATR/volatility regime
   457|└── Output: Sized Calls
   458|
   459|STEP 5 — Package
   460|├── Call type (BUY/SELL/HOLD/WATCH)
   461|├── Entry zone, target, stop loss
   462|├── Conviction score (1-10)
   463|├── Reasoning chain (which tools, what vault said)
   464|├── Alternative scenario (what would invalidate this call)
   465|└── Output: FINAL SIGNAL
   466|```
   467|
   468|### Signal Format (unified across all agents)
   469|
   470|```json
   471|{
   472|  "signal_id": "2026-06-01-001",
   473|  "date": "2026-06-01",
   474|  "time": "07:30:00",
   475|  "agent": "morning-trader | evening-orch | research",
   476|  "environment": {
   477|    "macro_bias": "MILD_BULLISH",
   478|    "volatility_regime": "NORMAL",
   479|    "market_trend": "UP (daily SMA-20 > SMA-50)",
   480|    "vix_level": 16.19,
   481|    "crude": 91.7,
   482|    "usd_inr": 94.99,
   483|    "dxy": 98.94
   484|  },
   485|  "calls": [
   486|    {
   487|      "symbol": "RELIANCE",
   488|      "direction": "BUY",
   489|      "entry_zone": "1350-1365",
   490|      "target": 1420,
   491|      "stop_loss": 1320,
   492|      "conviction": 7,
   493|      "horizon": "swing",
   494|      "reasoning_chain": [
   495|        "core_bias: BULLISH (+0.5)",
   496|        "fvg_signal: BULLISH (+1) — FVG on daily, gap fill incomplete",
   497|        "vault_learnings: FVG was 74% accurate in last 30 days",
   498|        "vault_factor: Crude factor 3/3 accurate, crude falling supports OMCs",
   499|        "portfolio: Not currently holding, sector allocation OK"
   500|      ],
   501|