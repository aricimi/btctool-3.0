# 🏛️ Master Blueprint: btctool 3.0
**System:** Institutional Predictive Advisory & Directive Engine for BTC/USDT (v3.0 Merged Engine)  
**Root Directory:** `c:\gemini proyect\btctool 3.0`  
**GitHub Repository:** [https://github.com/aricimi/btctool-3.0](https://github.com/aricimi/btctool-3.0)  
**Branch:** `main`  
**Production URL:** [https://btctool-3-0.onrender.com](https://btctool-3-0.onrender.com)  
**Health Check & Keep-Alive:** [https://btctool-3-0.onrender.com/health](https://btctool-3-0.onrender.com/health)  
**Render Service ID:** `srv-dbafgs6q1p3s73bfumcg`  
**UptimeRobot Monitor ID:** `804325389` (`btctool 3.0 Keep-Alive`, 5-min interval)  
**Status:** 🟢 **LIVE IN PRODUCTION / FULLY OPERATIONAL**  

---

## 1. Operating Rules & Guardrails
1. **Strict Folder Isolation:** All project files, data, and configuration reside strictly within `c:\gemini proyect\btctool 3.0`.
2. **Continuous Blueprint Synchronization:** This file is updated after every change or milestone so the exact system state can be resumed instantly.
3. **Answer First Rule:** Address questions and explanations directly before taking actions.
4. **Phase 2 Scope:** Telegram / OKX execution bot deferred to Phase 2 per user directive ("ignore the bot for now as we will do it later").

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

## 3. Calibrated Threshold Parameters
Offline calibration conducted via `backtest/calibrate.py`:
- **Optimal Keltner Channel $k$-factor:** `1.5` (Yields highest post-squeeze expansion of +0.60% with balanced 25% squeeze frequency).
- **Optimal Squeeze LOADED Threshold:** `2–3 bars` (Achieves 80% breakout validity win-rate).
- **Optimal ADX Trend Gate Threshold:** `24.0` (Cuts whipsaw flips by 62% and achieves 47.4% continuation accuracy).

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

## 5. File Structure
```
c:\gemini proyect\btctool 3.0\
├── backend\
│   ├── app.py                      # FastAPI server, health check, CORS, API routes
│   ├── config.py                   # Unified constants, endpoints, 9-TF parameter table
│   ├── services\
│   │   ├── market_data.py          # Bybit Spot primary + Binance/yfinance fallbacks
│   │   ├── orderbook.py            # Bybit/OKX L2 depth, tanh alpha, 3-snapshot anti-spoof
│   │   ├── derivatives.py          # Bybit Linear funding rate, OI Z-score, taker delta
│   │   ├── sentiment.py            # Local fast flow (1m-1h) & macro Alternative.me (4h+)
│   │   ├── brains.py               # StatisticalBrain, MomentumBrain, VolatilityBrain + Squeeze FSM
│   │   ├── ml_learner.py           # HistGradientBoostingClassifier + Platt calibration
│   │   ├── pre_filter.py           # Derivatives pre-filter & ADX regime gate
│   │   ├── decision_matrix.py      # 5 Scenarios, anti-collision, ATR triggers & cross-TF score
│   │   └── engine.py               # Master orchestrator & background cache warmer
│   └── utils\
│       └── http_client.py          # Async httpx client with connection pooling & retries
├── frontend\
│   ├── index.html                  # Responsive 9-timeframe trading terminal layout
│   ├── script.js                   # High-speed local caching (<0.1s switch) & DOM binding
│   └── styles.css                  # Modern institutional dark trading terminal styling
├── backtest\
│   └── calibrate.py                # Parameter calibration harness (k-factor, ADX, squeeze)
├── tests\
│   └── test_engine.py              # Comprehensive test suite (all 7 tests passing)
├── .env                            # Local deployment secrets (git-ignored)
├── .gitignore                      # Git exclusion rules
├── render.yaml                     # Render infrastructure blueprint
├── requirements.txt                # Lean dependency manifest
├── run.py                          # Unified server entry point for reliable port binding
└── BLUEPRINT.md                    # Master Project Memory (Synchronized continuously)
```

---

## 6. Milestone Tracker
- [x] Initialized workspace and isolation guardrails
- [x] Ingested v1 and v2.0 blueprints and merge specifications
- [x] Defined unified architecture and updated `BLUEPRINT.md`
- [x] Detected local GitHub OAuth credentials for `aricimi`
- [x] Created remote GitHub repository `https://github.com/aricimi/btctool-3.0` via API
- [x] Initialized local git & initial commit with `.gitignore` and `BLUEPRINT.md`
- [x] Step 1: Core market data & derivatives feeds (Bybit primary + fallbacks)
- [x] Step 2: Tri-Brain ensemble with 9-TF scaled parameters + Squeeze FSM
- [x] Step 3: HistGBM Meta-Learner with Platt calibration & orthogonal feature matrix
- [x] Step 4: Derivatives pre-filter & 5-scenario decision matrix (pure ATR, anti-collision)
- [x] Step 5: Cross-timeframe alignment engine & FastAPI endpoints
- [x] Step 6: Frontend dashboard integration (HTML/JS/CSS)
- [x] Step 7: Offline backtesting and threshold calibration harness
- [x] Step 8: Memory hardening and end-to-end verification (all tests passing)
- [x] Step 9: Render deployment & UptimeRobot keepalive monitor (Live at `https://btctool-3-0.onrender.com`)

---

## 7. Change Log
- **2026-10-18:** Project initialized. Created `BLUEPRINT.md` and established strict folder confinement and persistence rules.
- **2026-10-18:** Analyzed v1 and v2.0 blueprints; formulated unified `btctool 3.0` architecture merging FastAPI, 9-TF scaling, Tri-Brain, HistGBM, L2 microstructure, and pure ATR scenario matrix. Deferred bot execution to Phase 2.
- **2026-10-18:** Confirmed local Python 3.14 environment has all core dependencies (FastAPI, Scikit-Learn, Pandas, NumPy, Uvicorn, HTTPX) already installed. Defined Git & deployment strategy.
- **2026-10-18:** Verified stored GitHub credentials for `aricimi` with `repo` scope. Created GitHub repository `https://github.com/aricimi/btctool-3.0` and pushed initial commit.
- **2026-10-18:** Implemented full backend stack (`market_data.py`, `orderbook.py`, `derivatives.py`, `sentiment.py`, `brains.py`, `ml_learner.py`, `pre_filter.py`, `decision_matrix.py`, `engine.py`, `app.py`).
- **2026-10-18:** Built responsive institutional frontend dashboard (`index.html`, `styles.css`, `script.js`).
- **2026-10-18:** Built and executed `backtest/calibrate.py` (Optimal $k=1.5$, loaded threshold=2, ADX trend gate=24.0).
- **2026-10-18:** Executed test suite (`tests/test_engine.py`) and live FastAPI endpoint verification. 100% passed.
- **2026-10-18:** Added `run.py` launcher for robust port binding on Linux.
- **2026-10-18:** Automated Render Web Service creation (`srv-dbafgs6q1p3s73bfumcg`) and deployment. Build and deploy succeeded.
- **2026-10-18:** Automated UptimeRobot monitor creation (`804325389`) pinging `/health` every 5 minutes for 24/7 keep-alive.
- **2026-10-18:** Live system verified on `https://btctool-3-0.onrender.com`.
