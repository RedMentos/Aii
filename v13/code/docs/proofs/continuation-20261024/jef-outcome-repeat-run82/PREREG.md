# Run82 prereg — bounded JEF FINAL outcome replay idempotence

2026-10-24. Base Run81 PR114 `3b8258a9cb1df5e25d3f992d2e3e65ed09a89024`.
Owner: `v13/code/v13/jefoutcome.py`, `v13/code/tests/test_jefoutcome.py`, Run82 evidence only. Do not modify other owners' code or model/native artifacts.

Problem: repeated `jefoutcome.after_turn` for the same FINAL event can append another (event_id, component) label and create a new outcome source. Repeated callbacks/recovery inflate self-learning reports and may reinsert a stale skill label after a human route correction.

Test-first RED: duplicate FINAL callback for same event/targets must not grow the retained label ledger or create another self-label source; a later different target for the same event must not silently overwrite the first; after route correction to skill='none', a repeated FINAL must not restore 'skill'. Distinct events with identical targets still create distinct labels. Preserve explicit human precedence and RECORD default.

Fix: precheck the retained event+component ledger before source creation, then atomically recheck inside Store state CAS before adding labels. Only newly committed labels count in return/log. This is **bounded idempotence within the retained MAX=1024 ledger**, not a claim of global forever-exactly-once across eviction; durable beyond-window dedup remains a separate acceptance question.

Run existing 373-test Linux CI plus new tests and official privacy scan. Preserve original RED, any fixture errors and GREEN logs. No native/Redmi or STEP2/B3/JEPA gate promotion.
