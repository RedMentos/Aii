# Run29 — closed original registered real-file World-JEPA SHADOW result (FAIL, preserved)

Owner GPT-6 scheduled continuation. 2026-10-31 UTC. Review-only PR #1356, child of Run28 #1355. Exact executed source HEAD `be88168989fb47cac2c8a81db62217468456fb4b`. Binding Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; original Z12b model and real-file experiment blobs `99a686a131a1bdc89efe0d0cf9610ec54cbd853b` / `2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4` untouched. Run28 prereg `14a641750ef65ea291897c1e0e2f24aa094f24ec` frozen before fit.

## Original closed evidence and private backup

GitHub Actions **41145551357** terminal SUCCESS, artifact ID **13021455575**, original ZIP SHA256 **`79130a171e4f71214069aebaf023075fe6ecd48721a03170cef759a1fa37dc25`**. Independently downloaded, ZIP CRC PASS, **76/76** inner SHA256SUMS verified. PINS/VENV/DEPS/TEST/REALFILE/REPORT_CHECK/COMPILE/PRIVACY/DIFF exits all **0**; **12/12** focused tests PASS. Three registered seeds 101,102,103; train=4000, cf=150, attr=300, steps=3000 unchanged; 3600 fit rows per seed; all per-seed result checkpoints and synthetic file-world action logs retained in original artifact. Structural report check PASS; **model utility verdict is FAIL** (not contradicted by successful execution).

Private permitted Library backup `/V13-Checkpoints/2026-10-31/Run29-WorldJepa/run29-realfile-41145551357-sha79130a17.zip` uploaded and independently materialized/read back byte-identical (SHA256 above). Earlier `container_path` uploads failed `container_session_unavailable`; retry via exact exported `source_file_ref` succeeded. No rejected anyone-writable Drive destination used.

## Registered W1–W6 results (no rescore or posthoc waiver)

| Gate | Result | Observation |
|---|---|---|
| W1 covered-action counterfactual retrieval | PASS | pooled .9415; per-seed .9300 / .9430 / .9516 |
| W2 zero/shuffled controls and gap | PASS | no-action .1868, shuffled .1880, retrieval gap > .75 |
| W3 noncollapse | PASS | local latent effective ranks 8.95 / 7.59 / 8.15, min std > 1.0 |
| W4 confidence/error + unseen veto | PASS | covered Spearman −.3405; all held-out actions labeled SIMULATION_UNCERTAIN |
| W5 own/world/none attribution | PASS | own-only SELF .9204, world-only WORLD 1.0000, none SELF .9208 |
| **W6 no-action attribution at least .20 worse** | **FAIL** | JEPA balanced .9602; no-action balanced **.9664** (no-action is slightly better) |

Overall **`SHADOW_CANDIDATE_FAIL`**, not partial GREEN. Pooled held-out counterfactual retrieval .9288 is descriptive only: exact held-out operation-slot support remains zero and the candidate explicitly returns `SIMULATION_UNCERTAIN`. High retrieval is compatible with structural/compositional priors and a **96D** concatenated latent versus original **16D**; matched-capacity control missing. Original Z12B_WORLD_JEPA_FAIL and original W6 attribution confound remain unmodified. No evidence of semantic world understanding, real user tasks, learned German transfer or general AGI.

## Next authorized work

Run31 isolated AG12 finite-confidence candidate is an independent software package (separate owner/files, no native resource conflict). For World-JEPA, next registered work should compare **fresh same-seed original Z12b** and a capacity-matched control, and design a separately preregistered **disjoint** attribution evaluation that can actually distinguish action-conditioned from no-action predictions; do not change Run29 seeds, source or thresholds. Avoid interpreting the current W5/W6 confound as success. Retain raw failed attempts and the 96D/16D capacity caveat.

Gates unchanged: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, no Redmi, whole V13 incomplete. No production merge or auto-merge.
