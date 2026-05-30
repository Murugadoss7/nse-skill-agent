# 🧠 NSE Skill Agent — Trading Intelligence System

A comprehensive NSE (National Stock Exchange of India) trading intelligence system combining **17 signal scripts**, **5 Hermes Agent skills**, and an **Obsidian knowledge vault** into one unified brain.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                 nse-trading-sme (SKILL)               │
│         The Unified Brain — loaded by all agents       │
│  ┌──────────────────────────────────────────────────┐ │
│  │ ① SME Knowledge Base │ ② Tool Orchestration Map  │ │
│  │ ③ Vault Integration  │ ④ Signal Synthesis        │ │
│  │ ⑤ Performance Matrix │ ⑥ Failure Analysis        │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────┘
                       │ loaded by
    ┌──────────────────┼──────────────────┐
    ▼                  ▼                  ▼
┌─────────┐    ┌──────────────┐   ┌──────────────┐
│ Morning │    │ Evening      │   │ Research     │
│ Trader  │    │ Orchestrator │   │ Agent        │
│ 7:30AM  │    │ 4:30PM       │   │ 6PM Daily    │
└─────────┘    └──────────────┘   └──────┬───────┘
                                         │ Sunday
                                    ┌────▼───────┐
                                    │ Failure    │
                                    │ Analysis   │
                                    │ Loop       │
                                    └────────────┘
```

## Skills (`skills/`)

| Skill | Purpose |
|-------|---------|
| `nse-trading-sme.md` | **The brain** — SME knowledge + orchestration + vault + signal synthesis + self-improvement |
| `nse-research-orchestrator.md` | Evening agent — reads all data, makes BUY/HOLD/SELL calls (loads SME skill) |
| `nse-morning-trader.md` | Pre-market agent — stock-specific calls by 7:30AM (loads SME skill) |
| `nse-trading-researcher.md` | Research agent — finds techniques, backtests, failure analysis (loads SME skill) |
| `nse-proactive-signal-scanner.md` | Signal engine — 8-factor bias model + weekly outlook |

## Scripts (`scripts/`)

| Category | Script | What It Does |
|----------|--------|-------------|
| **Signal** | `nse_signal_engine.py` | Core 8-factor bias engine (crude, USD/INR, VIX, peers, etc.) |
| | `nse_vps_scanner.py` | Pre-market scanner — fetches yfinance → runs signal engine |
| | `nse_fvg_signal.py` | Fair Value Gap factor (-2 to +2) |
| | `nse_vcp_scanner.py` | Volatility Contraction Pattern + market breadth |
| | `nse_volatility_regime.py` | ATR(14) regime detector (Low/Normal/High/Extreme) |
| | `nse_vwap_strategy.py` | VWAP crossover signals |
| **Analysis** | `nse_backtest_engine.py` | Generic backtesting framework (3+ strategies) |
| | `nse_signal_history_analyzer.py` | Factor decay, calibration drift, regime correlation |
| | `nse_prediction_analyzer.py` | Accuracy tracking + root cause analysis |
| **Portfolio** | `nse_portfolio_review.py` | Multi-factor position scoring |
| | `nse_portfolio_drift.py` | Allocation vs target deviation |
| **Context** | `nse_macro_monitor.py` | Economic indicators tracker |
| | `nse_ownership_scanner.py` | Insider transaction signals |
| **Verify** | `nse_vps_verify.py` | Morning bias vs actual close comparison |
| | `nse_vps_weekly.py` | Weekly outlook generation |

## Daily Pipeline (IST)

| Time | Job | What Happens |
|------|-----|-------------|
| 7:00AM | `nse-vps-pre-market` | Fetch overnight data, run 8-factor bias |
| 7:30AM | `nse-morning-trader` | Load SME skill + vault → stock-specific BUY/SELL/HOLD calls |
| 4:00PM | `nse-vps-verify` | Compare morning bias vs Nifty close |
| 4:15PM | `nse-data-analyzer` | Compute accuracy stats, write to Sheet |
| 4:30PM | `nse-research-orch` | Load SME skill + vault → unified evening report |
| 6:00PM | `nse-researcher-daily` | Find techniques, backtest, catalog |

**Sunday:** 6PM deep research + failure analysis → 7:30PM weekly outlook

## Self-Improvement Loop

Every Sunday, the researcher:
1. Reads ALL MISS signals from past week
2. Classifies failures: Type A (factor), B (technique), C (regime), D (data), E (execution)
3. Detects patterns: 3x same failure = CRITICAL proposal
4. Writes analysis to vault `06-Learnings/`
5. Proposes fixes (new parameters, combos, or scripts)
6. **User approves via Telegram** → changes implemented
7. Tracks improvement week-over-week

## Principle

**Agent proposes → User approves → Agent implements**

No changes are made without explicit user approval via Telegram.
