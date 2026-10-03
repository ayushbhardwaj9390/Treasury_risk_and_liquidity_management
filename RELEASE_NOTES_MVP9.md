# MVP-9 Release Notes

## Global Treasury Optimization & Decision Intelligence

MVP-9 adds an advisory optimization layer to the existing institutional treasury-risk platform.

### Added
- Portfolio FX hedge optimization constrained by configured policy bands
- Explicit hedge execution-cost assumptions and no invented market quotes
- Tail-liquidity contingency funding allocation
- Double-counting protection for intercompany funding structures
- Cash-pool sweep optimization with non-executable proposal status
- Cached 324-combination multi-factor scenario search
- Three-strategy treasury decision pack
- Six optimization/decision specialist agents
- Optimization context supplied to GPT-6 Astra synthesis
- MVP-9 command-centre sections

### Controls
- AI/optimizer execution authority: **NONE**
- Human approval: **REQUIRED**
- Unmatched derivative exposure is not extended by the optimizer
- Scenario breach count is not interpreted as probability
- Missing facility pricing is surfaced instead of fabricated
- Trapped cash is excluded from transferable funding capacity

### Verification
- 65/65 backend tests passing on a clean SQLite demo database
- Python compile check passing
- Frontend TypeScript source passes local dependency-stub type checking
- No new database migration required for MVP-9
