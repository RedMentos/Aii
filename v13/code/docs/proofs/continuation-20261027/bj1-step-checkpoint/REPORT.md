# BJ1 opt-in step checkpoint candidate — 2026-10-27

**Scope:** review-only candidate; no Age-0 authority, no model swap, no default behavior change, no Canon gate promotion.

## Source and ownership
- Owner: `codex/automation11-bj1-step-resume-candidate-20261027`.
- Exact parent: PR #718 head `edd0212c1774f893433040f48fa6b57c3d2d4209`; parent chain remains review-only, not `main`.
- Canon: `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` W3/W6, §13.1–13.4, §14.5, IH-H25. Preserve all original STEP2/B3/BJ1 negative gates and unchanged seed/model/cohort settings.

## Why this package
The independent registered BP2b seed41 legacy native attempt, Actions run `40506115941` on source `7243d71f51ff53587b5062953a7d79f786648e87`, **did not complete**. The original Actions artifact `12737361371` was downloaded and inspected without changing it:
- Original ZIP SHA256 `31f27480b98291ad60082a8fa56b2ff37ce08f053a711851fc08823f568ce982`, CRC PASS, 14 files.
- `SOURCE_EXIT=0`, `ENV_EXIT=0`, `NATIVE_EXIT=124`, `PRIVACY_EXIT=0`.
- Exact pinned 2,340,697,936-byte FP32 master: `FULL_FILE_HASH_PASS`, expected SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a`. Seven metadata SHA checks PASS.
- Native log shows model load and PyTorch fallback for `causal_conv1d_fn` and `causal_conv1d_update`, then the **35-minute process timeout**. No completed native arm, score, or learning utility proof; the log does not establish how many optimizer steps finished.
- Original ZIP was copied to a permitted private Library checkpoint; byte-exact readback matched the original SHA256. The rejected anyone-writable Drive destination was not used.

## Implementation
- `v13/body_jepa_checkpoint.py`: opt-in, CPU adapter-only immutable step blobs, fsynced `CURRENT.json` pointer, SHA256 and source/config binding, trainable adapter + predictor + AdamW optimizer + EMA + two Torch RNG states + step history. Safe `torch.load(weights_only=True)`, strict tensor/optimizer identity and moment shape checks, reject changed weights, tampering, cross-source replay, orphan-only state, nonfinite data and backward step pointers. Previous committed step remains addressable after an orphan write.
- `v13/body_jepa.py`: the existing `BodyJepaTrainer.fit` consumes this checkpoint only with `cfg['checkpoint_resume']=True` and a pinned full master SHA. A new checkpoint is committed after every completed step. Source fingerprint includes full training items (including weights), config, anchors, probes, master SHA and base generation. New metrics report enabled/restored step. Existing `checkpoint_resume` default is absent/off; original registered BP2b 12-arm plans and frozen numerical settings are untouched.
- `tests/test_body_jepa_checkpoint.py` and `tests/test_body_jepa_checkpoint_fit.py`: synthetic CPU exact uninterrupted-vs-interrupted optimizer/EMA/RNG comparison, real tiny HF/PEFT `BodyJepaTrainer.fit` crash after fsync and restart, source/weight mutation, symlink, orphan, hash tamper, stale step and optimizer-order refusals.
- CI workflow pins a CPU Torch version plus Transformers/PEFT; no public model download, native runner or Redmi execution.

## Evidence and limitations
- Local isolated Torch-only helper tests: 7/7 PASS (container, synthetic).
- GitHub Actions `40514361736` at `7751c9f29a2a27f819a955962a3ab295a0a5e2e2`: **8/8 PASS** (7 helper + 1 actual tiny synthetic trainer), compile PASS, privacy CLEAN, `git diff --check` PASS. A newer exact-head run is required for later guards.
- Not a native model result. This does not show that the original 35-minute attempt had a resumable completed step or that an optimized kernel would be compatible. The candidate is not enabled for an active registered cohort.
- `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `BJ1=NO_SIGNAL`, `jepa_weight=0` in the registered BP2b cohort, Age authority 0, Redmi unmeasured, complete V13 false.

## Next owner action
1. Verify latest exact-head CI and independently inspect checkpoint optimizer/EMA/source guards.
2. Prepare a **new** explicitly registered native continuation experiment with unchanged original failed attempt retained; do not rewrite seed41 attempt evidence or silently change its protocol. Measure first-step time and resident memory before allocating another 35-minute job.
3. Continue unrelated Canon packages if native execution remains blocked. Do not promote BJ1, BP2b, STEP2, B3, or age.

Focused command:
`cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_body_jepa_checkpoint tests.test_body_jepa_checkpoint_fit`

Known prerequisite: pinned CPU `torch`, `transformers`, `peft` for the tiny integration test; real native run separately needs full master, approved CPU/memory budget, and a new preregistration. No private training states or prompts are committed.
