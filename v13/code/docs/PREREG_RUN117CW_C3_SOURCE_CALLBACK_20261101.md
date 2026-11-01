# Run117CW prereg — real Store source-only C3 callback boundary

2026-11-01. Review-only independent sibling of Run117CV native model-capacity pilot, base Run117CU `39605b586e4bc3a961ab8449f6d8cd31c1f965f8`. This document is committed before code or tests. Do not mutate Run117CV native owner, frozen Canon, cohorts or existing runtime.

## Concrete functional gap

Run117CM/CU proves source-only F1/F5/JEF prompt construction with real SQLite but **not** a live C3 model callback with source recheck after generation. A source can be forgotten, superseded, or a new USER event can arrive during a long model response. A returned C3 action must never gain even SHADOW readout authority from a stale source; callback side effects also need detection. This candidate is an **isolated default-OFF source-only callback adapter** (not production Runtime._turn).

## Fixed tests and acceptance

Build existing `jef_c3_source_only_shadow_candidate.build` twice around exactly one caller-provided callback, retaining the real Store and memory open. Pass a copied two-message source-only prompt and frozen Run68 action JSON schema. Accept only strict JSON object `{"action":"A"|"B"|"NONE"}` (no duplicate keys, extra keys, non-finite constants, oversized output, markdown or commentary). Validate unchanged prompt hash, source role text, exact source refs, latest authoritative USER, session and human memory lineage, and unchanged Store action/message counts after callback. On revocation, source edit, replacement memory, new current USER, callback exception or mutation: fail closed with no model output/parsed action, zero delivery/tool/learning authority. Successful callback may yield a **non-delivering SHADOW action** only, never a claim of independent reasoning or native execution. A callback is untrusted; real native model and process proof remain separate.

Use actual Runtime/Store/Memory SQLite and synthetic callbacks for positive and adversarial tests. Verify a restart and revoked source negative path. No real model call, no Redmi measurement, no native C2/B1/B2, no age promotion. Original Run117CU/CN and Run117CM tests must remain unchanged and passing. Save original RED/GREEN software logs and source hashes, review branch checkpoint and private backup if available.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; `jepa_weight=0`; whole system incomplete.
