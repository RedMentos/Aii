# Run117CN prereg — disjoint C3 source-independence three-arm pilot (NO NATIVE LAUNCH YET)

2026-11-01 UTC. Review-only child of Run117CM PR #1564 at exact parent `e9d02e5d9caa4110ffd6c47630d4c184eea4ceb8`. Owner Run117CN. This document is persisted **before** implementing fixture/harness or observing native outputs. Existing Run73/75/82/83/117BW source/model/seed/runner cohorts and hashes must not change.

## Hypothesis and negative interpretation

Existing native C3 evidence shows reliable copying of a visible typed JEF action, not independent source reasoning. Test a new **source-only** arm against a **typed-correct** formatting control and a deliberately **typed-wrong** synthetic counterfactual. The wrong arm is **not** a human-authorized JEF decision and must never be used for live output. Source-only must contain full human-source-verified policy, sheet and current request, but no computed oracle/typed action; the correct answer is used **only by the offline scorer**. Any prompt leakage, missing source proof, model mismatch, nonzero authority or cross-arm KV reuse invalidates the pilot. No model/tool/learning/age promotion from a small native pilot.

## Frozen cohort and order

Seed `117041`. Exactly nine new disjoint project/domain tasks, with three A, three B, three NONE. TABLE serialized as `json.dumps(TABLE,sort_keys=True,separators=(',',':'))`, SHA256 `fb5708c82f4d62338eb080264ec6c2cbf8234fc9b5845abc3c0e53e513597335`. Each row: `(project, domain, op1, op2, (bound1,bound2,required), optionA, optionB, expected)`.

```python
TABLE = (
 ("Saffron","coastal sensors","Minimum","Maximum",(90,25,True),(105,18,True),(115,21,True),"A"),
 ("Vega","polar gliders","Minimum","Minimum",(120,14,False),(119,18,True),(140,20,False),"B"),
 ("Quartz","orchard robots","Maximum","Minimum",(160,30,True),(145,28,True),(155,29,True),"NONE"),
 ("Boreal","bridge probes","Maximum","Maximum",(200,18,False),(170,14,False),(185,13,True),"A"),
 ("Nimbus","river skimmers","Minimum","Maximum",(75,11,True),(90,12,True),(95,10,True),"B"),
 ("Cedar","archive crawlers","Maximum","Maximum",(135,16,True),(120,14,False),(130,17,True),"NONE"),
 ("Tangent","warehouse optics","Minimum","Minimum",(110,20,False),(130,23,False),(130,24,True),"A"),
 ("Peregrine","mountain relays","Maximum","Minimum",(145,10,True),(120,9,True),(125,11,True),"B"),
 ("Zephyr","harvest drones","Minimum","Minimum",(50,8,True),(70,9,False),(55,10,False),"NONE"),
)
```

Arms `SOURCE_ONLY`, `TYPED_CORRECT`, `TYPED_WRONG`; order cycles through `(S,C,W)`, `(C,W,S)`, `(W,S,C)` three times, giving each arm each position three times. TYPED_WRONG maps `A→B`, `B→NONE`, `NONE→A`. Exactly 27 cold native C3 calls, no shared conversation/KV between arms, no training. Synthetic source texts use the same fixed Run73 mixed-range grammar but unique projects/numbers. The fixed oracle is `jef_range_native_fixture_773.oracle`; strict scorer is its exact JSON sole-key `action` decoder, no partial credit. No fixture edits after first native output.

## Model and execution prerequisites

Pinned C3 GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, runner SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`, unchanged registered source/model license/provenance. Native execution only after fixture and source-only prompt tests GREEN, independent review and original pinned artifacts installed. Use the existing serialized native-owner concurrency group; no competing heavy jobs. Native score is descriptive: report per-arm exact 0–9, per-label breakdown, wrong-typed-follow count, raw output, source/runner/model hashes, closed Store and process receipts. A source-only score ≥7/9 with ≥2/3 in each label is only a **small pilot signal**, not independent reasoning/STEP2 proof. Preserve failures and any missing-artifact RED.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no Redmi/learning/whole-system promotion. Next: implement fixture and software-only integrity tests, verify original raw, then consider serialized native run. Remaining platform budget UNKNOWN.
