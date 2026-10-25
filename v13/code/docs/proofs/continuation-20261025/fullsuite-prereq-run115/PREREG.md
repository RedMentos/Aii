# Run115 — restore missing full-suite test prerequisites without hiding errors

2026-10-25 UTC. Parent: Run114 PR #145 `6fce98c2111429b1951e6e527608cb9c543c21b3`. Owner: **new Run115 CI workflow and evidence/coordination files only**. No edits to runtime, tests, model files, canonical blueprint, Run106 `episodes.py` or Run107 `episodic_route.py`. No competing native inference or model jobs.

## Observed baseline
Run113 full Python unittest discovery (GitHub Actions 40144632264): 2151 tests, five ERROR, fifteen SKIP. Run114 fixes the single historical World confidence ablation `prediction=None` crash (new 4 + inherited 12 PASS, five-seed synthetic outcome INCOMPLETE_ABSTENTION). Four independent errors remain: three test imports require `torch` absent from Run113's isolated model-free environment; one Run18 test imports `test_lp3_serial_cohort`, which was never integrated as a repository test module. PR #52 holds a sealed Run16 `SOURCE_AND_TESTS.tar.xz` with Git blob `667d7f1b73a655097a44ff4c61749af113f7544f`. **Do not silently count archive contents as installed production code.**

## Locked experiment
1. Inventory the exact archived source tar and verify its Git blob hash. No write to tracked source.
2. Isolated Linux Python venv: `numpy==2.3.5`, `prompt-toolkit==3.0.52`, and `torch==2.9.1+cpu` from the official PyTorch CPU index (official documentation and wheel listing checked 2026-10-25). No HF/model downloads.
3. Extract the verified archive to a temporary directory; add its test/helper paths only to `PYTHONPATH`. Label this **augmented archived-candidate environment**, not the repository's integrated test suite.
4. Run bounded `python -m unittest discover -s tests -p 'test_*.py' -v`, 900-second cap, record exact PASS/ERROR/FAIL/SKIP. A passing augmented suite does not erase Run113 failures or integrate the archive.
5. Official privacy scan separately, with sufficient git history. Keep failed attempts and dependency provenance; no gate promotion.
6. If torch install or archive extraction fails, preserve exact error and continue with other independent canonical work.

## Original gates
STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, DS2 H2 FAIL, V13 INCOMPLETE. Native/Redmi/full-system NOT PROVEN.
