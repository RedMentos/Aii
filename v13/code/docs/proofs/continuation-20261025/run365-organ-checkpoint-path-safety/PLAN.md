# Run365 — organ checkpoint path and identity confinement (preregistered)

Parent reviewed branch: `assistant/run364-plain-ui-cursor-20261025` @ `4616bb0618b7ff64969df6f1af369da723f5da3e`.
Target production blob `v13/code/v13/organ.py`: `798a5b6ba7979b8c31cbcaee01a496dad2bb8ef3`.
Owner for this package only: `v13/code/v13/organ.py`, `v13/code/tests/test_organ_path_safety_run365.py`, `.github/workflows/run365-organ-path-safety.yml`, this proof directory. No concurrent edits to BUILD_STATE, shared handoff, model artifacts or other owners' files.

## Observed source-level defect and expected RED
`snapshot(r, role)` uses the operator-provided role as a filesystem path component before validating it. `members` also accepts arbitrary role strings, while `_load(r,sid)` embeds an unchecked user-provided glob expression in the manifest search. Thus a role like `../../escaped` can create a checkpoint outside the intended `organs` directory, and `*` may resolve a different snapshot than the requested ID. The manifest hash alone does not bind its role and ID to its parent directory.

## Precommitted tests
1. Invalid/relative role and unknown role must be rejected before any directory is created outside the organ checkpoint root.
2. Malformed or wildcard snapshot IDs must be rejected, even if exactly one legitimate snapshot exists.
3. A hash-consistent but identity-mismatched manifest must be rejected.
4. A symlinked organ root escaping the runtime home must be rejected.
5. Existing valid B1/C2 snapshot, check, restore tests must continue passing.

RED expected on unpatched source; GREEN requires a narrow role allowlist from existing model roles, generated-ID validation, manifest path/identity binding and home containment. Do not change age, learning, permission, original cohorts, evidence level or V13 gates.

## Execution/evidence plan
Run exact-head GitHub Actions with isolated pinned Python dependencies and `python -m unittest -v tests.test_organ_path_safety_run365 tests.test_organ`; capture raw logs, source SHA and official public privacy scan. Preserve RED and GREEN Actions run IDs, exact source heads and outcomes. Software-only SQLite proof; native/Redmi not attempted. No completion promotion.
