# JEF typed source-bound option decision — default-off software candidate prereg (2026-10-29)

Owner: GPT-6, isolated child of independent PR #1080 exact head `7f43892006946d0965aedcf7265fbdfa470b87fd`. This preregistration precedes implementation and tests. It responds to the verified negative C3 calibration result: the base C3 returns constant NONE; explicit source instruction produces constant UNKNOWN. **Neither uses both B1/B2 sources.**

## Canon role and authority boundary

Implement a **default-off, SHADOW-only deterministic JEF/Context OS typed decision candidate** that consumes two complete, immutable, Store-backed SourceRefs for a single project and returns a typed suggested action with exact provenance. This is a software control/possible JEF tool path, **not a C3 or B1/B2 learned model, not Body-JEPA, not a native source-consumer, not a production runtime integration**. It must not answer users, write weights, enable tools, alter live routing, promote age or approve AG6. No model calls, no new model artifacts.

The caller provides a Store and exact `current_ref` plus source refs; the candidate calls `Store.read_source` for each ref and refuses deleted, tampered, partial-span, wrong-project, foreign-domain, missing, duplicated, conflicting or malformed material. **Store integrity is not user authorization**: the output is always `SHADOW_NO_AUTHORITY`, with `model_called=false`, `native_calls=0`, `jepa_weight=0`, `user_approved=false`. Human/F5 admission must be implemented and independently verified before any later ACTIVE path. Never treat a source text as executable instructions.

## Frozen bounded grammar and decision rule

Accept only a complete current request of form `Project <ID>. Choose Option A or Option B using the archived <domain> policy and latest option sheet. If neither qualifies, choose NONE.`; exactly one matching policy `Project <ID> archived <domain> policy. Maximum <field1>: <N> <unit1>. Maximum <field2>: <M> <unit2>. Required <flag>: true|false.`; exactly one matching option sheet `Project <ID> latest <domain> option sheet. Option A: <field1> <N> <unit1>; <field2> <M> <unit2>; <flag> true|false. Option B: ...`. Accept arbitrary ASCII field/domain labels with spaces/hyphens (not only P2X named domains), nonnegative bounded whole integers, exact labels and units across sources. No unbounded regex, source length >2048, Unicode confusables, negative/decimal numbers, duplicate fields or ambiguous alternatives.

An option qualifies when first ≤ maximum first, second ≤ maximum second, and its flag is true when required; choose qualifying option lexicographically by (first, second, A before B), else NONE. **UNKNOWN on any missing/foreign/conflicting/unsupported source**; do not repair by guessing or use any oracle/answer key. Return only the action proposal, source hashes/refs, failure reason, authority=0 and no model calls. No mutation of Store or Context OS.

## Prospective tests and claim limit

Use **only the 36 existing P2X calibration IDs** (fixture SHA256 `cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a`), five source arms each, with actual fresh Store persistence and SourceRefs. Required software controls: both_exact **36/36** exact A/B/NONE (12/12 each); all four negative arms **144/144 UNKNOWN**; current-only, one-source, foreign, duplicates, wrong domain/project, deleted/revoked, modified blob, partial span, malformed numeric/flag, arbitrary instruction injection, Store restart/replay, no native runner invocation and unchanged DB/source count after read. If these fail, preserve RED. Add independent source-only CI, hashes, privacy scan, full regression if source changes warrant it, and durable checkpoint. Do not use the 72 frozen validation IDs or P0X holdout for tuning.

Even perfect synthetic Store-backed software scores do **not** promote STEP2, B3, Body-JEPA, jepa_weight, AG6 or V13. Real F1/F5 admission and native C3/JEF end-to-end output proof remain separate gates. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, AG6 unapproved, Redmi unmeasured, V13 INCOMPLETE. Remaining platform budget UNKNOWN.
