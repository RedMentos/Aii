# Unfiltered combined V13 software review after four JEF/SkillLive fixes — prereg 2026-10-30

Parent review PR #1178 exact verified head `0d01165bc271865deedd49b61dcd39b7eff87503`. CI-only review child; no runtime/source/model/cohort changes. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Own only this prereg, a new full-suite workflow and a result delta.

## Why
Prior full unfiltered run #1174 at `917c2c7d9d717426facd0bc6f98b126af3a4ece3` ran 3360 tests with **two frozen Run34/Run37 `native_source_or_catalog_changed` errors** and 11 skips. It predates four branch-scoped source fixes:
1. #1175 JEF lifecycle current-session SQL boundary;
2. #1176 typed exact update provenance;
3. #1177 agreeing SkillLive route correction must not poison JEF;
4. #1178 idempotent FINAL self-label retry/correction.
Each has original RED and exact-source GREEN focused raw, but focused evidence does not prove the entire integrated software corpus.

## Frozen method
Ubuntu 24.04, isolated venv with NumPy 2.2.6, torch 2.5.1+cpu, Transformers 4.44.2, PEFT 0.13.2, psutil, PyYAML, Pillow, prompt-toolkit 3.0.52. Execute `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` without exclusions/waivers. Capture original full raw, source/Canon Git blobs, exact head, dependency freeze, all stage exits, SHA256SUMS, artifact CRC/hash, privacy/diff. The two frozen historical source errors must remain visible, never rewrite registered original source. Any additional error is a regression to triage.

## Negative gates and coordination
No model downloads, no Redmi, no native device proof. Keep Age-0 RECORD_ONLY, jepa_weight=0, STEP2/B3/Body-JEPA/World-JEPA/LP3/whole-system gates unchanged. Only this one heavy full suite runs; no parallel native/model jobs. Do not merge review chain into production main automatically.
