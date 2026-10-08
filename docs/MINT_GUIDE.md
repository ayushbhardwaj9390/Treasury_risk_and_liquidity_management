# Mint interface guide

Mint provides curated, instant help for all 13 treasury workspaces. It does not
call a language model or inspect uploaded files, company records or live report values.

## Using Mint

- Open Mint from the corner of any workspace.
- Screen guide shows one instruction at a time. Previous/Next moves through that
  screen's instructions; Show all instructions displays the complete list.
- Browse workspace guides opens the chosen workspace and updates its guide.
- Ask Mint explains controls, concepts and common errors. Suggested questions follow
  the current screen. Follow-up examples/details use the last topic only when it
  belongs to the current workspace. Earlier conversation remains labelled by screen.
- Full app tour opens the workspaces in sequence. It never fills or submits forms.
- Escape or Close Mint guide closes help and returns focus to the launcher.

Help, questions and tour are separate modes to keep instructions and conversation
from competing for screen space. Conversation is capped at the latest 12 exchanges
and 300 characters per question; reloading clears it. Unmatched questions receive
an explicit fallback rather than an invented answer. No confidential data is needed.

## Boundaries

Mint describes workflow requirements, including role eligibility, evidence and
sign-offs, but cannot approve, activate sources, execute financial actions or
certify company readiness. The five GPT-6 Astra reasoning teams and deterministic
treasury engines are separate. Public demo saves stay disabled; real backend,
identity, provider evidence and production controls remain required.

## Verification

Curated routing tests cover screen questions, specialist topics, examples, errors,
privacy and execution boundaries. Browser smoke checks cover mode switching,
instruction navigation, workspace selection, tour navigation, questions, context
changes, keyboard dismissal and responsive layout. Verification results are recorded
in PROJECT_STATUS.md for the release. Real company login remains externally blocked.

Release verification — 8 October 2026: code commit `23faf5c` passed all 68 frontend
regressions and full Linux backend/frontend CI, including migrations and audits:
https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37733985201.
All 13 local guide selections and tour stops passed browser checks, together with
instruction navigation, scoped follow-ups, risk examples, clear conversation and
Escape focus restoration. The published app passed guide/tour navigation,
seven-step governance instructions and actual 390px mobile checks without page-wide
overflow. Mint remains curated help; hosted identity and external evidence are
unavailable and are not claimed verified.
