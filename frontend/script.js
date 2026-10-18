/**
 * btctool 3.0 - Frontend Client & High Speed Local Cache Manager
 */

let currentTf = "1h";
const _localTfCache = {};
const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "1d"];

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

    // 2. Directive Card / 24/7 Scenario Simulator
    const scen = data.intraday_scenario;
    const plan = data.trade_plan || {};
    const actionEl = document.getElementById("directive-action");
    const scenarioTag = document.getElementById("scenario-tag");
    const roleEl = document.getElementById("directive-role");
    const card1Title = document.getElementById("card1-title");
    const longBoxLabel = document.getElementById("long-box-label");
    const shortBoxLabel = document.getElementById("short-box-label");
    const longBoxSub = document.getElementById("long-box-sub");
    const shortBoxSub = document.getElementById("short-box-sub");
    const longTrigger = document.getElementById("long-trigger");
    const shortTrigger = document.getElementById("short-trigger");
    const pName1 = document.getElementById("param-name-1");
    const pName2 = document.getElementById("param-name-2");
    const pName3 = document.getElementById("param-name-3");
    const pName4 = document.getElementById("param-name-4");
    const pName5 = document.getElementById("param-name-5");
    const stopLossEl = document.getElementById("stop-loss-val");
    const target1El = document.getElementById("target1-val");
    const target2El = document.getElementById("target2-val");
    const rrRatioEl = document.getElementById("rr-ratio-val");
    const atrMultipleEl = document.getElementById("atr-multiple-val");

    // Scenario-specific elements
    const scenStatusLabel = document.getElementById("scenario-status-label");
    const scenProgressLabel = document.getElementById("scenario-progress-label");
    const scenProgressBar = document.getElementById("scenario-progress-bar");
    const wave2AmpTag = document.getElementById("wave2-amp-tag");
    const wave2Desc = document.getElementById("wave2-desc");
    const consensusMacro = document.getElementById("consensus-macro");
    const consensusTactical = document.getElementById("consensus-tactical");
    const consensusOb = document.getElementById("consensus-ob");

    if (scen && scen.wave_1) {
        // --- 24/7 MULTI-SCREEN SCENARIO SIMULATOR MODE ---
        if (card1Title) card1Title.textContent = "24/7 MULTI-SCREEN SCENARIO SIMULATOR";
        if (scenarioTag) scenarioTag.textContent = `${scen.macro_bias || "RANGE"} REGIME`;

        if (actionEl) {
            actionEl.textContent = scen.guidance || scen.headline;
            const mode = scen.action_mode || "";
            if (mode === "ENTER_NOW" || scen.status === "OPTIMAL_ENTRY_ZONE") {
                actionEl.style.color = "var(--accent-green)";
                actionEl.style.borderColor = "rgba(0, 255, 163, 0.4)";
                actionEl.style.background = "rgba(0, 255, 163, 0.08)";
            } else if (mode === "ENTER_SHORT") {
                actionEl.style.color = "var(--accent-red)";
                actionEl.style.borderColor = "rgba(255, 59, 105, 0.4)";
                actionEl.style.background = "rgba(255, 59, 105, 0.08)";
            } else if (mode === "TIGHTEN_STOPS" || scen.status === "EXHAUSTION_WARNING") {
                actionEl.style.color = "#ffb020";
                actionEl.style.borderColor = "rgba(255, 176, 32, 0.4)";
                actionEl.style.background = "rgba(255, 176, 32, 0.12)";
            } else if (mode === "TAKE_PROFIT" || scen.status === "TARGET_REACHED") {
                actionEl.style.color = "var(--accent-cyan)";
                actionEl.style.borderColor = "rgba(0, 229, 255, 0.4)";
                actionEl.style.background = "rgba(0, 229, 255, 0.08)";
            } else {
                actionEl.style.color = "var(--accent-cyan)";
                actionEl.style.borderColor = "rgba(0, 229, 255, 0.4)";
                actionEl.style.background = "rgba(0, 229, 255, 0.08)";
            }
        }

        if (roleEl) {
            roleEl.textContent = `Scenario: ${scen.headline} (Screen: ${data.timeframe.toUpperCase()})`;
        }

        const w1 = scen.wave_1;
        const w2 = scen.wave_2;

        if (longBoxLabel) longBoxLabel.textContent = `WAVE 1: ${w1.direction} MOVE`;
        if (longTrigger) longTrigger.textContent = `${w1.direction === "SHORT" ? "-" : "+"}$${Number(w1.expected_amplitude_dollars).toFixed(0)}`;
        if (longBoxSub) {
            const entry0 = w1.entry_zone ? Number(w1.entry_zone[0]).toLocaleString() : "--";
            const entry1 = w1.entry_zone ? Number(w1.entry_zone[1]).toLocaleString() : "--";
            longBoxSub.textContent = `Optimal Entry: $${entry0} – $${entry1}`;
        }

        if (shortBoxLabel) shortBoxLabel.textContent = "TARGET CEILING (TP ZONE)";
        if (shortTrigger) shortTrigger.textContent = `$${Number(w1.target_price).toLocaleString()}`;
        if (shortBoxSub) shortBoxSub.textContent = `Invalidation Risk Floor: $${Number(scen.invalidation_floor).toLocaleString()}`;

        // Progress Bar
        const progPct = scen.progress_pct || 0;
        const realDol = scen.realized_dollars || 0;
        if (scenStatusLabel) scenStatusLabel.textContent = `STATE: ${(scen.status || "").replace(/_/g, " ")}`;
        if (scenProgressLabel) scenProgressLabel.textContent = `Progress: ${progPct}% (${realDol >= 0 ? "+" : ""}$${realDol.toFixed(0)})`;
        if (scenProgressBar) {
            scenProgressBar.style.width = `${Math.min(100, Math.max(0, progPct))}%`;
            scenProgressBar.className = `progress-fill ${w1.direction === "SHORT" ? "red-fill" : "green-fill"}`;
        }

        // Wave 2 Box
        if (wave2AmpTag && w2) wave2AmpTag.textContent = `Wave 2: ${w2.direction} to $${Number(w2.expected_target).toLocaleString()}`;
        if (wave2Desc && w2) wave2Desc.textContent = w2.description || "Synthesizing subsequent trajectory...";

        // Parameters
        if (pName1) pName1.textContent = "Invalidation (Stop Loss):";
        if (stopLossEl) {
            stopLossEl.textContent = `$${Number(scen.invalidation_floor).toLocaleString()}`;
            stopLossEl.className = "param-val text-red font-bold";
        }

        if (pName2) pName2.textContent = "Wave 1 Target Ceiling:";
        if (target1El) target1El.textContent = `$${Number(w1.target_price).toLocaleString()}`;

        if (pName3) pName3.textContent = "Expected Amplitude:";
        if (target2El) target2El.textContent = `+$${Number(w1.expected_amplitude_dollars).toFixed(0)} Move`;

        if (pName4) pName4.textContent = "Risk : Reward Ratio:";
        if (rrRatioEl) rrRatioEl.textContent = w1.risk_reward_ratio || "--";

        if (pName5) pName5.textContent = "Active Screen Focus:";
        if (atrMultipleEl) atrMultipleEl.textContent = `${data.timeframe.toUpperCase()} (10-Screen Live Consensus)`;

        // Consensus summary chips
        const mc = scen.multi_screen_consensus || {};
        if (consensusMacro) consensusMacro.textContent = mc.macro_anchor || "Macro: --";
        if (consensusTactical) consensusTactical.textContent = mc.tactical_5m || "Tactical: --";
        if (consensusOb) consensusOb.textContent = mc.orderbook_bias || "Orderbook: --";

    } else if (plan.is_roadmap) {
        // Strategic Roadmap Mode (1W, 1D, 4H)
        if (card1Title) card1Title.textContent = "STRATEGIC ROADMAP & VOLATILITY RADAR";
        if (longBoxLabel) longBoxLabel.textContent = "CORRIDOR FLOOR (SUPPORT)";
        if (shortBoxLabel) shortBoxLabel.textContent = "CORRIDOR ROOF (RESISTANCE)";
        if (longBoxSub) longBoxSub.textContent = "Macro Lower Boundary";
        if (shortBoxSub) shortBoxSub.textContent = "Macro Upper Boundary";

        if (pName1) pName1.textContent = "Forecast Horizon:";
        if (stopLossEl) {
            stopLossEl.textContent = plan.forecast_period || "Next Session";
            stopLossEl.className = "param-val text-cyan font-bold";
        }

        if (pName2) pName2.textContent = "Expected Volatility (%):";
        if (target1El) target1El.textContent = `±${plan.expected_vol_pct}%`;

        if (pName3) pName3.textContent = "Expected Volatility ($):";
        if (target2El) target2El.textContent = `±$${Number(plan.expected_vol_dollars).toLocaleString()}`;

        if (pName4) pName4.textContent = "4-Pillar Confluence:";
        if (rrRatioEl) rrRatioEl.textContent = plan.four_pillars ? plan.four_pillars.confluence_summary : "Verified";

        if (pName5) pName5.textContent = "Trading Corridor:";
        if (atrMultipleEl) atrMultipleEl.textContent = plan.atr_stop_multiple || "--";

        if (longTrigger) longTrigger.textContent = plan.corridor_floor ? `$${Number(plan.corridor_floor).toLocaleString()}` : "$--";
        if (shortTrigger) shortTrigger.textContent = plan.corridor_roof ? `$${Number(plan.corridor_roof).toLocaleString()}` : "$--";

    } else {
        // Tactical Sniper Execution Mode (1M, 3M, 5M, 15M, 30M, 1H, 2H)
        if (card1Title) card1Title.textContent = "TRADING DIRECTIVE & EXECUTION PLAN";
        if (longBoxLabel) longBoxLabel.textContent = "LONG ENTRY TRIGGER";
        if (shortBoxLabel) shortBoxLabel.textContent = "SHORT ENTRY TRIGGER";
        if (longBoxSub) longBoxSub.textContent = "Distinct Structural Level";
        if (shortBoxSub) shortBoxSub.textContent = "Distinct Breakdown Level";

        if (pName1) pName1.textContent = "Invalidation (Stop Loss):";
        if (stopLossEl) {
            stopLossEl.textContent = plan.stop_loss ? `$${Number(plan.stop_loss).toLocaleString()}` : "$--";
            stopLossEl.className = "param-val text-red font-bold";
        }

        if (pName2) pName2.textContent = "Target 1 (Scalp / Base):";
        if (target1El) target1El.textContent = plan.target_1 ? `$${Number(plan.target_1).toLocaleString()} (+${plan.gain_pct}%)` : "$--";

        if (pName3) pName3.textContent = "Target 2 (Max Runner):";
        if (target2El) target2El.textContent = plan.target_2 ? `$${Number(plan.target_2).toLocaleString()} (+${plan.max_runner_pct}%)` : "$--";

        if (pName4) pName4.textContent = "Risk : Reward Ratio:";
        if (rrRatioEl) rrRatioEl.textContent = plan.risk_reward_ratio || "--";

        if (pName5) pName5.textContent = "ATR Multiple Standard:";
        if (atrMultipleEl) atrMultipleEl.textContent = plan.atr_stop_multiple || "--";

        if (longTrigger) longTrigger.textContent = plan.long_entry_trigger ? `$${Number(plan.long_entry_trigger).toLocaleString()}` : "$--";
        if (shortTrigger) shortTrigger.textContent = plan.short_entry_trigger ? `$${Number(plan.short_entry_trigger).toLocaleString()}` : "$--";
    }

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
    const difDeaStr = (mom.macd_dif !== undefined && mom.macd_dea !== undefined) ? ` · DIF: ${mom.macd_dif} / DEA: ${mom.macd_dea}` : "";
    document.getElementById("macd-slope-val").textContent = `${mom.is_accelerating ? "▲ Expanding" : "▼ Decelerating"}${difDeaStr}`;
    
    const maCrossEl = document.getElementById("ma-cross-val");
    if (maCrossEl) {
        maCrossEl.textContent = (mom.ma5 && mom.ma10) ? `$${mom.ma5.toLocaleString()} / $${mom.ma10.toLocaleString()} (${mom.ma5 >= mom.ma10 ? "MA5>MA10 ▲" : "MA5<MA10 ▼"})` : "--";
        maCrossEl.style.color = (mom.ma5 && mom.ma10 && mom.ma5 >= mom.ma10) ? "var(--accent-green)" : "var(--accent-red)";
    }
    const volSurgeEl = document.getElementById("vol-surge-val");
    if (volSurgeEl) {
        volSurgeEl.textContent = mom.volume_surge ? `${mom.volume_surge.toFixed(2)}x (vs 10-bar avg)` : "--";
        volSurgeEl.style.color = (mom.volume_surge >= 1.25) ? "var(--accent-green)" : "var(--text-muted)";
    }

    document.getElementById("vol-score").textContent = `State: ${vol.squeeze_state || "--"}`;
    const bollInfo = vol.bb_bandwidth_pct !== undefined ? ` · BB Width: ${vol.bb_bandwidth_pct}% (${vol.bb_direction})` : "";
    document.getElementById("vol-regime-val").textContent = `Vol Rank: ${Math.round((vol.volatility_regime_rank || 0.5) * 100)}th%${bollInfo}`;

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
