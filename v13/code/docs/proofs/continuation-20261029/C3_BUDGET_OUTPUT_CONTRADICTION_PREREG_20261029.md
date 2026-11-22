# C3 F1/F5 native budget-answer contradiction gate — preregistration (2026-10-29)

Parent review-only PR #1144 at `de9bd8206cb6294187f42ca46c20ea5434b43fd1`, preserving PR #1143 deterministic CLI, World-Model integrity, Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

## Problem
The opt-in `scripts/ask_verified_budget._answer_uses_euro_source()` currently checks for the exact amount, one matching EUR/Euro token, absence of extra different numbers, and foreign project names. It can still accept a contradictory generated answer such as `Project Elyra budget is not 615 Euro.`, or `615 Euro and 615 dollars` (same numeral in a foreign currency), and return `FINAL` after one native C3 call. This is not a source-grounded factual answer.

## Frozen tests before source change
1. Valid `The budget for Project Elyra is 615 Euro.`, `615 Euros.`, `Projekt Elyra: 615 EUR.` remain accepted.
2. Contradictions/negations `is not 615 Euro`, `615 Euro is wrong`, `615 Euro? No`, `615 Euro is unverified` are rejected.
3. Same-numeral foreign currencies `615 Euro and 615 dollars`, `615 Euro but 615 USD`, `615 Euro and 615 GBP` are rejected, even though no new numeric token is present.
4. Integrated fake native C3 with a verified F1/F5 source and one generated contradictory answer returns `UNVERIFIED_NATIVE_ANSWER`, no `answer`, one native call and proven process unload; no extra native calls.
5. Existing `tests.test_ask_verified_budget` and `tests.test_verified_exact_standalone_cli_20261029` remain green. Source-exact deterministic CLI is unaffected.

Implementation: conservative post-generation output veto for explicit negation/uncertainty, interrogatives, and foreign currencies. Do not change preregistered native model/seed/source hashes, memory admission, output rendering, age/learning gates or native call count. False negatives are acceptable for this opt-in factual lane; do not pretend this regex provides semantic proof or general fact-checking. Software fake runner only, no native/Redmi gate promotion.
