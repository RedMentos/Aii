# BP2b 12-arm serial native batch operator — software proof closed, 2026-10-27

**Owner:** GPT-6 independent review branch `assistant/v13-bp2b-native-batch-20261027`, parent exact `d89f9311f39c6d1c2aa9c7250eb68bb3b1a593e6` (PR #712, separate native owner running). Not production-integrated.

## Functional change

New `scripts/bp2b_native_batch.py` executes the **exact frozen 12 registered combinations** (seeds 41/42/43 × `legacy`, `bp2b`, `bp2b_minor`, `manual_ref`) **serially**, each in a fresh process. Dry-run is read-only and lists all plans; explicit `--execute-native` plus unique safe prefix and verified master required. A nonblocking owner lock and atomic fsynced `STATE.json` preserve per-arm command, status, raw-log SHA and result SHA. On restart, only exact verified completed results are skipped; failed, interrupted, tampered and untracked attempts are refused without overwriting. `--max-jobs` limits partial execution but never modifies registered cohort. `full_acceptance=false` always; no age/learning promotion.

## RED → GREEN

- RED GitHub Actions `40506726172`, exact `d52501ed4a30312e4ce9613f903aae967be2cc30`: 28 tests, **one failing test assertion** because the prereg prose/test incorrectly called the second arm `locality`. Actual frozen `ARMS` order is `legacy,bp2b,bp2b_minor,manual_ref`. The production batch script always read canonical `ARMS` and never changed cohorts. Dry-run/compile/privacy exit 0. Raw ZIP artifact `12735052873`, SHA256 `ec41fec25448104e1996e2f71e82674c582ebdfa3d8326537e347bb6ecb03da6`, CRC PASS.
- GREEN GitHub Actions `40506848909`, exact `74d2166c862af8b2f8f0edcc8e8411a5b58e3529`: **28/28 software tests PASS**, dry-run no output writes, compile and privacy CLEAN. Raw ZIP artifact `12735531718`, SHA256 `9dce3b1a27c6a5bad3421aacf6c6116957763c97088444bab6e058f71b991e3c`, CRC PASS.
- Both original ZIPs independently hashed, privately backed up in ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-Native-Batch/`, materialized again and compared byte-exact (both PASS). No public model/adapter weights or private data.

**Evidence class:** SOFTWARE_FAKE_TEST and synthetic orchestration only; no new native model run launched by this package. The separate seed41 legacy native attempt remains owned by PR #712. No STEP2/B3/BJ1/Body-JEPA/jepa/Q4/Redmi/full-V13 promotion.

**Next command:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`. After the first native arm has been reviewed and heavy owner cleared, use `PYTHONPATH=. python scripts/bp2b_native_batch.py --out <isolated-root> --master-dir <verified-master> --attempt-prefix <unique> --max-jobs 1 --execute-native` to start a new independent batch; do not duplicate an already-running seed41 arm. For later resume increase `--max-jobs` under the same prefix.
