# 🏛️ Master Blueprint: btctool 3.0
**System:** Institutional Predictive Advisory & Directive Engine for BTC/USDT (Merged Engine)  
**Root Directory:** `c:\gemini proyect\btctool 3.0`  
**Status:** Architecture Blueprint Stage — Feasibility Confirmed, Awaiting User Authorization to Code  

---

## 1. Operating Rules & Guardrails
1. **Strict Folder Isolation:** All operations, files, resources, and configuration reside strictly within `c:\gemini proyect\btctool 3.0`. No reading, modifying, or scanning external directories.
2. **Continuous Blueprint Synchronization:** This file is updated after every change or milestone to prevent loss of state from power outage or restart.
3. **Answer First Rule:** Address questions and explanations directly before writing implementation code.
4. **Deferred Modules:** Alert bot / Telegram execution engine deferred to Phase 2 per user directive ("ignore the bot for now").

---

## 2. Core Architecture & Stack

```
┌─────────────────────────────────────────────────────────┐
│                   SHARED DATA PIPELINE                  │
│  Bybit Spot Klines → Primary                           │
│  Binance + yfinance → Fallback                         │
│  Bybit/OKX Order Books → L2 Microstructure            │
│  Bybit Linear → Funding Rate, OI, Taker Delta          │
│  Alternative.me → Fear & Greed (Macro TFs 4H+)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              LEVEL 1 — SIGNAL GENERATION                │
│                                                         │
│  StatisticalBrain  │  MomentumBrain  │  VolatilityBrain│
│  (v2.0 logic)      │  (v2.0 logic)   │  + Squeeze FSM  │
│                    │                 │                  │
│  9-TF Scaled RSI   │  9-TF Scaled    │  ATR + KC/BB    │
│  + %B              │  EMA + MACD     │  State Machine  │
│  (v1 params)       │  (v1 params)    │  (merged)       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│            LEVEL 2 — ML META-LEARNER                    │
│                                                         │
│  HistGradientBoostingClassifier (sklearn, no new dep)  │
│                                                         │
│  Inputs:                                               │
│  • Brain scores (L1 outputs)                           │
│  • OB Imbalance ratio (tanh-adjusted)                  │
│  • Funding Rate                                        │
│  • OI Change Z-score                                   │
│  • Taker Buy/Sell Delta ratio                          │
│  • ADX(14) + Volatility regime                         │
│  • Time-of-day session feature                         │
│                                                         │
│  Output: Calibrated probability_up (0.0 → 1.0)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          LEVEL 3 — DERIVATIVES PRE-FILTER               │
│                                                         │
│  • Funding rate suppression                            │
│  • Liquidation trap filter (adaptive threshold)        │
│  • OI Z-score confirmation                             │
│  • ADX regime gate (ADX > 22 for trend mode)           │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│        LEVEL 4 — SCENARIO DECISION MATRIX               │
│        (v2.0 5-scenario + v1 anti-collision rule)       │
│                                                         │
│  Priority: Derivatives → 4H Regime → Squeeze State     │
│            → OB Imbalance (tanh) → %B                 │
│                                                         │
│  Triggers: ALL in ATR multiples, NO dollar amounts     │
│  Collision Guard: Long & Short triggers NEVER identical │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   WEB DASHBOARD                         │
│  • FastAPI asynchronous backend                         │
│  • High-performance HTML5/CSS3/Vanilla JS UI           │
│  • Instant 9-timeframe switching (<0.1s cache warmer)  │
│  • Cross-timeframe alignment score (7-9, 5-6, <5)      │
│  • Memory hardened for cloud (<120 MB RAM target)       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Component Synthesis: What btctool 3.0 Merges

| Component | Source Origin | Role in `btctool 3.0` |
| :--- | :--- | :--- |
| **Backend & UI** | v1 | FastAPI + async routes + HTML/JS trading terminal (lightweight, <120MB). |
| **Timeframe Parameters** | v1 | 9-timeframe scaled RSI, EMA, BB, MACD parameters (1M to 1W). |
| **Tri-Brain Ensemble** | v2.0 | `StatisticalBrain`, `MomentumBrain`, `VolatilityBrain` signal decomposition. |
| **ML Meta-Learner** | v1 + v2.0 | HistGradientBoostingClassifier + Platt scaling fed by orthogonal features and Brain scores. |
| **Order Book Microstructure** | v2.0 | Bybit + OKX L2 depth with exponential decay $w_i = e^{-40 \Delta P / mid}$ and tanh alpha $\Delta P = 0.15 \tanh(3.0 \cdot imb)$. |
| **Derivatives Feeds** | v2.0 | Bybit Linear funding rate, OI Z-score, and taker buy/sell delta. |
| **Derivatives Pre-Filter** | v2.0 + v1 | Funding suppression, liquidation trap filter, ADX trend gate ($ADX > 22$). |
| **Squeeze FSM** | v1 + v2.0 | 5-State Volatility Squeeze Machine (`IDLE`, `BUILDING`, `LOADED`, `FIRING`, `TRENDING`). |
| **Decision Engine** | v2.0 + v1 | 5 Scenarios + v1 Anti-collision rule + Zero dollar amounts (pure ATR triggers). |
| **Cross-TF Alignment** | New | Confluence metric across all 9 timeframes (7-9 strong, 5-6 moderate, <5 conflicted/suppressed). |
| **Backtest & Calibration** | New | Offline validation harness to calibrate $k$-factor, ADX thresholds, and squeeze counts. |

---

## 4. Timeframe Scaling Matrix (9 Timeframes)

| Timeframe | Horizon | RSI Periods | Fast / Slow EMA | BB Period / Dev | MACD Params | ATR Stop Multiplier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1M** | 3 min | (3, 7, 14) | 5 / 13 | 14 / 2.0 | (6, 13, 5) | $1.0 \times ATR$ |
| **5M** | 15 min | (5, 9, 14) | 8 / 21 | 20 / 2.0 | (8, 17, 7) | $1.0 \times ATR$ |
| **15M** | 45 min | (6, 12, 24) | 9 / 21 | 20 / 2.0 | (12, 26, 9) | $1.5 \times ATR$ |
| **30M** | 1.5 hours | (6, 14, 28) | 12 / 26 | 20 / 2.0 | (12, 26, 9) | $1.5 \times ATR$ |
| **1H** | 3 hours | (6, 12, 24) | 9 / 21 | 20 / 2.0 | (12, 26, 9) | $1.5 \times ATR$ |
| **4H** | 12 hours | (7, 14, 28) | 10 / 30 | 20 / 2.2 | (12, 26, 9) | $2.0 \times ATR$ |
| **8H** | 24 hours | (7, 14, 28) | 12 / 36 | 20 / 2.2 | (12, 26, 9) | $2.0 \times ATR$ |
| **1D** | 3 days | (9, 14, 30) | 20 / 50 | 20 / 2.0 | (12, 26, 9) | $2.0 \times ATR$ |
| **1W** | 3 weeks | (7, 14, 21) | 10 / 40 | 20 / 2.0 | (12, 26, 9) | $2.0 \times ATR$ |

---

## 5. Planned Workspace File Structure
```
c:\gemini proyect\btctool 3.0\
├── backend\
│   ├── app.py                      # FastAPI application, CORS, cache warmer, routes
│   ├── config.py                   # Unified endpoints, thresholds & constants
│   ├── models\
│   │   └── summary.py              # Pydantic schemas for 9-TF summary & directives
│   ├── services\
│   │   ├── market_data.py          # Primary Bybit Spot + Fallbacks (Binance, yfinance)
│   │   ├── orderbook.py            # Bybit + OKX L2 depth, tanh alpha, 3-snapshot filter
│   │   ├── derivatives.py          # Bybit Linear funding rate, OI Z-score, taker delta
│   │   ├── brains.py               # StatisticalBrain, MomentumBrain, VolatilityBrain + FSM
│   │   ├── ml_learner.py           # HistGradientBoostingClassifier + Platt calibration
│   │   ├── pre_filter.py           # Derivatives pre-filter & ADX regime gate
│   │   ├── decision_matrix.py      # 5 Scenarios, anti-collision, ATR triggers & cross-TF score
│   │   └── sentiment.py            # Local fast sentiment (1m-1h) & macro Alternative.me (4h+)
│   └── utils\
│       └── http_client.py          # Async httpx client with connection pooling & retries
├── frontend\
│   ├── index.html                  # Responsive 9-timeframe trading terminal UI
│   ├── script.js                   # High-speed DOM rendering, local caching (<0.1s switch)
│   └── styles.css                  # Terminal styling, squeeze badge indicators, cross-TF radar
├── backtest\
│   └── calibrate.py                # Offline parameter calibration & backtesting harness
├── requirements.txt                # Lean dependency manifest (fastapi, uvicorn, scikit-learn, etc.)
└── BLUEPRINT.md                    # Master Project Memory (Synchronized continuously)
```

---

## 6. Git & Cloud Deployment Strategy
- **Local Git Repository:** Initialized in `c:\gemini proyect\btctool 3.0` with atomic commits per milestone.
- **Remote GitHub:** Automated creation via GitHub REST API under user `aricimi` (`https://github.com/aricimi/btctool-3.0.git`).
- **Hosting Engine:** Automated Render Web Service creation via Render REST API (`POST /v1/services`), running `uvicorn backend.app:app` with `render.yaml`.
- **Keep-Alive:** UptimeRobot HTTP monitor pinging `/health` every 5 minutes.

---

## 7. Milestone Tracker
- [x] Initialized workspace and isolation guardrails
- [x] Ingested v1 and v2.0 blueprints and merge specifications
- [x] Defined unified architecture and updated `BLUEPRINT.md`
- [x] Detected local GitHub OAuth credentials for `aricimi` (ready for automated repo creation)
- [ ] Create remote GitHub repository `aricimi/btctool-3.0` via API
- [ ] Initialize local git & initial commit with `.gitignore` and `BLUEPRINT.md`
- [ ] Connect Render API and prepare deployment automation
- [ ] Step 1: Core market data & derivatives feeds (Bybit primary + fallbacks)
- [ ] Step 2: Tri-Brain ensemble with 9-TF scaled parameters + Squeeze FSM
- [ ] Step 3: HistGBM Meta-Learner with Platt calibration & orthogonal feature matrix
- [ ] Step 4: Derivatives pre-filter & 5-scenario decision matrix (pure ATR, anti-collision)
- [ ] Step 5: Cross-timeframe alignment engine & FastAPI endpoints
- [ ] Step 6: Frontend dashboard integration (HTML/JS/CSS)
- [ ] Step 7: Offline backtesting and threshold calibration harness
- [ ] Step 8: Memory hardening and end-to-end verification
- [ ] Step 9: Render deployment & UptimeRobot keepalive monitor

---

## 8. Change Log
- **2026-10-18:** Project initialized. Created `BLUEPRINT.md` and established strict folder confinement and persistence rules.
- **2026-10-18:** Analyzed v1 and v2.0 blueprints; formulated unified `btctool 3.0` architecture merging FastAPI, 9-TF scaling, Tri-Brain, HistGBM, L2 microstructure, and pure ATR scenario matrix. Deferred bot execution to Phase 2.
- **2026-10-18:** Confirmed local Python 3.14 environment has all core dependencies (FastAPI, Scikit-Learn, Pandas, NumPy, Uvicorn, HTTPX) already installed. Defined Git & deployment strategy.
- **2026-10-18:** Verified stored GitHub credentials for `aricimi` with `repo` scope. Confirmed ability to automate GitHub repository creation and git workflow.
