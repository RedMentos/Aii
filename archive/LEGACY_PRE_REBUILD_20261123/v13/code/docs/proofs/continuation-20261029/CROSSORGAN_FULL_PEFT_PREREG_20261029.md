# V13 cross-organ full unfiltered software replay after BJ1 + C3 changes — prereg (2026-10-29)

## Immutable parent and reason to rerun
- Review-only child of PR #1154, exact parent commit `dedc2b41315a615d1e79ac88ad9a6f0e64baded1`. C3 script blob `704b2a0c0dc90f06a842d5a828984b7e72692ae2`; Body-JEPA source blob `fe912d908868d5e923297fa52b44e09f1e39bf1f`; Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.
- Independent prior full unfiltered PEFT suite `40960222503` ran **3304 tests, 2 ERROR, 11 skipped**, with only original frozen Run34/Run37 `native_source_or_catalog_changed`; raw ZIP SHA256 `518e5bc842c73e483f38c05dcabe2ea8b3b57556ae709f454047d399258787f1`, CRC clean, 30/30 hashes, private byte-exact backup.
- **Reason for new full replay:** after that suite, the review chain added a bounded fail-closed Body-JEPA shuffled negative control (4 new tests, 25/25 existing BJ1+new focused GREEN) and a C3 source-answer contradiction/hedge veto (3 new tests, focused GREEN not yet observed at preregistration). The old full-suite result does **not** cover these source changes.
- Expected count if all new tests discover: **3311 tests** (3304+4+3), with frozen Run34/Run37 source-pin errors still RED. This is a prediction, not a result.

## Exact experiment
- Wait for C3 focused GREEN and original raw closure before launching the new full suite. Fresh isolated Ubuntu 24.04 Python 3.12 venv with official CPU `torch==2.5.1+cpu`, `transformers==4.44.2`, `peft==0.13.2`, `numpy==2.2.6`, same basic deps as prior. Verify exact imports, `pip check`, pip freeze, Canon/source Git blobs.
- Run **entire unfiltered** `PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'`, no exclusions, no edits to tests, cohorts, model/seed/source pins, no waivers. Record full original raw, all stage exits, compileall, privacy, diff, SHA256SUMS and original ZIP artifact.
- Any new errors must be investigated; the historical Run34/Run37 negative gates must remain and cannot be repinned. A 3311-test run with two frozen errors is **still RED**, not full-suite PASS.

## Claim boundaries
Software/synthetic/Linux-only. No deployed LFM2/Redmi, native JEPA utility, B3/STEP2/LP3 gate promotion or AG6 activation. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; Redmi UNMEASURED; V13 INCOMPLETE.
