# JEF N3 duplicate human rating guard — preregistration 2026-10-30

Base: PR #1167, verified branch checkpoint `8c9ff4b0a86371bff8d6468c0e2b1f21247c85bf`. Review-only child. Ownership: `v13/code/v13/jefbridge.py`, new tests, new CI workflow and this evidence. No concurrent modifications of another owner's files, no frozen cohort/model/seed change.

## Problem
`inputs.record_rating` retains at most one answer rating per (event, origin), replacing later notes. However its JEF `on_rating` hook calls `JEFBridge.outcome` on each receipt; identical repeated human feedback currently runs another SGD update, inflating learning despite no new label. The operator `:jef outcome` has the same issue.

## Scope and frozen behavior
Only *identical* human feedback to the same event and source is made exactly-once across controller instances and restarts. Different explicit utility values remain additional corrective updates under the existing online policy; this package does **not** claim to implement replacement/rollback of old gradients. Existing internal cross-check labels, turn learning, query/observer stats and mode remain unchanged. The new receipt ledger is bounded to retained turns and written in the same CAS transaction as weights; no extra database state or autonomous authority.

## Predeclared tests
- One selected-offer turn, two identical direct human outcomes: first updates one offer, second updates zero; weights and update count unchanged on duplicate.
- A fresh JEFBridge instance on the same Store still recognizes the duplicate; a different utility on the same event may update once under the existing policy; repeating that new utility is again a no-op.
- Two different event IDs with the same score each update their own selected offer; no global score-based deduplication.
- Retained receipts are bounded by `TURNS_KEEP`; a turn falling outside the retained window does not become trainable by resubmission.
- Explicit `:jef outcome` same-session repeated command is idempotent; foreign/invalid values remain refused by PR #1167.
- Run focused `tests.test_jefbridge`, `tests.test_jef_operator_session_20261030`, new tests, Canon SHA, privacy, diff, compile; close raw CI with SHA256SUMS. No native models or gate promotion.

## Open after package
True latest-only gradient replacement for revised `:note` labels remains a separate registered design/evidence task; do not imply that an online second SGD step is an inverse of the first.
