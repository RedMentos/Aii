# Run188 — full B2 + C3 pipeline cost audit (posthoc, 2026-10-25)

Parent Run187 PR216, verified independent CI `40170412907` SUCCESS, head `9389d00cae4d83f91e082d1fc62250369c4b3f89`. This is an **additional posthoc diagnostic** using exactly the immutable Run181 native B2 and Run186 native C3 36×3 reports. It does not retune either frozen preregistered decision, and no model was run for this audit. Source and 7 local synthetic tests were written before the actual cost replay, but not remotely preregistered beforehand.

## Source binding

- Run181 B2 source ZIP SHA256 `cb0786ec15734efe4b3dda2607218dccf98cb96015d2852349a44b8c689982fb`, raw report SHA256 `ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880`.
- Run186 C3 native ZIP SHA256 `eca63cb1482282cda517216b6049188fc9d6c9bbdd219564ccae9b108f631667`, raw report SHA256 `2d9828c2e688b65e50df1849a77fc9bbaf4dd56f59ae423e7b62722f7fc10219`.
- All 108 B2/C3 rows paired by original index/kind. Run187 independent source-supported score audit required before cost accounting. No invalid/duplicate rows. Closed Run188 JSON SHA256 `d1e80731964a800fa0c1080595c9a509363f414c6e49e41bfb7865d9b7eccbf4`, verified in private Library `/V13/Run188-B2-C3-total-cost-audit-20261025.json` after re-materialization.

## Measured proxy results

| View | Source-supported C3 answers /36 | Mean B2+C3 prompt tokens | Sum of B2+C3 request seconds | Supported answers /1000 prompt tokens |
|---|---:|---:|---:|---:|
| fixed960 | 10 | 1041.6 | 9.29 s | 0.2667 |
| event960 | 11 | 1629.2 | 13.95 s | 0.1875 |
| gist | 13 | 2078.5 | 17.52 s | 0.1737 |

Gist yields **3 more source-supported C3 answers** (13 vs 10) on this 36-item synthetic cohort, with paired wins 7 vs losses 4. But **total prompt tokens are ~1.995×** and summed request seconds **~1.886×** the fixed960 arm. The posthoc total-cost diagnostic therefore reports **PIPELINE_TOTAL_COST_NO_GAIN**. This does not overturn Run186's narrower preregistered C3-only `C3_GIST_FINAL_UTILITY_CANDIDATE`, nor Run181's preregistered B2-only `GIST_NO_GAIN`; it shows why both stages and their costs must be measured together.

The sum of separately measured native B2 and C3 request durations is **not** actual integrated wall-clock latency. It excludes startup, routing, energy, thermal constraints, RAM and Redmi. The 36 synthetic memos are not independent held-out multi-seed evidence. No Gist activation or STEP2/B3/Body-JEPA/learning/RSI claim follows.

## Gates and next

STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE; Run173 orphan and AGE0c false alarms retained. The rejected anyone-writable Drive destination was not used. Next: preregister an independent held-out multi-seed, end-to-end B1/B2/C3 utility test with total cost, quote-negative-control and Redmi resource constraints; improve Gist scheduling/slot budget only against that bound cohort, without changing registered old criteria.
