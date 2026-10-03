# Global Treasury AI — MVP-12 Release Notes

## Enterprise Liquidity Command + Predictive Balance-Sheet Intelligence

MVP-12 deepens the platform's core mission: treasury risk and liquidity risk for a multinational enterprise.

### New deterministic engines
1. Structural Liquidity Maturity Ladder
2. Interest Rate Gap & DV01 Proxy
3. Funding Tenor Resilience Optimization
4. Cross-Currency Funding Structuring
5. Contingency Funding Plan
6. Treasury Early-Warning Indicators
7. Predictive Balance-Sheet Treasury Twin

### New specialist agents
- Structural Liquidity Gap Agent
- Interest Rate Gap & DV01 Agent
- Funding Tenor Optimization Agent
- Cross-Currency Funding Structuring Agent
- Contingency Funding Plan Agent
- Treasury Early Warning Agent
- Predictive Balance-Sheet Twin Agent

Runtime total: **63 specialist agents**.

### Control principles
- committed facilities are contingent liquidity, not cash
- residual floating-rate cash sensitivity is separate from DV01
- funding-tenor output does not invent pricing
- cross-currency funding requires live pricing and tax/regulatory review
- contingency capacity is allocated sequentially to limit double counting
- EWI thresholds are governed inputs, not LLM judgments
- balance-sheet twin is a treasury simulation, not an accounting forecast
- AI / optimizers retain **execution authority = NONE**

### Verification
- 85 backend tests passed across clean-database regression blocks
- 7 dedicated MVP-12 tests passed
- Python compilation passed
- frontend TypeScript source passed with local dependency declaration stubs
- no new schema migration required
