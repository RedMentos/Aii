# Run14K prereg — source-bound C3 structured six-field fact candidate (2026-10-30)

Owner GPT-6 V13 continuation. Review-only cross-organ JEF/C3 child of Run14J PR #1327 at `6f8957ee0b14deb49f06a131f025167de69fc1c4`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Existing Run13V mux blob `0044a96979db760fdd0c9fe35d6be17152289170`; Run13M source-fact grammar blob `82d1f1e2af5bf565f9d5f081844e1da55c88084c`. Frozen Run13J/K/L/T cohorts and native artifacts, pinned 350M model hash/revision, licenses and all historical negative outcomes remain unchanged.

## Motivation, not a utility claim

Run13T pinned 350M native C3 freeform exact-copy experiment showed 0/8 exact in both baseline/strict and source-facts verified 3/8 vs 0/8 (strict HURT). A constrained **structured extraction** alternative may be easier to verify, but its actual native utility is UNKNOWN until a separately preregistered disjoint native experiment. This package only adds source-bound SHADOW plumbing, no model call or output authority.

## Scope and acceptance

From a verified Run13I JEF snapshot with exact Run13M four-fact answer, build one deterministic bounded user prompt for six typed slots: `project`, `option_a`, `remaining_a`, `option_b`, `remaining_b`, `faster`. C3 candidate must be a single strict JSON object, exactly those keys, no duplicates/extra text/unknown fields, exact names, exact nonnegative integer amounts (not bool), correct faster relation, valid UTF-8 and bounded bytes. No normalization, inference or source-derived claims beyond the four original facts.

Extend Run13V `select_shadow` **only** for candidate JSON that passes source recheck, exact model/output native receipt, deterministic structured user prompt hash **and structured system hash**, and strict slot comparison. On success, return the original trusted JEF answer as selected text with a distinct `C3_STRUCTURED_FACTS_VERIFIED_SHADOW` provenance, never freeform C3 text or JSON. On any mismatch or missing receipt, retain existing JEF fallback; on revoked/tampered source ABSTAIN. Preserve all existing freeform Run13M acceptance, negative gates, native_calls_by_mux=0, Store writes=0, no autonomous chat egress, Age0 RECORD_ONLY. No Runtime wiring or automatic native activation.

Test-first real Runtime SQLite + existing frozen Run13L synthetic Store fixture: exact structured JSON currently falls back (RED); candidate selects source-exact trusted text only with correct native receipt and hashes; wrong numeric/faster/name, duplicate keys, extra fields, markdown, Unicode, wrong model/prompt/system/output hashes fall back; source deletion abstains; no model/Store write. Existing Run13V/W and Run13M tests stay GREEN. Pinned software CI original RED and candidate GREEN, raw CRC/inner hashes/private readback.

This is software/synthetic SHADOW evidence only. A separate preregistered native 350M experiment and independent raw replay are required before any C3 utility inference. STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi unmeasured, V13 incomplete. Next: tests first, source-only implementation, then consider disjoint native structured-vs-copy study with serialized model jobs.
