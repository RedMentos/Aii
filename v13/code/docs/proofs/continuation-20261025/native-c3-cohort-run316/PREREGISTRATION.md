# Run316 preregistration — fixed 5-case native C3 second-turn/forget cohort

2026-10-25. Owner `assistant/native-c3-cohort-run316-20261025`. Parent Run315 exact native one-case PASS checkpoint `9d7097c283d9d998ead463bffb76c8d47c5640f8` (review chain, not main). Owned only new `v13/code/scripts/native_c3_cohort_run316.py`, `v13/code/tests/test_native_c3_cohort_run316.py`, new `.github/workflows/run316-native-c3-cohort.yml`, proof directory. No Runtime/Memory/Store/C3 source/model/seed/Canon modifications.

## Frozen registered cases, no post-result cherry-picking
Case order and exact strings:
1. ASTER — `What is the exact calibration code for fictional Project RUN316-ASTER?` → `59217`.
2. BERYL — `What is the exact entry passcode for fictional Project RUN316-BERYL?` → `80426`.
3. CEDAR — `What is the exact docking bay number for fictional Project RUN316-CEDAR?` → `27615`.
4. DELTA — `What is the exact maintenance ticket number for fictional Project RUN316-DELTA?` → `94531`.
5. ECHO — `What is the exact color-key code for fictional Project RUN316-ECHO?` → `61872`.

Canonical JSON (`sort_keys=True,separators=(',',':')`) SHA256 `a5c990124a088f7968882ca269352bce2f0635acbf03e1685e473e5f23895ce7`. All codes invented, disjoint from Run315's 73194, not user data. Fresh SQLite home per case; no shared memory; serial execution. Same real pinned C3 LFM2.5-350M model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` and llama.cpp b10964 as Run315, no new download artifacts or model changes.

## Evidence contract
Use the already verified Run315 native probe, vary only synthetic QUESTION/CODE **before** each serial call; never replace the native generator or answers. For each case capture three real native FINAL outputs and source-bound C3 context before correction, after synthetic explicit global correction and after forget, with restart/new session and zero history. Store each raw per-case report and aggregate after every case (durable partial progress). Compute observed improvement, second exact, post-forget nonretention, integration pass, errors and rates with denominator fixed at 5. Do not discard failures, rerun/cherry-pick successful seeds or change question wording. A single-case PASS does not imply a general rate; 5 cases is exploratory.

Fixture-only tests are labelled separately and cannot satisfy native claims. Serialized Linux-native GitHub Actions bootstrap exact registered public models; source hash/Canon checks, official privacy, all raw logs and exit codes retained. CI can pass as evidence capture only if all five cases complete with source/forget integrity; **semantic utility failures remain in the aggregate and never promote STEP2**. If native integration fails, CI fails, raw evidence remains. No Redmi, Body-JEPA, B3 or AGI claims. Continue another independent package after checkpoint.
