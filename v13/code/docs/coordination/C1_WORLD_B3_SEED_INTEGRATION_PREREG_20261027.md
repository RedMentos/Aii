# C1 + World-JEPA + B3 paired-seed integration — preregistration (2026-10-27)

Review-only integration; no production merge or device authority. Owner GPT coordinator. Base C1+World PR #780 exact `3a3892a8525f51e0dab914b4a58e44a7ac4c3017`; independent B3 L1 + seed-identity child of PR #781 currently at `38d76f8fee75cc19c554fdf880074f738744a1b6`. The two branches share ancestor `87dd02f82abdcc3762029dac3ea8170c9db30e7c`.

## Disjoint-source proof and integration strategy

GitHub compare from the shared ancestor shows PR #780 modifies only C1 provenance source `v13/code/v13/executive.py`, two C1 tests, and C1 coordination/workflow files. B3 review changes `v13/code/v13/b3bridge.py`, B3 test fixtures, B3 coordination/workflows. **No overlapping changed paths**. Build a two-parent review merge tree with the complete PR #780 tree plus all B3 branch changed paths, preserving exact blob SHA values from each side. No force-push, no source rewriting, no production promotion.

## Falsifiable checks

1. Both parent SHAs are present; merge-tree blobs match exact PR #780 C1 and exact B3 seed-identity source/test blobs.
2. Focused combined tests cover C1 goal/question provenance and B3 L1 seed identities, including negative/mismatched controls.
3. Full `unittest discover -s tests -p 'test_*.py' -q` must pass; compileall, privacy scan against shared ancestor and `git diff --check` must pass.
4. Original B3 L1 native `FAIL`, STEP2 `UTILITY_FAIL`, LP1/LP2/BJ1 negatives, `jepa_weight=0`, Age0, no native receiver/Redmi proof. No partial software integration is proof of learned utility.
5. Preserve raw CI exits and ZIP with hashes and private backup. Any failure remains visible and blocks integration claim.

Next: construct two-parent merge candidate, run focused + full source-wide CI, independently review before any further upstream integration. No auto-merge.
