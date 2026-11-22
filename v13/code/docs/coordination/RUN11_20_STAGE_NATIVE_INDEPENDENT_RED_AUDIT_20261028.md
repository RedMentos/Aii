# Run11 — independent full 20-stage Linux-native acceptance audit (2026-10-28)

**Owner:** GPT-6 independent review of PR #871, based on its observed head `e719910f02b4d4af50ac245cd8175cef287dff4b`; review-only child. This is an **actual-weight Linux x86_64** result, not a Redmi run. The original native workflow source remains at `4f106ad6b63977cdec1a4d9050ee2c361fe36260`, Actions run `40649812006`. No source, frozen fixture, model, seed or gate promotion.

## Verified closed raw evidence

- GitHub artifact **12800785500**, original filename `v13-integrated-full-acceptance-final-40649812006-4f106ad6b63977cdec1a4d9050ee2c361fe36260.zip`, independently downloaded as `run11-final-native.zip`.
- Independently computed ZIP SHA256: `5d496cc71fe72a8b79aa5a099019b5872c5c6f9dbec064e7f8cea662966228fb`; equals GitHub upload log digest.
- ZIP integrity: `testzip() == None` (no CRC error); 76 entries; **75/75** entries referenced by `SHA256SUMS.txt` verified against original raw bytes, zero missing or mismatched.
- Source pin/install/bootstrap/deep-model verification all `EXIT=0`; `BLOBS` registered **24/24** and actual native model roles **4/4**. Original `CHUNK5/10/15/20_EXIT=2` is the script's partial/failing status; all four `CHUNK*_CHECK_EXIT=0` confirm closed stage counts and unique finished PASS/FAIL statuses.
- Cumulative stage checkpoint counts: **5/5 PASS, 8/10 PASS, 11/15 PASS, 15/20 PASS**. The final report status is **`IMPLEMENTED_PATHS_PARTIAL`**, not PASS.
- `PRIVACY_EXIT=0`, privacy scanner `CLEAN`. `DIFF_EXIT=2`: **three trailing whitespace lines** in the newly added workflow at lines 180, 226 and 272. This is an independent CI failure in addition to five native stage failures. A whitespace-only workflow correction is isolated on this child branch; **do not relabel the original run GREEN**.

## Actual 20-stage results (original source, unchanged)

| Stage | Verdict | Observed blocker |
|---|---|---|
| 1 jef-modes | PASS | Existing JEF modes native structural path |
| 2 experience | PASS | Experience replay path |
| 3 learning | PASS | Test approvals only; not automatic Body-JEPA |
| 4 executive | PASS | Executive continuity |
| 5 resources | PASS | Native resource path |
| **6 readouts** | **FAIL** | `READOUT_LIFECYCLE_PARTIAL`: `RuntimeError: Halt gate blocked; see actual trajectory/evaluation metrics`; recorded halt trajectories for 60–330. Do not bypass the halt gate. |
| 7 native-taps | PASS | Native taps |
| 8 predictor-b1 | PASS | B1 bounded predictor proof only |
| 9 predictor-b2 | PASS | B2 bounded predictor proof only |
| **10 control-calibration** | **FAIL** | `CONTROL_CALIBRATION_PARTIAL`: `checks.support=false`; 49 held-out observations, after Brier 0.08106 vs before 0.25, but **held_out_support_pass=false**. `EVALUATED_FAIL`, `commit_eligible=false`. |
| **11 memory-retrieval** | **FAIL** | `MEMORY_RETRIEVAL_PARTIAL`: source delivered in native context, but both `native_language_answer_uses_human_source=false` and `native_detail_answer_uses_human_source=false`; expected `400 Euro` not present in either answer. Do not infer retrieval utility from source delivery. |
| 12 consolidation | PASS | Bounded consolidation path |
| **13 output-adapter** | **FAIL** | `OUTPUT_ADAPTER_PARTIAL`: `checks.calibration=false` and `first_token_accuracy=false`; held-out first-token accuracy 11/24 = 0.4583; candidate `EVALUATED_FAIL`, `commit_eligible=false`. |
| 14 a3-student | PASS | Existing stage-specific student proof only |
| 15 world-predictor | PASS | World predictor bounded proof |
| 16 step12 | PASS | JEF STEP12 path, not STEP2 utility exit |
| 17 body-state | PASS | Body-state bounded path |
| 18 second-attempt | PASS | Bounded second-attempt path |
| **19 cancel-restart** | **FAIL** | `checks.cancel_native_process_stopped=false`, `all_passed=false`; the cancel trace separately reports `runner.interruption_unload.process_reaped=true`. **Investigate whether this is a check/telemetry mismatch or actual lifecycle leak** before changing behavior or gate. |
| 20 sustained | PASS | Linux-only bounded sustained proof; not Redmi thermals |

## Claim boundaries and next work

This run is **15 PASS / 5 FAIL** and the GitHub workflow conclusion is **failure** (both native partial and `git diff --check` red). Do not hide failures behind a whitespace-only fix or rerun with relaxed thresholds. Read original `archive/{readouts,control-calibration,memory-retrieval,output-adapter,cancel-restart}.{json,log}` before repair. Keep source/model/seed/fixture hashes unchanged for the historical run. New candidates require independent preregistration and disjoint holdout, and must be compared with the original raw evidence.

Next highest priority: (1) source-bound independent triage of stage 19 process reaping versus check logic, and stage 6 halt; (2) C3 exact-source retrieval consumption on a new heldout; (3) native calibration/support and first-token adapter improvements; (4) separate C5 manifest-aware no-B routing on a new source lineage with historical frozen tests unchanged; (5) Redmi user-run `HANDY_PFLICHT.sh`. Current Linux source is not a complete V13.

**Negative gates unchanged:** STEP2 `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; LP3 heldout `FAIL`; `jepa_weight=0`; Age0 `RECORD_ONLY`; Redmi not measured; `canonical_architecture_complete=false`; `user_full_scope_complete=false`. No production/main merge.

**Resume command:** Inspect original artifact 12800785500 and run source-pinned stage-19 cancellation telemetry counterexample on a new review branch; do not start concurrent heavy native owners. Preserve this report and original raw archive separately.
