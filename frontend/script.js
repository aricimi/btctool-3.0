/**
 * btctool 3.0 - Frontend Client & High Speed Local Cache Manager
 */

let currentTf = "1h";
const _localTfCache = {};
const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"];

document.addEventListener("DOMContentLoaded", () => {
    initTimeframeButtons();
    fetchSummary(currentTf);
    fetchCrossRadar();
    
    // Auto refresh cycling: every 8 seconds
    setInterval(() => {
        fetchSummary(currentTf);
        fetchCrossRadar();
    }, 8000);
});

function initTimeframeButtons() {
    const buttons = document.querySelectorAll(".tf-btn");
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tf = btn.getAttribute("data-tf");
            if (tf === currentTf) return;
            
            buttons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentTf = tf;
            
            // Instant render from local cache if available (<0.1s switch)
            if (_localTfCache[tf]) {
                renderSummary(_localTfCache[tf]);
            }
            // Fetch latest asynchronously
            fetchSummary(tf);
        });
    });
}

async function fetchSummary(tf) {
    try {
        const resp = await fetch(`/btc/summary?timeframe=${tf}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        
        _localTfCache[tf] = data;
        if (tf === currentTf) {
            renderSummary(data);
        }
    } catch (err) {
        console.error(`Failed to fetch summary for ${tf}:`, err);
    }
}

async function fetchCrossRadar() {
    try {
        const resp = await fetch(`/btc/cross-alignment`);
        if (!resp.ok) return;
        const data = await resp.json();
        renderRadarStrip(data);
    } catch (err) {
        console.error("Radar fetch error:", err);
    }
}

function renderSummary(data) {
    if (!data || data.error) return;

    // 1. Live Ticker & Header
    const priceEl = document.getElementById("current-price");
    if (priceEl && data.current_price) {
        priceEl.textContent = `$${data.current_price.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`;
    }

    const macroBadge = document.getElementById("macro-badge");
    if (macroBadge) {
        const reg = data.macro_regime || "Range";
        macroBadge.textContent = `4H REGIME: ${reg.toUpperCase()}`;
        macroBadge.className = `badge ${reg === "Trend Up" ? "badge-green" : (reg === "Trend Down" ? "badge-red" : "badge-neutral")}`;
    }

    const squeezeBadge = document.getElementById("squeeze-badge");
    if (squeezeBadge && data.indicators) {
        squeezeBadge.textContent = data.indicators.squeeze_badge;
    }

    // 2. Directive Card
    const plan = data.trade_plan || {};
    const actionEl = document.getElementById("directive-action");
    if (actionEl) {
        actionEl.textContent = plan.action || "SCANNING...";
        if (plan.action_type === "BUY" || plan.action_type === "BUY_LIMIT") {
            actionEl.style.color = "var(--accent-green)";
            actionEl.style.borderColor = "rgba(0, 255, 163, 0.4)";
            actionEl.style.background = "rgba(0, 255, 163, 0.08)";
        } else {
            actionEl.style.color = "var(--accent-red)";
            actionEl.style.borderColor = "rgba(255, 59, 105, 0.4)";
            actionEl.style.background = "rgba(255, 59, 105, 0.08)";
        }
    }

    const scenarioTag = document.getElementById("scenario-tag");
    if (scenarioTag) scenarioTag.textContent = plan.scenario || "Scenario Active";

    const roleEl = document.getElementById("directive-role");
    const tfParam = data.indicators || {};
    if (roleEl) roleEl.textContent = `Timeframe: ${data.timeframe.toUpperCase()} · ATR Standard: ${plan.atr_stop_multiple || "--"}`;

    document.getElementById("long-trigger").textContent = plan.long_entry_trigger ? `$${plan.long_entry_trigger.toLocaleString()}` : "$--";
    document.getElementById("short-trigger").textContent = plan.short_entry_trigger ? `$${plan.short_entry_trigger.toLocaleString()}` : "$--";
    document.getElementById("stop-loss-val").textContent = plan.stop_loss ? `$${plan.stop_loss.toLocaleString()}` : "$--";
    document.getElementById("target1-val").textContent = plan.target_1 ? `$${plan.target_1.toLocaleString()} (+${plan.gain_pct}%)` : "$--";
    document.getElementById("target2-val").textContent = plan.target_2 ? `$${plan.target_2.toLocaleString()} (+${plan.max_runner_pct}%)` : "$--";
    document.getElementById("rr-ratio-val").textContent = plan.risk_reward_ratio || "--";
    document.getElementById("atr-multiple-val").textContent = plan.atr_stop_multiple || "--";

    // 3. ML Probabilities & Order Book
    const probUpPct = data.prob_up_pct || 50;
    const probDownPct = data.prob_down_pct || 50;
    
    document.getElementById("prob-up-text").textContent = `${probUpPct}%`;
    document.getElementById("prob-down-text").textContent = `${probDownPct}%`;
    document.getElementById("prob-up-bar").style.width = `${probUpPct}%`;
    document.getElementById("prob-down-bar").style.width = `${probDownPct}%`;

    const ob = data.orderbook || {};
    document.getElementById("ob-imbalance-val").textContent = `${ob.imbalance_ratio > 0 ? "+" : ""}${Math.round(ob.imbalance_ratio * 100)}% (${ob.source || "L2"})`;
    document.getElementById("ob-alpha-val").textContent = `${ob.tanh_alpha > 0 ? "+" : ""}${Math.round(ob.tanh_alpha * 100)}% ΔP`;

    const deriv = data.derivatives || {};
    document.getElementById("funding-rate-val").textContent = `${deriv.funding_rate_pct > 0 ? "+" : ""}${deriv.funding_rate_pct}%`;
    document.getElementById("oi-zscore-val").textContent = `${deriv.oi_zscore > 0 ? "+" : ""}${deriv.oi_zscore}`;
    document.getElementById("taker-delta-val").textContent = `${deriv.taker_delta > 0 ? "+" : ""}${Math.round(deriv.taker_delta * 100)}%`;

    // 4. Tri-Brain Ensemble
    const brains = data.brain_ensemble || {};
    const stat = brains.statistical || {};
    const mom = brains.momentum || {};
    const vol = brains.volatility || {};

    document.getElementById("stat-score").textContent = `Bull: ${Math.round(stat.bull_score * 100)}% / Bear: ${Math.round(stat.bear_score * 100)}%`;
    document.getElementById("pct-b-val").textContent = stat.pct_b ? stat.pct_b.toFixed(2) : "--";
    document.getElementById("stat-note").textContent = stat.regime_note || "";

    document.getElementById("mom-score").textContent = `Bull: ${Math.round(mom.bull_score * 100)}% / Bear: ${Math.round(mom.bear_score * 100)}%`;
    document.getElementById("rsi-val").textContent = `${mom.rsi_fast || "--"} / ${mom.rsi_mid || "--"} / ${mom.rsi_slow || "--"}`;
    document.getElementById("macd-slope-val").textContent = `${mom.is_accelerating ? "▲ Accelerating" : "▼ Decelerating"} (${mom.smooth_slope > 0 ? "+" : ""}${mom.smooth_slope})`;

    document.getElementById("vol-score").textContent = `State: ${vol.squeeze_state || "--"}`;
    document.getElementById("atr-val").textContent = `$${vol.atr || "--"} (${vol.atr_pct || "--"}%)`;
    document.getElementById("vol-regime-val").textContent = `Vol Rank: ${Math.round((vol.volatility_regime_rank || 0.5) * 100)}th percentile`;

    // 5. Pre-Filter & Sentiment
    const preFilter = data.pre_filter || {};
    document.getElementById("adx-val").textContent = `${preFilter.adx_val || "--"}`;
    const adxStatus = document.getElementById("adx-status");
    if (adxStatus) {
        if (preFilter.adx_val > 22) {
            adxStatus.textContent = "ADX > 22: Strong Trend Confirmed";
            adxStatus.style.color = "var(--accent-green)";
        } else {
            adxStatus.textContent = "ADX <= 22: Range / Consolidation Mode";
            adxStatus.style.color = "var(--accent-gold)";
        }
    }

    const sentiment = data.sentiment || {};
    const sentVal = document.getElementById("sentiment-val");
    if (sentVal) {
        sentVal.textContent = `${sentiment.value}/100 · ${sentiment.classification}`;
    }
    const sentSrc = document.getElementById("sentiment-src");
    if (sentSrc) sentSrc.textContent = sentiment.source || "";

    // Warnings list
    const warningsList = document.getElementById("warnings-list");
    if (warningsList) {
        warningsList.innerHTML = "";
        const warns = preFilter.warnings || [];
        if (warns.length === 0) {
            warningsList.innerHTML = "<li>Pre-filter clear. No institutional traps active.</li>";
        } else {
            warns.forEach(w => {
                const li = document.createElement("li");
                li.textContent = w;
                warningsList.appendChild(li);
            });
        }
    }

    // Cross-TF Badge
    const crossAlign = data.cross_tf_alignment;
    const crossBadge = document.getElementById("cross-tf-badge");
    if (crossBadge && crossAlign) {
        crossBadge.textContent = crossAlign.badge;
        crossBadge.className = `badge ${crossAlign.dominant_count >= 7 ? "badge-green" : (crossAlign.dominant_count >= 5 ? "badge-gold" : "badge-red")}`;
    }
}

function renderRadarStrip(radar) {
    const strip = document.getElementById("radar-strip");
    if (!strip) return;
    
    strip.innerHTML = "";
    TIMEFRAMES.forEach(tf => {
        const item = _localTfCache[tf];
        const probUp = item ? Math.round(item.prob_up_pct) : "--";
        const pill = document.createElement("div");
        pill.className = "radar-pill";
        pill.innerHTML = `<span class="tf-label">${tf.toUpperCase()}:</span><span class="tf-prob">${probUp}% Up</span>`;
        strip.appendChild(pill);
    });
}
