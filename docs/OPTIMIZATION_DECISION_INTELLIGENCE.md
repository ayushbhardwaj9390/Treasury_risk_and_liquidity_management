# MVP-9 Optimization & Decision Intelligence

## Purpose
Turn validated treasury-risk outputs into governed **strategy alternatives** without granting the optimizer or LLM authority to transact.

## Engines
1. **Portfolio Hedge Optimization**: converts policy-compliant target hedge ratios into incremental notional requirements and an explicit forward/option mix using user-supplied cost assumptions.
2. **Contingency Funding Allocation**: allocates modelled tail funding need first to a capped portion of transferable cash, then to committed external capacity. Intercompany lines remain structuring options to prevent liquidity double counting.
3. **Cash-Pool Optimization**: matches pool-member contribution capacity against funding needs and creates non-executable sweep proposals.
4. **Scenario Search**: evaluates 324 configured combinations across collections, payables, facility availability, FX shocks and rate shocks, while reusing cached deterministic components for low latency.
5. **Treasury Decision Pack**: compares three policy profiles: Liquidity Preservation, Balanced, and Risk Reduction.

## Decision boundary
The decision pack has no write path to payments or derivatives. A strategy must still pass pricing, tax/legal review, policy checks, maker-checker approval, release controls and external acknowledgement.

## Current data limitation
The committed-facility master currently lacks executable funding spreads. Therefore MVP-9 ranks committed facilities by available liquidity capacity, **not by claimed all-in economic cost**. Production deployment should add facility pricing curves, fees, utilization pricing, commitment fees, tax effects and optionality costs before cost-optimal funding selection.
