# Auto11 fifth package — C5 SHADOW action outcome / visible-output integrity (2026-10-31)

Owner GPT-6 automation; isolated review child of PR #1451 exact `94ac048ace8c8723fadb3b3332140f17c3ffb3a9`, after verified 97/97 software GREEN and private raw backup. Native owners Run85/Run87 untouched.

**Problem:** strict `_c5_shadow` currently authenticates action status SHADOW_DRAFT and C5/F3 packet binding, but does not read the action `outcome` column. An accidental or malicious write to `actions.outcome` while leaving status SHADOW_DRAFT could pass C6 integrity. Similarly a second FINAL/OUTPUT_COMMITTED/STREAMING assistant message for the same event should never coexist with a source-only SHADOW DRAFT and pass the strict C5/F3 verifier.

**Prospective change:** in isolated `c5_shadow_action_binding.py`, require exact `outcome IS NULL` and zero assistant messages with statuses FINAL, OUTPUT_COMMITTED or STREAMING for the same event/session. Keep all original strict Run49 C5/F3 packet checks and SHADOW_DRAFT status, no output permission, no Store/runtime mutation. Add real SQLite adversarial tests for outcome tamper, competing FINAL/OUTPUT_COMMITTED/STREAMING, valid outcome-null path and C6 fail-closed. Existing 97 software tests retained; pinned isolated workflow, privacy/diff and raw hashes. No native/Redmi or whole-system promotion.

**Negative gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; Run70/77 scientific RED; historical full-suite RED; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete.
