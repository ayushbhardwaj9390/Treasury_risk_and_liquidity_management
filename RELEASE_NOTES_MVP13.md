# MVP-13 Release Notes — Deep Liquidity-Risk Intelligence

## Scope
MVP-13 deepens the treasury platform around liquidity-risk concentration, probability, attribution and action readiness without adding execution authority.

## New deterministic engines
1. **Liquidity Concentration & Transferability Engine**
   - legal-entity, bank and currency concentration
   - top-share and HHI metrics
   - trapped-cash share and transferability ratio kept separate
2. **Probabilistic Weekly Liquidity Path Engine**
   - seeded Monte Carlo weekly paths
   - probability of any buffer breach
   - P05 / median / P95 minimum headroom
   - expected breach week and 95% tail funding need
3. **Liquidity Stress Attribution Engine**
   - collections, payables, facility, FX, rates, collateral and refinancing attribution
   - interaction residual for non-linear overlap
   - FX value shock does not become cash loss without a modeled transmission channel
4. **Forecast Driver Concentration Engine**
   - probability-weighted receivable drivers
   - contractual payable drivers
   - largest and top-five dependency shares
5. **Liquidity Action Playbook Engine**
   - inherits sequential contingency funding capacities
   - working-capital and new-funding actions remain unquantified until evidenced
   - execution authority remains NONE

## Multi-agent changes
- Registered specialist agents: **68**
- New agents:
  - Liquidity Concentration Agent
  - Probabilistic Liquidity Path Agent
  - Liquidity Stress Attribution Agent
  - Forecast Driver Concentration Agent
  - Liquidity Action Playbook Agent
- Heavy probabilistic / attribution / playbook agents are deployed **on-demand** rather than on every summary refresh.
- GPT-6 Astra specialist-profile coverage now matches all 68 registered agents.
- Liquidity-focused multi-agent questions automatically route the on-demand liquidity specialists when material.

## New APIs
- `GET /api/v1/liquidity/concentration`
- `GET /api/v1/liquidity/probabilistic-path`
- `POST /api/v1/liquidity/stress-attribution`
- `GET /api/v1/liquidity/forecast-drivers`
- `GET /api/v1/liquidity/action-playbook`

## Verification
- 92 backend tests collected after MVP-13 additions.
- 85 non-summary regression tests passed in one clean-database run.
- 6 orchestration-summary regression tests passed separately.
- 1 new on-demand Astra-routing regression test passed separately.
- Python compilation passed.
- Frontend TypeScript source check passed using temporary local dependency stubs; a complete Next.js production build still requires the normal npm dependency installation.

## Control boundary
AI and optimization remain advisory. No MVP-13 engine can create, approve, release or execute a treasury transaction.
