# Run117DE prereg — independent normalized-source C3 semantic probe

2026-11-01 UTC. Review-only child of independently verified Run117DD PR #1581 at `9ed2966868313dc43161845efcaaa69e9755775d`. **This preregistration is committed before any new fixture, candidate, tests, software run or native launch.** Original Run117DA 48/48 Linux-native FINAL/reaped, independently audited ZIP SHA256 `71b2337a0fb012cbf0842417092311d666b52f19110e95646054d01f8bb35568`, no exploratory schema signal. Do not tune, rescore, overwrite or rerun DA seed117053.

## Problem and falsifiable mechanism

Both LFM2.5-350M and Qwen3.5-0.8B overproduce NONE when asked to independently apply exact human-source minimum/maximum rules. A **new default-OFF source-only presentation** may improve semantic use without revealing the deterministic JEF oracle: parse only the *literal* policy and option-sheet spans into typed threshold, comparison direction, boolean requirement and A/B numeric fields; include the complete original source strings and SourceRef digests; do **not** compute or send eligibility, ranking, expected answer, fixed JEF suggested_action or typed action. C3 must still independently compare the options. No production Runtime changes or model training.

Control = original Run117CM `source.build` two-message prompt, exact human Store admission. Candidate = same admitted source texts plus normalized **data-only** worksheet and system instruction, with exact post-build Store/source/epoch recheck. Both source messages must bind to the same USER F1/F5/JEF records and exact source IDs. Any unsupported grammar, conflicting fields, source mutation/revocation, ambiguous project/domain, oracle leak or nonzero authority fails closed. No fixed reader output or synthetic expected label may enter the model prompt. Keep original code and registered cohorts unchanged.

## Frozen new cohort (not DA)

Seed **117061**, projects EB01–EB12 (not DA, Run73, Run75, Run83, Run117CN), four A/four B/four NONE. JSON compact/sort_keys SHA256 **`81af85fb4a93baf8ea32c925f41548c6e9380ccd6025df43f2d4c346caad2e64`**. Tuple format project/domain/op1/op2/(rule1,rule2,required_sealed)/(A1,A2,sealed)/(B1,B2,sealed)/expected-offline-only:

```python
TABLE = (
 ('EB01','mesa turbines','Maximum','Minimum',(135,30,False),(130,36,True),(146,22,False),'A'),
 ('EB02','glacier telemetry','Minimum','Maximum',(215,15,True),(197,22,False),(217,14,True),'B'),
 ('EB03','port cranes','Maximum','Maximum',(165,25,True),(180,26,False),(171,32,False),'NONE'),
 ('EB04','reef surveyors','Minimum','Minimum',(125,30,False),(130,35,True),(140,40,False),'A'),
 ('EB05','rail beacons','Maximum','Minimum',(90,35,True),(104,34,False),(86,40,True),'B'),
 ('EB06','desert pumps','Minimum','Maximum',(205,25,True),(197,28,False),(194,29,False),'NONE'),
 ('EB07','marsh buoys','Maximum','Maximum',(95,25,False),(92,24,True),(107,32,False),'A'),
 ('EB08','solar trackers','Minimum','Minimum',(115,15,True),(140,25,True),(127,18,True),'B'),
 ('EB09','tunnel drones','Maximum','Minimum',(80,30,True),(94,29,False),(88,24,False),'NONE'),
 ('EB10','ridge relays','Minimum','Maximum',(185,15,False),(191,13,True),(191,15,False),'A'),
 ('EB11','orchard probes','Maximum','Maximum',(215,30,True),(199,29,True),(199,28,True),'B'),
 ('EB12','cave monitors','Minimum','Minimum',(80,15,True),(76,13,False),(62,9,False),'NONE'),
)
```

Four cases EB04/08/10/11 deliberately require both-option ranking/tie-break rather than only eligibility. Fixed oracle: eligible iff every Minimum/Maximum comparison holds and required sealed is true when mandated; choose lexicographic min (option1, option2, label), else NONE. Frozen source renderer: exact `tests.test_jef_range_policy_shadow.texts`, not a newly invented parser-generated policy. Independent table hash and oracle tests before any native call.

## Planned comparison and evidence

Two unchanged pinned native models: LFM2.5-350M Q4_0 SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, revision `657e078c94084481950a2d555a941481f715536b` (LFM Open License 1.0); Qwen3.5-0.8B Q4_0 SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, revision `8fea620810c4afa23dd6443f999a48574c1611a3` (Apache-2.0). Pinned llama.cpp b10964 Linux SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. **Planned**, not launched: 12×2 models×2 presentation arms = 48 serial native calls, JSON schema ON for both arms (to isolate source representation, not syntax). Temperature 0, seed117061, threads 2, max128 tokens, 120s per call, counterbalance four-arm order by row index; identical original Store source identities per paired arm, no typed oracle. Save partial raw, native FINAL/reaping, model/runner/source/prompt SHA and all negative gates. Strict original Run75 JSON scorer, no markdown cleanup, no semantic partial credit.

Exploratory signal per model requires all 48 source-bound FINAL/reaped and **normalized >=7/12, >=5/8 non-NONE correct, and paired net gain >=3** over raw source; otherwise NO_GAIN or STRUCTURAL_RED. Record per-arm exact and NONE frequency and both-option subset separately, but subset is diagnostic only. No power claim or STEP2/JEPA promotion from 12 synthetic tasks. A negative result falsifies this exact normalization mechanism, not the entire V13 goal.

## Ownership and continuation

This branch owns only new Run117DE fixture, default-OFF presentation candidate, tests, preflight and scoped documentation/CI. Frozen Run117DA source/weights/runner, Canon, production Runtime, other owners' branches and original failed attempts are untouched. First software-only real SQLite F1/F5/JEF tests and independent review, then optionally launch new native cohort under `v13-native-c3-ag12-20261030` only if no active heavy owner. No model downloads or native jobs during prereg stage. Keep original raw private, CI small receipts and private Library backup. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no Redmi, learning, production merge or whole-system promotion.
