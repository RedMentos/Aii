# Run11W — original C2 route regret, source-pinned read-only audit (2026-10-30)

**Software-only descriptive analysis, not a native rerun or a routing policy.** Independent child of Run11V PR #1251 at `b8c225d122b970ae199ea36c6d712e9fa8d039f5`. Preregistered before source at commit `3a05994d12e988cf139ce7332adb540a84ad578e`. No frozen scorer/model/seed163/seed181/Canon/runtime changes. Original Run11R native Actions 41035932580 remains RED; its 24 raw rows were independently structurally replayed by Run11T.

## Evidence

Run11W Actions **41039913409 GREEN**, exact tested HEAD `9a25b7f52ef8334fda6ffbe36b9e36520cf94309`, artifact **12969118553**, ZIP SHA256 `011dadbf3baf3540d15566ae9ccc33f682506a64b4f9bdeead1f7a197c0975ad`, **7100 bytes**, 23 entries, CRC clean, **22/22 inner hashes**, **65/65 software tests PASS**, all 9 stages exit0, privacy CLEAN. Original native RED ZIP SHA256 `47493d719ac1d6dedcb0142106b29b96817c0d4a211a6a2219879dec93cc8c5e` and HEAD `3d76c8e28735cfef4d40c290baad4556b61e04a7` re-fetched and verified with manifest, model pins, original source prompts, all 24 raw/preclose witnesses and age/negative gates. Source-only route audit returned `DESCRIPTIVE_ROUTE_REGRET_NO_GATE`.

Run11W software artifact is privately backed up at `/V13-Checkpoints/2026-10-30/Run11W-C2-Route-Regret/SOFTWARE_GREEN_41039913409_sha011DAD.zip` and independently byte-reverified after Library materialization. Original native raw remains in the preexisting private Run11R folder, not republished.

## Frozen seed163 results (secondary contradiction-veto scorer, not rescore)

| Source | Best single-organ / 2 | Distinct-both / 2 | Native-auto / 2 | Auto route → final role |
|---|---:|---:|---:|---|
| Mistral163 | 1 | 0 | 0 | both → B1_DETAIL |
| Lyra163 | 2 | 0 | 0 | both → B1_DETAIL |
| Orion163 | 2 | 1 | 0 | both → B1_DETAIL |
| Nova163 | 2 | 0 | 2 | gist → B2_GIST |

Frozen totals: C3-only **0/8**, B1-only **2/8**, B2-only **7/8**, distinct-both **1/8**, shared-dual **0/8**, native-auto **2/8**. Across the four sources, distinct-both is **6 points below** the per-fixture best single, native-auto **5 points below**. Native C2 invocation/selection **4/4**; three auto turns selected `both` with final B1, one selected `gist` with final B2. This describes the observed routing/output relationship, **not** evidence of causality, model ranking in general, or a trained C2 policy.

The new seed181 Run11V native workflow **41039528340** was still running when this checkpoint was written; its ZIP SHA256 remains UNKNOWN. The Run11W auditor accepts only registered seed163 secondary and seed181 primary `score_pair` slots, refuses unpinned/changed ZIPs, and withholds full-cohort deltas if any row is native invalid. No seed181 result is inferred until original raw is available.

## Gates and next step

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete. Source-only audit does not promote any gate. The frozen strict primary seed163 remains **0/48** and is not replaced by this descriptive secondary analysis.

Owner GPT-6 Run11W branch `assistant/v13-run11w-c2-route-regret-audit-20261030`; only new Run11W script/tests/workflow/scoped evidence touched. Next command: after Run11V native terminal, download its original ZIP and verify SHA/HEAD/CRC/manifest and independent Run11V verifier. If complete, invoke `python v13/code/scripts/c2_route_regret_audit_run11w.py --zip <native181.zip> --sha256 <verified> --head 6ba8986202febfe0faa813e8c1589ca85acac939 --seed 181 --schema v13.c2_body.disjoint.seed181.v1 --fixture-sha256 ae4799f60316cf51412d228547662de8cb4b6523dedffd5fc02b2862d84477e3 --score-slot score` on the original ZIP, without tuning any scorer. If native RED, preserve failure and do not claim 8-source comparative completion.
