# Run30 independent read-only Run26 Linux-native Keldara CQ aggregate (2026-10-28)

**Original raw evidence:** Run26 Actions `40715223545` SUCCESS at exact `03c664c6a70eebe943ec6a0384a24814ca59c0c5`. Downloaded original GitHub Actions artifact ZIP SHA256 `989abb8ac7b8fcd91ec047f97b735c9c8f84342e49251855b3375f7b3519762b`; ZIP CRC clean; **26/26** inner SHA256 manifest entries verified; `HEAD.txt` matches source commit. Original `STEP2_RAW.json` SHA256 `0a1ce865d590adb5c4ead5007f42c202dbe6f24140a562ebdbc44bcb9f39baf3`. All **7/7** original canonical row hashes independently recomputed from deterministic JSON; model hashes before/after and runner SHA before/after identical. Source Run15 blob `635e5727a42cb1eac4f84441afda2977b0c8109c`, Keldara EN SPLIT/CQ/seed 20261114 unchanged. The original raw ZIP was privately uploaded to `/V13-Checkpoints/2026-10-28/Run30-Native-Aggregate-Audit/RUN26_ORIGINAL_40715223545_sha989abb8a.zip` and **byte-identical Library readback verified**. No raw prompt, source text or model output is published here.

**Independent field-level audit of the original native run** (one fixture, 12 fields/variant; no re-scoring):

| Variant | Utility | Exact | Incorrect fields |
| --- | ---: | --- | --- |
| b1_only | 8/12 = .6667 | No | project, action, A.remaining, B.remaining |
| b2_only | 3/12 = .2500 | No | project, action, A.cost, A.remaining, A.days, B.cost, B.remaining, B.days, B.eligible |
| both_none | 8/12 = .6667 | No | project, action, A.remaining, B.remaining |
| both_exact | 8/12 = .6667 | No | project, action, A.remaining, B.remaining |
| both_control | 8/12 = .6667 | No | project, action, A.remaining, B.remaining |
| same_policy_dual | 8/12 = .6667 | No | project, action, A.remaining, B.remaining |
| prompt_only_dual | 7/12 = .5833 | No | project, action, A.remaining, B.remaining, B.eligible |

**Result:** `both_exact - b1_only = 0.0000` on this one fixture. **Every** variant fails the same four fields: project, action, A.remaining, B.remaining. Thus the current evidence does not support native two-body complementary utility. **Do not attribute all four failures to C3 alone:** independent inspection of the original `consumer_messages` shows that the `both_exact` B2 offer supplied **zero verified source quotations** to C3, while B1 supplied one. The current-source message refers to earlier rules but does not itself supply their numeric values. Missing B2→C3 rule evidence can explain the null remaining budgets; the incorrect final action and project formatting additionally require consumer/output analysis. This is a post-hoc descriptive observation, not a causal ablation. Prompt formatting, B2 quote selection, arithmetic, schema normalization and their interaction remain open. One fixture cannot establish a population effect. The original Run26 scoped structural PASS remains valid; **STEP2 UTILITY_FAIL remains unchanged**.

**Reproducibility:** New stdlib read-only `scripts/run30_native_keldara_aggregate_audit.py` validates original ZIP and row hashes, returns only fixed-field aggregate masks and preserves all negative gates. Synthetic tests `tests/test_run30_native_keldara_aggregate_audit.py` cover clean, tampered inner hash, duplicate variant, promoted gate, inconsistent field score and model drift. CI source-only full regression evidence must be verified separately before calling this new software package GREEN; original Run26 native evidence was already SUCCESS.

**Next preregistered direction (not run here):** Preserve this frozen native output, compare (a) strict source-bound deterministic recipe, (b) C3-only exact structured extraction and (c) B1/B2+C3 with identical source/format on **fresh disjoint** fixtures, recording both actual output and exact field provenance. Require no oracle in model prompts, no unapproved live authority, original cohort untouched, full A/B controls and independent F5 checks. Only a fresh measured native improvement over single-body controls can change STEP2.

**Gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Remaining platform budget UNKNOWN.
