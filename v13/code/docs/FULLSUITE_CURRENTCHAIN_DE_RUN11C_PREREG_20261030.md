# Current-chain unfiltered full software regression — prereg 2026-10-30 run11c

Review-only owner `assistant/v13-fullsuite-currentchain-de-20261030-run11c`; exact parent #1225 HEAD `852f2c6ccef375cb03a0ad8318fec851f3b191ad`, descendant of #1223 and historical JEF/C2/C3/Body/World/Sleep integration. Original Canon Git blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` must remain unchanged. This is independent **software-only** review; no model downloads or native/Redmi execution.

## Frozen test plan before workflow
Run **unfiltered** `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` on Ubuntu 24.04 with isolated venv, pinned CPU `torch==2.5.1+cpu`, `numpy==2.2.6`, `transformers==4.44.2`, `peft==0.13.2`, psutil/PyYAML/Pillow/prompt-toolkit. Capture full stdout/stderr and exit, pip freeze/check, actual package imports, Canon and JEF/C2/C3/Body/World/Sleep source Git blobs, compileall, privacy scan, diff check, raw stage statuses and SHA256SUMS. Preserve original RED evidence.

Prior unfiltered current-chain runs: ~3,404 tests, **2 historical frozen Run34/Run37 `native_source_or_catalog_changed` errors**, 11 skips, no other failures. These are real historical source-pin mismatches, not reasons to suppress, waive, skip, edit or relabel tests. A full suite is GREEN only if the actual unfiltered command returns 0; otherwise report exact failures, count, and whether newly introduced. No automatic rerun without new reason.

No shared source changes in this review package; branch-scoped evidence only. No age/learning/approval changes, no STEP2/B3/Body-JEPA/JEPA/Redmi/whole-system promotion. Next: fix only genuinely new regression with independent tests, or continue another canonical organ. Keep full raw artifact and private byte-identical backup.
