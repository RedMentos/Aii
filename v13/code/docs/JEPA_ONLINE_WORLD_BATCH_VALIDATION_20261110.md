# JEPA / Memory checkpoint — 2026-11-10, batch prevalidation

## Scope and source
- Base: draft #1673, branch `jepa/online-world-cursor-recovery-20261110`, which itself builds on `codex/v13-integrated-online-jepa-20261109`; not stale main.
- Own branch: `jepa/online-world-restart-idempotence-20261110`; draft PR #1677.
- Read root and v13/AGENTS.md, existing source `online_world.py` and `continuous_predictor.py`, project BUILD_STATE/ROADMAP/HANDOFF and latest open PR list. Other agent ownership (Body/JEF/QA) untouched.

## Confirmed predecessor status
- Parent PR #1673 head `69b99154ad1ca9e351aadac58fa376cb4d610429`: GitHub Actions **SUCCESS** for workflows `V13 combined online JEPA integration` (42799753777) and `V13 continuous local plasticity` (42799753861). This is software CI, not Redmi proof.
- Parent fail-closed cursor check is not a two-file transaction and may reject interrupted checkpoints until operator recovery.

## This change
- Code: `v13/code/v13/online_world.py` now validates all new T8 action/outcome rows before any gradient or disk update, rather than mutating the first row before detecting a malformed later row.
- Tests: `v13/code/tests/test_online_world_batch_validation_20261110.py` checks invalid second outcome, invalid second action, and valid two-row replay after restart (no double gradient).
- CI: `.github/workflows/v13-online-world-batch.yml` compiles and runs batch, cursor recovery and earlier online-world regression suites.

## Claim limits / outstanding
- New PR head `12920680f0723d1e441df83982279e9d46bca75f`; Actions query immediately after push returned **no workflow runs yet**. New tests have **not been executed locally**, because container cannot resolve github.com for cloning. Do not mark GREEN until Actions completes.
- The prevalidation is limited to the bounded new-row batch. It does not make predictor+cursor commits atomic, prevent I/O failure after a successful gradient, or guarantee convergence. Retention remains a replay-error measurement, not full JEPA utility.
- No Android hardware measurements, no active GGUF weight mutation, no STEP2/B3 gate promotion. Existing negative gates remain.
- Next: check Actions on PR #1677; fix failures. Then design a single atomic journal/checkpoint that binds cursor IDs to predictor weights with crash-injection tests, preserving migration/rollback semantics. Coordinate with #1673 and integrated-JEPA owners before merging.
