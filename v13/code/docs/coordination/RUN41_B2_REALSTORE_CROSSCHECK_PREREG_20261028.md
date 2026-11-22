# Run41 — real V13 Store/Runtime read-only B2 source bridge cross-check prereg (2026-10-28)

**Parent:** Run40 review-only PR #948 exact head `2d8740f8086e66991d151250a07951f6651fed71`. This prereg precedes any Run41 test source. No production Runtime/Store/cognition edits, model download, native execution, original TP/s27 changes or gate promotion.

**Question:** Does the Run40 SQLite read-only history adapter work with the *actual* V13 Store and validated OfferPacket schema, rather than only a synthetic in-memory table layout? A false-positive from a simplified SQL fixture would invalidate its claim of being a usable candidate.

**Predeclared tests:** instantiate a temporary `Runtime` (software-only), persist a B2 old project rule note with its binding rules beyond 240 characters, then at least five same-project supplier sheet turns with validated `OfferPacket` records and `Cognition.retain_body_offer`, causing the first rule note to leave the four-slot retained B2 state. Call `run40.select_from_store` on a later real `Store.event` with the same session/generation/model; assert the exact old rule SourceRef and excerpt are returned and no rows, B2 state, or generation changed. Repeat with the old rule source explicitly tombstoned; assert it is excluded. The selected source remains `SOURCE_POINTER_ONLY_SHADOW` and `PRIOR_HYPOTHESIS_NOT_FACT`; no C3 answer or quote authority.

**Evidence:** new isolated `tests/test_run41_b2_realstore_crosscheck.py`, no source changes. CI runs focused real Store tests after installing the same pinned Python dependencies as the parent full suite, then the full suite, privacy and diff, preserving SHA256SUMS and exit logs. This does not establish Linux-native inference, Redmi, B2 quote generation, C3 utility or STEP2. Failed attempts are retained.

**Gates:** Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi unmeasured, V13 incomplete. Platform budget UNKNOWN.
