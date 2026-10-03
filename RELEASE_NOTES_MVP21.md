# MVP-21 — Predictive Treasury Risk Radar

Adds a forward-looking treasury risk radar without turning heuristic signals into fake probabilities.

## Added
- Historical FX regime detection using approved return observations.
- Governed treasury deterioration score (0–1) based on liquidity breach probability, survival horizon, funding concentration, forecast bias, market regime and early-warning signals.
- Three dynamic stress scenarios adjusted to the detected market regime.
- Clear separation between the Monte Carlo buffer-breach probability and the composite deterioration score.
- New API: `GET /api/v1/intelligence/treasury-risk-radar`.

## Controls
- Execution authority remains `NONE`.
- No market-direction trading signal is generated.
- Insufficient historical data is explicitly surfaced.
