# V13 verified exact-source budget answer — review candidate (2026-10-29)

Parent PR #1141 review branch head `0cbf94d8d3a53f70044f4905fbf7a18970d91390`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. This is a new functional **source-exact** operator lane, not a learned language ability, not a change to registered C3 heldout cohort, and not a production merge.

## Problem

Existing `:verified <Frage>` is only a F1/F5 authorization preflight (`READY`), while opt-in native C3 output may still produce unsupported numbers. The independently audited six-case native C3-only heldout in PR #1138 was English 3/3 and German 0/3. A user needs an explicit, deterministic answer option for an **already verified, human-authored project-budget source** without pretending C3 learned German.

## Contract

Add `:verified exact <Frage>`, local `OPERATOR_TTY` only. The existing `:verified <Frage>` must stay preflight-only and existing `--native` refusal unchanged. Call the existing `_preflight` and F1/F5 `verified_recall_messages` path; if missing, conflicting, tampered, revoked, wrong-session or wrong-project, return `CLARIFY` with no sourced amount. Only render the canonical project name and whole-Euro amount from the **admitted SourceRef**, never model output or untrusted question content. Re-run full preflight after formatting and suppress the answer if the source/decision changes. Output is `FINAL_SOURCE_EXACT`, `authority=EXACT_SOURCE`, `learned=false`, `native_calls=0` (no C3 generation). If semantic recall is enabled, it may use the existing encoder; do not claim zero possible retrieval-model calls. No tool/age/learning authority.

Software tests: English and German authored source exact answer, default preflight unchanged, missing/conflicting/revoked sources, revocation between checks, malformed invocation, and no C3 native call. Compare original RED vs isolated candidate GREEN with exact source/test hashes; run original source-consumer and operator regression tests. Existing registered native cohort/model/seed pins unchanged. No STEP2/B3/Body-JEPA/LP3 or whole-system promotion.

The two preflight checks narrow but do not prove elimination of every concurrent source mutation window. Never claim atomic source authorization without a transactional lock/revalidation proof.
