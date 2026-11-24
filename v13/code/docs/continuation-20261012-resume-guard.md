# Checkpoint V13 — isolated resume integrity guard, 2026-10-12

This checkpoint belongs to PR #2 and branch `assistant/evidence-streaming-20261012`; active canonical Runtime sources are unchanged.

## Actual change
- Added `scripts/source_handoff_resume_guard_candidate.py` and `tests/test_source_handoff_resume_guard_candidate.py` in addition to prior sealed storage/audit candidates.
- Guard performs canonical SHA-256 row ledger and precise row/arm allowlist checks, refuses extra/missing or duplicate hashes, mismatched running summaries and forged top-level gate evidence (`canonical_gate_pass`, `learned_semantic_utility_proven`, `phone_measured`). It refuses final `RECORDED_DIAGNOSIS` with fewer than all sixteen correctly recorded fixture-arm rows, failed row states or altered installed-artifact binding.
- The original `scripts/source_handoff_ablation.py` remains frozen and does **not** call this candidate. Guard is code for independent review and possible later integration, not a new claim of native readiness.

## Checks
- 25/25 focused CPU-only tests PASS on Linux Python 3.13, with all three candidates and their unit tests in a staged code tree. No native GGUF model or Android device used.
- Updated source/test files were read back from remote and their Git blob hashes matched locally calculated identities:
  - source `5310e2f0de49a37b13c62c0a45703eeae8dc12b0`
  - test `90275be66c1baae444ec19b3870eb9ab11225b95`
- Hash/CRC-verified local snapshot `V13_Continuation_Checkpoint_20261012_v4.zip`, SHA-256 `918eafc476b7f2fe054428740d82a3bbe0009bc230bd07091f83969988c9eaef`; mirror exists in ChatGPT Library under `/V13/`.
- GitHub draft PR: https://github.com/RedMentos/Aii/pull/2 (unmerged).

## Other independent check
- SourceHandoff preregistration old/new report binding comparison saved at `docs/proofs/continuation-20261011/assistant-static-review-source-handoff-rebind-20261012.json`: 100 -> 121 Python source hashes; 21 newly inventoried nested `v13/agi/*` sources; 1 changed `scripts/source_handoff_ablation.py` hash; fixed fixtures, arms, model-artifact hashes, sampling, protocol settings and frozen prior cohort unchanged. No 16 native inference outputs from this checkpoint.

## Next reviewer actions and truth
- Check that stricter resume rules are compatible with historical original reports and interrupted edge cases; add integration tests to original test harness before activating.
- Run existing frozen 16-case SourceHandoff native ablation with verified original registration and actual model weights. Then original NumPy seeds 13/21/34 and Dream2 B40 (2/15 durable). Keep original failures: STEP2 UTILITY_FAIL and B3 L1 FAIL. No quality-/Canon-/Redmi-PASS.
- Recheck remote authority HEAD and original Drive handoff before cross-agent edits, avoid conflicting writes and force pushes.

`canonical_architecture_complete=false`; `user_full_scope_complete=false`.
