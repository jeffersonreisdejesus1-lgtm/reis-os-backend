# META-ARQ-REIS-OS-TRADING-MISSION-RUNTIME-V1-ECONOMIC-002

STATUS: TARGETED_REPAIR_IMPLEMENTATION_BASELINE

Purpose: bounded intraday/day-trade market radar with paper trading, economic validation, and signal emission.

## Non-negotiable gates
- REAL_MONEY_AUTONOMOUS_EXECUTION = FORBIDDEN
- PAPER_TRADING = REQUIRED
- FOUNDER_FINAL_GATE = REQUIRED
- GITHUB = SOURCE_OF_TRUTH
- RENDER = ZERO_COST_RUNTIME_TARGET
- NO_UNAUTHORIZED_SPEND = TRUE

## Signal contract
Required fields: asset, direction (BUY|SELL|HOLD), entry_price/range, estimated_holding_time, signal_expires_at, target_price, stop_price, gross_expected_return_pct, estimated_trading_cost_pct, net_expected_return_pct, position_size, account_risk_pct, confidence_score(advisory only), data_cutoff, market_data_timestamp, run_id, signal_id, evidence_ref.

Human surface minimum: ASSET + BUY/SELL/HOLD + ESTIMATED_HOLDING_TIME + ESTIMATED_NET_PROFIT + ENTRY + TARGET + STOP.

## Runtime pipeline
BINANCE PUBLIC DATA -> DATA VALIDATION/FRESHNESS -> SHARED CACHE -> DETERMINISTIC FEATURE ENGINE -> OPPORTUNITY FILTER -> MARKET BRAIN -> SELECTIVE PAIR BRAINS -> HARD RISK GATE -> BATCH MULTI-PERSPECTIVE JURY -> OPTIONAL INDEPENDENT SECOND PASS -> PAIR ANALYST -> PORTFOLIO/GLOBAL RISK -> NOESIS FINAL GATE -> PAPER EXECUTION ENGINE -> OUTCOME + COST + CAUSAL LEDGER.

## Economic authority
Exactly one cost authority: ECONOMIC_GOVERNOR.
REQUEST -> ESTIMATE -> ATOMIC RESERVATION -> PROVIDER CALL -> USAGE RECEIPT -> COST LEDGER -> RECONCILIATION.
Executable gates: DAILY_BUDGET, MONTHLY_BUDGET, RUN_BUDGET, SIGNAL_BUDGET, CYCLE_CALL_LIMIT, STRONG_MODEL_LIMIT.
Provider/model pricing must be configured by registry; never assume a free model.

## Risk
STOP_DISTANCE != ACCOUNT_RISK.
Required policy controls: max_capital_at_risk_per_trade, max_daily_realized_loss, max_daily_total_risk, max_concurrent_exposure, max_correlated_exposure, max_drawdown.
Absolute stop-distance ceiling 25%; effective stop is technically derived.
Net expected return must include applicable fees/spread/slippage/funding/borrowing/tax assumptions.

## Time/freshness
Trading class: INTRADAY/DAY_TRADE. Minimum expected holding ~1h; normal 1h-8h; overnight forbidden by default. signal expiration and entry validity are required.
Freshness fields: market_data_timestamp, received_at, processing_started_at, signal_created_at, max_data_age.

## Failure model
EXCHANGE_UNAVAILABLE, RATE_LIMITED, PARTIAL_DATA, BOOK_UNAVAILABLE, CANDLE_GAP, OUT_OF_ORDER_EVENT, DUPLICATE_EVENT, CLOCK_DRIFT -> HOLD_DATA.
Other kill switches: HOLD_COST, HOLD_MODEL, HOLD_RISK, HOLD_DRAWDOWN, HOLD_ANOMALY, HOLD_PROVIDER, SYSTEM_STOP.

## Evidence and cache
Evidence ledger is logically append-only with EVENT_ID, CAUSAL_PARENT_ID, RUN_ID, INPUT_HASH, OUTPUT_HASH, CONFIG_HASH, MODEL_REF, PROMPT_REF, DATA_SNAPSHOT_REF, PREDECESSOR.
Cache key includes state, model_version, prompt_version, policy_version, feature_engine_version, market_data_window, risk_policy, and TTL.

## Paper trading
DECISION_CUTOFF required; no look-ahead. Execution simulation must model entry trigger, entry price, slippage, stop-first-or-target-first, partial target, gap, timeout. If intrabar ordering cannot be resolved: RESULT=AMBIGUOUS.

## Baseline experiment
ARM_A=DETERMINISTIC_ONLY; ARM_B=AGENTIC. Both receive same universe, cutoff, fees, position sizing, and execution simulator.
Primary economic metric: incremental_agentic_value = agentic_net_expectancy - deterministic_net_expectancy - agentic_incremental_compute_cost.

## Institutional sequence
NOESIS targeted repair -> DEDALA adversarial rereview -> SYNESIS independent assurance -> FOUNDER architecture freeze -> implementation qualification -> FOUNDER final promotion/merge.
