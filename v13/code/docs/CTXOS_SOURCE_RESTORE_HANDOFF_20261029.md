# Context OS exact source restoration handoff — 2026-10-29

## Ownership and lineage
- Parent PR #1104 exact source head `15732a6237187743c9cc6fe8539fdddfed94c6dc`, draft child PR #1109. Canon `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Prereg `1118dea7c97318df0782695198095e1897e2eb7f`, then test-only `b14d682497483246ee43b7e3c64f0f1cc2d00328`, then original RED `a2878cec6e06412beb14d9a24afd2b216da3fd91`, then implementation `7ae4d317e122e459f38edf0363c943d629f7f25d`.
- Own source `v13/code/v13/context_os.py`, new `tests/test_contextos_source_restore_20261029.py`, prereg/handoff and two own workflows. No unrelated source touched, no force-push or production merge.

## Feature and safety boundary
- `:ctxos source <event_id>` now reads current-session EventEnvelope SourceRef and full original source through Store.read_source. Source id, hash, full char range and modality must match the event; tombstoned, corrupt, truncated, missing and foreign-session sources are denied. Exact UTF-8 text returned with `SOURCE_EXACT_READ_ONLY` marker. No mutation to context plans, active model messages, memory, learning or age.
- Original test-only RED Actions `40900478763`: 6/6 expected errors due absent API, artifact `12909806221` ZIP SHA256 `d72df6275c6217ce9549ac9636fa785c90cb7ad17e4c40e51b6aeff510f02d16`, CRC clean, private backup `/V13-Checkpoints/2026-10-29/CTXOS_SOURCE_RESTORE_ORIGINAL_RED_40900478763_SHAd72df627.zip`. Privacy scan also RED from shallow checkout (missing base), not a demonstrated leak; full workflow uses fetch-depth50.
- Fresh source-only focused/full CI `40900620349` at `c7fd3f25533dd798a4c49d4b0f6ba2d5277cec3c` launched; outcome **pending** at this handoff. Pinned CPU torch, transformers, peft for full suite. Do not claim GREEN until exact-head raw verified.

## Next commands
1. Inspect Actions `40900620349`, all exit files and raw artifact; `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_contextos_source_restore_20261029 tests.test_context_os`; full `python -m unittest discover -s tests`; `python v13/code/scripts/public_repo_privacy_scan.py --base 15732a6237187743c9cc6fe8539fdddfed94c6dc --head HEAD --no-worktree`.
2. If GREEN, independently review read-only source/session/hash invariants, save raw privately, re-materialize and compare SHA256. If RED, preserve original and repair with new focused test, no gate promotion.
3. After verified checkpoint, choose another canonical utility package (e.g. Dream/Sleep or JEF/C2), not more isolated C3 decoder experiments.

## Gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 incomplete.
