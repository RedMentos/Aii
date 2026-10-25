# Run152 — A3 support-floor held-out leakage, isolated candidate

**Independent canonical package:** A-Plane/A3 student training integrity. Existing frozen `v13/student_worker.py` computes `support_floor=float(np.min(np.max(raw[vi]@raw[ti].T,axis=1))-.02)` and clamps it. Here `vi` is the held-out source index set; changing validation samples can change the model's OOD support threshold. This is validation-set leakage. The frozen worker and all source/model hashes remain unchanged.

**Candidate:** `scripts/a3_trainonly_support_floor_run152.py` uses normalized training-only raw features and leave-one-out nearest-neighbour cosine; the 5th percentile minus .02 is clamped to the original .5..99 band. Source groups determine split, but held-out **text is never featurized**. Reject nonfinite/zero/duplicate train vectors and invalid dimensions; report only aggregate stats, input SHA and unchanged gates. No training, teacher calls, inference injection or new authority.

**Tests:** Eight tests including deterministic repeat, demonstrable legacy threshold dependence on heldout samples, invalid data, mocked read tracking of heldout text, exclusive report output, source bounds and actual `student_worker` integration. Local: 7 PASS, 1 SKIP (full worker unavailable in scratch). First synthetic fixture mistakenly used an unrelated cluster as its 'near' validation set, causing 1 FAIL; fixed fixture and original failure retained in `RAW_TESTS.log` vs `RAW_TESTS_GREEN.log`. CI must run all 8 on real worker.

**Evidence class:** software/synthetic only. This candidate does **not** prove improved OOD calibration; fresh teacher-target validation and ablation are required. No Body-JEPA, STEP2/B3 or Redmi promotion.

**Next:** CI and independent review; if calibration holds on fresh source-group OOD data, prepare a separately authorized integration after frozen SourceHandoff constraints are cleared.
