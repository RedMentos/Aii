# Run187 — independent raw C3 final-answer audit, Linux-native evidence (2026-10-25)

Parent Run186 PR215, head `c0c154aebf9ddab96a8414ad5c7febdb729af043`. This is an independent **posthoc read-only audit** of the Run186 preregistered C3 experiment; audit source and 9 local synthetic tests were created before inspecting the Run186 native artifact, but were not remotely preregistered before inspection. No change to original Run186 acceptance, B2 source, C3 prompts, model, seeds or original gates.

## Immutable inputs and raw verification

- Run181 Linux-native B2 source: GitHub Actions `40168581804` SUCCESS, artifact `12589259384`, ZIP SHA256 `cb0786ec15734efe4b3dda2607218dccf98cb96015d2852349a44b8c689982fb`, `report/report.json` SHA256 `ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880`.
- Run186 Linux-native C3 final: GitHub Actions `40170179243` SUCCESS, artifact `12589624346`, ZIP SHA256 `eca63cb1482282cda517216b6049188fc9d6c9bbdd219564ccae9b108f631667`, `final/report.json` SHA256 `2d9828c2e688b65e50df1849a77fc9bbaf4dd56f59ae423e7b62722f7fc10219`.
- Reconstructed original 36-row synthetic corpus hash `1872a3adf6e51e05e604053539d50ae05c955b221f78f1951d1f68e2a12f926c` matches frozen Run181 binding.
- Independently recomputed all 108 C3 answer/evidence scores from raw JSON and actual B2 quotes forwarded. Validated source/model/runner hashes, all indices, source quote counts, no authority flags, per-arm aggregates and preregistered paired criteria. **RUN187_INDEPENDENT_C3_FINAL_AUDIT_PASS**. Independent JSON SHA256 `b618accc7fa9b0907adb7fda5ba11c74d81eacf33db806a3d0b109188504e7e7`.

## Results — not system completion

| Arm | Answer key hits / 36 | Source-supported final answers / 36 | Invalid evidence quotes | Mean C3 prompt tokens |
|---|---:|---:|---:|---:|
| fixed960 | 33 | 10 | 12 | 126.8 |
| event960 | 25 | 11 | 11 | 128.2 |
| gist | 32 | 13 | 10 | 127.7 |

Run186's **prospective C3 proxy diagnostic**: Gist vs fixed960 paired supported wins **7**, losses **4**; invalid quote count lower (10 vs 12); mean prompt tokens 127.7 vs 126.8, within 110%. Thus **C3_GIST_FINAL_UTILITY_CANDIDATE**, independently reproduced. The paired difference is only three cases out of 36; it is not a statistically robust, multi-seed or Redmi benefit proof. The original Run181 B2-only utility verdict remains **GIST_NO_GAIN** (gist 1950.8 B2 prompt tokens vs fixed960 914.9); C3 prompt tokens do not account for upstream B2 cost, so total pipeline efficiency is not proven. No B1 complementarity, JEPA, re-entry, learning, retention or Redmi proof.

Original gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE; no Gist activation. Run173 orphan failure and AGE0c false alarms remain.

## Durable backup and next

Private Library copies verified byte-identical after materialization: `/V13/Run181-native-B2-gist-raw-20261025.zip`, `/V13/Run186-native-C3-final-raw-20261025.zip`, `/V13/Run185-source-support-native-replay-20261025.json`, `/V13/Run187-independent-C3-final-audit-20261025.json`. The rejected anyone-writable Drive destination was not used. Next: independently preregister held-out multi-seed C3 final utility with total B2+C3 token/latency/energy accounting and negative-control quote ablation, then B1+B2 complementarity and Redmi proof; no activation from this exploratory result.
