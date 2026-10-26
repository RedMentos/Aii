# Run404 — stage2 P_s20 native continuation preparation, NO native launch yet

2026-10-26. Owner GPT continuation. Base Run403/PR398 `c95cf7469f8f6aa123ad782f503b386dac3ec703`, stacked review, not main. Own only new `scripts/run404_stage2_resume.py`, `tests/test_run404_stage2_resume.py`, source-only CI and this proof folder. Frozen Run394/395/397/native runtime/model sources untouched. Run401/PR396 `O_s20` native job `40250662450` is still active at planning time; no competing heavy job permitted.

## Exact prerequisite

Run401 stage1 artifact ID and digest are **UNKNOWN** until Actions completes; do not invent, prefill or guess. Run402 safe archive restore is source-tested but not yet verified on actual Run401 artifact. Run403 full 378-row auditor is source-tested, not native.

## Scope

Build an opt-in CLI for the **next** native stage:
1. Require observed Run401 artifact ZIP and exact SHA; Run402 verifies and atomically restores into fresh work dir. Preview mode verifies O_s20 receipt **without** inference or rewriting the work tree.
2. Native execution requires explicit `--execute` plus exact installed model/runner home; call unchanged Run397 `--full --execute --max-new-arms 1`, expected next arm P_s20 only. Validate O and P native receipts (84 rows total), all remaining seven arms pending, no canonical gate promotion. If native fails, preserve failed attempt and report RED; never silently restart or overwrite.
3. Source-only adversarial tests use synthetic archive/receipts and mocks only; actual stage2 cannot be claimed before observed Run401 artifact and a separate serialized GitHub Actions run.
4. Preserve all STEP2/B3/Body-JEPA/jepa_weight/Age/Redmi/whole-system negative gates.

## Next

When Run401 completes: observe job/artifact ID and SHA, download+verify, run Run402 against real archive, and only then add a separately authorized pinned native stage2 workflow. No model job starts from this PR by default.