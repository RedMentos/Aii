# BP2b trained adapter byte identity on batch resume — 2026-10-27

**Scope:** GPT-6 review-only child of PR #717 exact `a718ee365eccd968930deccdfce740d71e3ac709`, branch `codex/automation11-bp2b-adapter-resume-20261027`. No native model execution, no frozen cohort/model/seed change.

## Finding and repair

The native one-arm runner already checks its exported GGUF adapter SHA before prediction. However, the batch operator only persisted RESULT/log/ATTEMPT/SCORE/prediction sidecar hashes. After completion, the actual `trainer/adapter.gguf` or `trainer/manifest.json` could be modified or deleted and a restart would silently skip the arm as verified. This is not a closed raw model-artifact proof.

Added `_adapter_manifest_sha()`: require regular, bounded trainer manifest; require its `hash` to match `RESULT.json.adapter_sha256`; call the existing native runner `_verified_adapter_sha256(trained, trainer_dir)` to rehash **actual GGUF bytes** and enforce the trainer directory/path/symlink/size guard; store manifest SHA in the fsynced batch state. Re-verify all at resume before any skip; missing/tampered adapter fails closed. No new authority, optimizer, cohort or inference route.

## Original RED/GREEN evidence

- **RED** Actions `40510656227`, source `095b5eebdf8200bdb10809237018708635e550d4`: 37 tests, **3 expected failures** (missing adapter accepted, modified GGUF accepted, and subsequent call allowed). Original ZIP artifact `12737261302`, SHA256 `751766a0ee27760e7eac2b8920ee114f97480efee9ae0b46d9ec3e97bbf84fa2`, CRC PASS, privacy CLEAN.
- **GREEN** Actions `40510696327`, source `9daf47fba96f5eee0da842c7c7d3ffe7f86ccd3b`: **37/37 PASS**, dry-run no output writes, compile0, privacy CLEAN. Original ZIP `12736284763`, SHA256 `9843e2f0f28a573506084c3bbd4d92694995abf4a702fd4bbb58f85265f59078`, CRC PASS.
- Both raw ZIPs privately uploaded to ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Adapter-Restart/`, re-materialized and compared byte-exact to originals (PASS).

**Evidence class:** SOFTWARE_ONLY. Tiny synthetic adapter fixture tests hash binding; no trained model, utility, Q4/Redmi, STEP2, B3, BJ1/Body-JEPA, age or full V13 acceptance proof. `jepa_weight=0`, `age_authority=0`, `full_acceptance=false`.

**Next:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. Inspect separate genuine native seed41 owner Actions `40506115941` and original artifacts before any new heavy run; do not overlap it. Independent full software suite Actions `40510172446` found an unrelated optional `/root/native/restore` test permission error; portability fix is under separate review branch.
