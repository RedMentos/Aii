# C6 SHADOW duplicate DRAFT cost/authority gate — prospective preregistration, 2026-10-31

**Base:** verified C6 B1/B2 offer lifecycle audit at commit `6bf46b50cbd9746547e724076b929d42a6b3c4a5`; original Run58/Run59/Canon/seed/model/scorers unchanged. This is a second independent, default-OFF software package, not a new native cohort.

**Risk:** a second call for the same current USER event after one C5/F3/assistant DRAFT can invoke a costly generator and stage additional DRAFT/action rows before C6 notices competing output. Even though output authority is zero, this creates unnecessary work and unusable shadow records. A previous assistant FINAL or a TEXT_REPORT action without a DRAFT must also not be silently ignored.

**Prospective controls and expected outcomes:**
1. First valid Cypress callback stages exactly one DRAFT and one TEXT_REPORT action, still only NEEDS_REAL_TTY preflight.
2. Second invocation on same event returns `EXISTING_OUTPUT_OR_ACTION_RED` **without invoking callback or changing packets/actions/messages counts**.
3. A pre-existing assistant FINAL or orphan TEXT_REPORT action also returns RED before callback.
4. A callback racing a new assistant DRAFT remains refused by downstream C6; do not promise atomic no-duplicate enforcement.
5. A post-stage B1/B2 OfferPacket tamper detected by the lifecycle wrapper returns RED with `shadow_draft_may_exist=True`; do not erase raw DRAFT evidence or return a C6 fingerprint.
6. No TTY approval, delivery, tools, learning, native claim or Runtime installation. Test real SQLite with isolated synthetic CypressBody, original Run58 untouched.

**Evidence:** extend isolated candidate and test; trigger existing CI with pinned upstream source checks, privacy, raw ZIP and private backup. Original first GREEN remains preserved and does not prove this second package. Do not change registered negative gates.
