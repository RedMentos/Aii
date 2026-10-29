# C3 opt-in native stream consumer bound — software result (2026-10-29)

## Source and ownership
- Review-only child of PR #1145 at `71fe7978d5dca6a134ced0c645346b291b97d92c`; branch `codex/v13-c3-native-stream-bounds-20261029-auto10ah`. Parent/main untouched; no force-push or production merge.
- Frozen preregistered test and workflow before source edit: test-only RED HEAD `ddbc17b7b7e2ed5601317a808eeca8a4ed284282`. Original source blob `87b1addd06680ce01f8247df735fa305371ceb93`.
- Source fix commit `f7725a3ea47ae5fb8c566cb6ec98b882b596e071`, new source Git blob `ae0260b4fb6ec51998cbe08326c430d0f2b8cc88`.
- No Canon change; exact blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. No registered cohort, model, source or seed hash rewritten.

## Actual bug and fix
- Prior `query` used unbounded `"".join(runner.generate(...))`; passing `max_tokens` to the runner was not an independent consumer cap.
- A fake native generator emitting 32,768 spaces followed by `615 Euro.` was accepted as `FINAL`, despite an excessive generated stream. The test-only RED run proves this.
- A new incremental collector rejects output exceeding 32,768 Python characters and rejects non-string chunks; ordinary multi-chunk strings are joined unchanged. It returns `None` on rejection, so existing post-generation source/answer guard returns `UNVERIFIED_NATIVE_ANSWER`. The existing C3 unload remains in `finally`.
- This protects the Python collector from unbounded *accumulation*. It does not bound allocation inside a faulty native generator before a chunk is yielded, nor prove native timeout/cancellation.

## Closed focused evidence
- RED Actions `40955251916`, exact HEAD `ddbc17b7b7e2ed5601317a808eeca8a4ed284282`: 40 tests, 1 FAIL + 3 ERROR (new helper absent and actual oversized native fake response erroneously `FINAL`), raw ZIP SHA256 `bd62dee396a7efe8a651430c197ab9f83f2a353206092b59c017feed86dbead7`. CRC clean, 18/18 SHA256SUMS, private Library backup readback byte-exact.
- GREEN Actions `40955357530`, exact source HEAD `f7725a3ea47ae5fb8c566cb6ec98b882b596e071`: 40/40 PASS, CANON/VENV/DEPS/PIP_CHECK/FOCUSED/COMPILE/PRIVACY/DIFF all exit0. Raw ZIP SHA256 `2a5c8ec3d138c089710e54531e42202791be1c182db82d042bb9c40b8fd60ede`; CRC clean, 18/18 SHA256SUMS; private Library readback byte-exact.
- Full independent software suite Actions `40955400194`, exact workflow HEAD `ac7fdfcec7a5967fc67b57475761a9d61c7801cf`: **RED, 3266 tests, 6 FAIL, 43 ERROR, 28 skipped**. Raw ZIP SHA256 `0de0ebb0e161ae6b965a480f120ece072f757b92dfb6155543eb3a13b34baea6`, CRC clean, 18/18 SHA256SUMS, private Library readback byte-exact. Error categories include 27 `RUN50_INVALID_RECORD_COUNT`, 8 `no such table: events` from older synthetic/closed-store World-JEPA fixtures, 4 missing `torch` import errors, and 2 inherited frozen Run34/Run37 source-pin errors; other errors/failures retained in original raw. This is NOT a full-suite PASS, and not all failures are attributable to this C3 change.
- Raw ZIPs backed up privately under `/V13-Checkpoints/2026-10-29/Run10-C3StreamBounds/`; not published to public git.

## Gates and continuation
Software fake-native only, not real Linux C3 inference, Redmi or causal utility. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; V13 INCOMPLETE. No authority/gate promotion.
Next command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_c3_stream_bounds_20261029 tests.test_c3_budget_output_guard_20261029 tests.test_ask_verified_budget tests.test_verified_exact_standalone_cli_20261029 tests.test_verified_exact_budget_20261029 tests.test_source_consumer_admission`.
Next: close independent full-suite raw, review cross-organ negative gates, then continue independent canonical package; real C3/Redmi measurements separately required.
