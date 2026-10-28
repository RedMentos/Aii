# Run11 heldout scorer role-specific model identity amendment — 2026-10-28

Independent source review after initial scorer implementation, **before changing this protocol**. The original manifest schema had a single `model_sha256` while actual V13 Age0 routes each turn to C3, B1 or B2; #849's 120/2 final runner was B1, not C3. A single C3 SHA across all answers would misrepresent actual model identity and could conceal an unintended model swap.

Amend the candidate manifest contract before any native heldout execution:
- Require `model_catalog_git_blob=7af05962af41d0bc3f7dd18ef01d4eba55eabf99` at manifest level.
- Require per-row `runner_model_sha256`, exactly matching the frozen current catalog for the row's `runner_role`: B1_DETAIL `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`; B2_GIST `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`; C3_LANGUAGE `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.
- Pairing requires same catalog and each row's exact role-specific model identity, **but does not require the same route decision**; route differences must be reported and reviewed, not silently erased. Current B2 two-body default only; a shared-body control needs a separately preregistered cohort.
- Add negative tests for B1 falsely reporting C3 hash, mismatched catalog, and role changes across paired prompt cohorts. A source-level manifest remains unverified external input without independent raw native/model hash evidence.

Frozen 16-item corpus Git blob `ceda0a5cb506cf09885652b24893cf7d8fdff63b` and original #849/#848 evidence unchanged. This amendment is software-only and does not grant tool, learning, age or model-swap authority. All negative gates unchanged.
