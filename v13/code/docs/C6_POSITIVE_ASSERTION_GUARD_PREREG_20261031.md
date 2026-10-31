# C6 positive budget assertion SHADOW guard — prereg 2026-10-31

Owner GPT-6, independent review-only sibling of active Run54 (#1392), based on verified C6 PR #1391 exact `7f21f779d5750e769bb77aac2aae5f40fd72afce`. Frozen original C6 preflight (`295702496d94e84113f253cc3a09d71aba3b1e34`), temporal draft, Store, Runtime, Canon, Run51 fixture/seed and native evidence unchanged.

## Concrete failure hypothesis
The original C6 preflight verifies presence of a project name and one exact number, not whether that number is positively asserted **as that project's budget**. A candidate such as `Project Cypress budget is not 64 Euro.`, `Project Lark budget is 64 Euro. Project Cypress is unrelated.`, or `Project Cypress budget is 64 Euro. Project Lark is unrelated.` can pass its bounded lexical gate. This is not a claim about native generation frequency.

## Predeclared isolated implementation
Add a **default-OFF**, no-output, no-commit strict lexical positive-assertion adapter. It first requires original read-only C6 preflight `NEEDS_REAL_TTY_APPROVAL`; then re-reads the current exact F1/F5 source and stored DRAFT, requires the *entire* answer to be one affirmative sentence asserting the bound project's integer Euro budget, and re-runs the original preflight. Only two tightly scoped English/German assertion forms are allowed; unsupported wording fails closed rather than pretending to prove general semantics. No model calls, output, tools, writes, learning or human-approval tokens. The returned fingerprint remains explicitly **not** consent. No Runtime integration.

## Frozen test plan
Real SQLite/Memory fixture Run51 seed467: valid `Project Cypress budget is 64 Euro.` and `The budget for Project Cypress is 64 EUR.` pass; explicit negation, another-project budget plus unrelated Cypress mention, unrelated second-project claim, appended uncertainty, appended tool claim, question, changed amount, revoked source, forged approval and opt-out fail. Record where original C6 returns `NEEDS_REAL_TTY_APPROVAL` for negative controls, and verify strict guard refuses, no DB writes and no candidate text in result. Re-run original C6 and F1/F5 focused tests, compileall, privacy diff. No new native, Redmi or semantic-utility proof.

Negative gates unchanged: Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no production merge or C6 delivery. A future real TTY-origin consent and transactional commit path requires separate preregistration and approval.