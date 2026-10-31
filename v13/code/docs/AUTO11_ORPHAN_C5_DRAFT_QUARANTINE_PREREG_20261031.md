# Auto11 fourth package — same-process orphan SHADOW DRAFT quarantine (2026-10-31)

Owner GPT-6 automation; isolated review child of PR #1450 exact `b677619888f8d0cf2d0ca8f68341c6dd38423cd3`, after 84/84 software GREEN with raw and private backup. No active Run85/87 native owner touched.

**Problem:** after C5/F3 SHADOW_DRAFT transaction commits, a newer USER, source revocation or C6 metadata tamper may cause a RED return while leaving an assistant DRAFT active in the same process. Frozen Store startup quarantines DRAFT to INTERRUPTED on restart, but no restart may occur for hours. No visible output is authorized, yet an active DRAFT is an avoidable stale state.

**Prospective behavior:** on a verified post-stage RED, atomically mark only the exactly identified same-event/session assistant DRAFT as `INTERRUPTED` and its own `SHADOW_DRAFT` action as `SHADOW_QUARANTINED`. Preserve original message text/metadata, source refs, C5/F3 packets and action expected/outcome; no delete, no tool dispatch, no FINAL, no TTY. Never alter a foreign event/action or a tampered DISPATCHED action; report `quarantine_complete=False` instead of faking containment. A successful preflight remains DRAFT + SHADOW_DRAFT. Repeat quarantine is idempotent and only updates statuses. Poststage race after the final read-only check still possible; do not claim perfect atomic delivery isolation.

**Acceptance:** real SQLite negative tests for newer USER immediately after staging, C6 text/metadata tamper, changed source after C6, action-status tamper, idempotent quarantine, no foreign row mutation, original evidence unchanged and zero FINAL/tool/learning. Retain all original RED/GREEN and prereg before code. No changes to Store, Runtime, Canon, native cohorts, model/seed pins or approval gates.

**Negative gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; Run70/77 RED; historical full-suite RED; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete.
