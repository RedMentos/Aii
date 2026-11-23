# V13 C3 operator bounded local input and native failure provenance — prereg 2026-10-30

Review-only software child of #1228 exact `f9625470aa1ee67ea4356d36a3be8d16a84835e7`. Native operator probe #1229 runs independently on its own pinned source/branch; do not touch its fixture, model, runner or cohort. File ownership: only `v13/code/scripts/listarith_de_operator_shadow.py`, new tests/workflow/scoped proof.

Two observed risks in current operator: `_read_text()` first checks `Path.is_file()` (follows symlinks) then unconditionally `Path.read_bytes()` before enforcing max size, so a 6-GB Redmi can allocate arbitrarily large input and operator can unexpectedly follow symlinks. Also the quarantine code overwrites `error_type` with `NATIVE_RECEIPT_UNVERIFIED` and loses the native-reported error type from the original failed attempt.

Acceptance: use bounded read `max_bytes+1` from an opened regular file, reject symlinks and special files, reject pre-existing oversized files without unbounded reads, preserve exact bytes/UTF-8 semantics and no stdout raw. Keep source/report SHA and 0600 exclusive output. Preserve native original error in a separate typed field when quarantining a malformed raw receipt; never promote raw to SHADOW_RESULT. Adversarial tests first, original RED then fixed GREEN and private raw ZIP. No model execution, live ToolStep/C5, Age/learning changes or gate promotion.

Gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi UNMEASURED, whole-system INCOMPLETE. Native probe #1229 is a separate evidence grade and must not be inferred from these tests.
