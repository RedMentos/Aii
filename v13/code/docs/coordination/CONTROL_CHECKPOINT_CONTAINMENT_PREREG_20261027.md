# WP-T14 control checkpoint accounting containment — preregistration (2026-10-27)

## Lineage and file ownership
- Review-only child of PR #763 exact parent `54e6d42e483cd1a15eec6e00e27a7672632db574` (not main; no auto-merge).
- Frozen prechange `v13/code/v13/control_budget.py` blob `f2beff6b2b3df4c1a98a4763e6ec93e17a8dabfa`. Existing row-integrity fix, limits and stage-marks remain.
- Owned files: `v13/control_budget.py`, new checkpoint containment test, dedicated workflow, proof note. No registered model/source/seed/SSOT edits.

## Counterexample and expected RED
`checkpoints()` claims to measure approved checkpoint paths under `home/checkpoints` but counts any existing `.npz/.gguf/.safetensors` path outside `home/models`, including absolute external paths, `../` traversal, symlink targets and aliases of the same file. This can inflate reported control parameter bytes and leak an external filesystem path in the operator report. It is not an authorization or SHA verification function, so a positive count must never be called an approval proof.

## Locked tests
- A real regular file inside `home/checkpoints` counts once.
- Absolute external, relative `../` traversal and `home/models` paths do not count.
- Final symlink to external file and symlinked intermediate directory outside root do not count.
- Same real file referenced as absolute and relative counts once (canonical identity).
- Original WP-T14 budget/finite-mark/row-integrity tests remain green; no threshold or native evidence changes.
- Test-only RED then minimal GREEN, focused and full software, source-bound raw logs/hashes/privacy/diff, all failed attempts preserved.

## Proposed containment
Resolve `home/checkpoints` and each candidate strictly, require canonical candidate to remain under that root, refuse symlinked candidates/parents, require regular file, deduplicate by canonical path. Report a relative checkpoint path and bytes only; never read file content or claim hash approval. No writes, no new permissions, no changed Age/learning gates.

## Claim limits
This is **accounting integrity only**, not proof that a generation artifact is approved or SHA verified. Actual checkpoint approval, model generation binding, native/Redmi memory and thermal measurements remain separate. LP1/LP2/BJ1/STEP2/B3 negatives, jepa_weight0, Age authority0 and whole V13 incomplete remain.
