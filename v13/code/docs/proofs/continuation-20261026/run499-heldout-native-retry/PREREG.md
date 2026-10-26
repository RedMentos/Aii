# Run499 — one-shot frozen 14-row Linux-native retry after Run498 source GREEN

Date: 2026-10-26. Owner: independent continuation / Run499 only. Base: Run498 PR #496, commit `2efebfe197b3465a0a10732b449fada527c89621`. Run498 source proof Actions `40302693619` and focused Actions `40302693801` both GREEN; Run497 original native Actions `40302045367` RED and remains preserved. Run498 PR #496 is **review-only, not merged to main**.

## Exact frozen scope and hypotheses

Reattempt **only** Run491 held-out episodes Vesper and Willow, arm C, seed 31, seven frozen variants each = 14 planned Linux-native consumer rows. Original Run491 fixture SHA256 `c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63`; pilot subset SHA256 `816c3a4cc8e8c85a7188b5c4524b13638d6bd4d353c782d296a363366702f774`. Original model hashes, revisions, license and runner SHA256 stay in `v13/code/scripts/run491_step2_heldout10.py` and `v13/code/specs/models.json`, not replaced. `run496_heldout10_native_pilot.py` is the Run498 source-verified symlink-compatible version, Git blob `543982e6c03c548eab87470732be279fbba53ac1`; original frozen `run491_step2_heldout10.py` Git blob `f4d2d8d5e66c49c508e376ebafce2146e5a2715b`; models spec Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`.

Prerequisites before native: source hash equality; isolated dependencies; source tests; frozen fixture-only manifest; pinned `v13.bootstrap` source downloads; actual installed GGUF/runner/native-library SHA preflight. No inference before actual byte preflight. Use one serialized GitHub-hosted Linux runner under existing `v13-native-c3-run131-serialized` concurrency group. No Redmi device, no private data, no license acceptance, no paid provisioning, no unpinned substitute models.

## New failure-closure contract

Run497 used `if: steps.X.outputs.rc == '0'` and could treat a skipped upstream step's empty output as numeric zero in GitHub Actions expressions. Run499 requires **both** `steps.X.outcome == 'success'` and the exact string exit code `steps.X.outputs.rc == '0'` at each dependency edge; final `if: always()` enforcement explicitly requires every stage outcome `success` and every raw exit-code file exactly `0`. A skipped native/audit step must produce RED, not GREEN. Keep original raw failure logs and SHA256 closure, safe no-model artifact, independent 14-row audit and original negative gates. No overwrite of original Run497 attempts or of new run artifacts.

## Acceptance and negative gates

Only `RUN499_14_LINUX_NATIVE_ROWS_INDEPENDENTLY_VERIFIED` with 14 unique (fixture, variant) pairs, actual installed bytes, original frozen oracle checks, no wrong committed, independent SHA-bound postflight, and all mandatory stages completed with exact zero may count as pilot success. This **does not** pass the 1050-row STEP2 cohort or certify semantic utility. Preserve `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=unmeasured`, Age-0 safety and permissions unchanged. A failure remains RED with its logs and next diagnostic; no silent retry or changed cohort.

## Next command

After source and owner checks, open a **draft** PR targeting `codex/run498-native-runner-symlink-20261026` with the one-shot `.github/workflows/run499-heldout-native-retry.yml`; inspect GitHub Actions run, preserve raw artifact IDs and SHA256, independently inspect postflight, and update a new Run499 checkpoint. If any prerequisite fails, record exact stage and continue another independent canonical package without promoting gates.
