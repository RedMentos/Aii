# Run22 preregistration — AG12 read-only English/German comparison (2026-10-30)

Owner: GPT-6 scheduled continuation. Exact review parent Run21 PR #1348, head `b02a73917bdb2b5aa451890e41af988c83bb2f5f`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.

## User goal / observed gap
The user requires English-first development followed by *observable* German learning. AG12 already has separate persistent English and German procedural suites, but `:growth eval` only shows the English state. There is no single operator readout that safely compares both persisted suites without registering/mutating the missing language. Comparing unrelated generations, stale seeds, partial runs or corrupted scores would falsely suggest transfer.

## Scope and predeclared behavior
Create a read-only AG12 comparison module and `:growth eval compare en-de [solver]` operator route. Only compare complete, persisted, source-checked EN/DE runs for the same requested solver, exact suite seed/hash and same generation. Validate historical holdout integrity, exact completed item counts and finite score metrics. Return explicit NOT_MEASURED / INCOMPLETE / SUITE_MISMATCH / GENERATION_MISMATCH / INVALID states instead of silently substituting runs. Do not create a German suite or run a model on a read-only query.

Test first on real Runtime/SQLite: English-only comparison leaves DE state absent and unchanged; English+German runs yield descriptive deltas, persist across restart and leave EN/DE state versions unchanged; partial/mismatched-generation/corrupt inputs cannot produce a comparable result; `:growth eval compare en-de` exposes only summary metrics, not prompts or answers. Negative controls should fail against original code (no comparison route).

## Claim limits
A cross-language score difference is **not proof of learned German transfer**: prompts/word sets differ and per-run model/source revision is not bound. Report diagnostic-only status and this limitation. Preserve all original holdout exclusions and Age0 RECORD_ONLY; no AG6 approval, native/Redmi, STEP2/B3/Body-JEPA/JEPA promotion. No change to registered source/model/seed cohorts.
