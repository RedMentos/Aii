# Run117DA prereg — disjoint C3 source-only JSON-schema ablation (2026-11-01)

Review-only child of Run117CX `1719870530b7b7702660f9518dcf5b556077e811`. This preregistration is committed **before** new fixture, runner, tests or native execution. Previous original [Run117CX native 41262163859](https://github.com/RedMentos/Aii/actions/runs/41262163859): 18/18 Linux-native FINAL/reaped, LFM350M 3/9 and Qwen0.8B 3/9, both chose NONE on all 9, paired net0; original CI RED due copied verifier schema typo, independent raw audit and private backup preserved. This result motivates a **new disjoint cohort**; do not retune or rescore original seed117041.

## Frozen independent cohort

Seed **117053**. Twelve fixed rows, four A/four B/four NONE, unique projects DA01–DA12 not present in Run73/75/83/117CN. Fixed table SHA256 (JSON sort_keys, compact separators) **`78ec82002dafa54bcd9bb09456a0351123d2974bf12222fa6b20794d44f2edfb`**. Columns project/domain/bound1/bound2/(threshold1,threshold2,required_sealed)/(optionA1,A2,sealed)/(optionB1,B2,sealed)/expected-for-offline-scorer-only:

```python
TABLE = (
 ("DA01","harbor buoys","Minimum","Maximum",(100,20,True),(120,15,True),(90,10,True),"A"),
 ("DA02","canal tugs","Minimum","Maximum",(80,15,True),(70,12,True),(90,14,True),"B"),
 ("DA03","cliff beacons","Maximum","Minimum",(120,20,True),(100,15,True),(130,25,True),"NONE"),
 ("DA04","wind probes","Maximum","Minimum",(200,10,False),(150,12,False),(180,11,True),"A"),
 ("DA05","river gauges","Minimum","Minimum",(70,10,True),(60,15,True),(75,11,True),"B"),
 ("DA06","lab samplers","Maximum","Maximum",(150,20,True),(120,10,False),(130,15,False),"NONE"),
 ("DA07","forest sensors","Minimum","Minimum",(100,15,False),(105,16,False),(115,18,False),"A"),
 ("DA08","archive skiffs","Maximum","Maximum",(140,25,False),(130,30,True),(135,20,False),"B"),
 ("DA09","polar monitors","Minimum","Maximum",(200,10,True),(210,12,True),(190,9,True),"NONE"),
 ("DA10","urban relays","Maximum","Maximum",(160,30,True),(140,25,True),(150,20,True),"A"),
 ("DA11","desert robots","Maximum","Minimum",(90,18,False),(100,25,True),(85,19,False),"B"),
 ("DA12","island rovers","Minimum","Minimum",(120,30,True),(125,25,True),(115,35,True),"NONE"),
)
```

All source text must use the existing `tests.test_jef_range_policy_shadow.texts` and frozen `jef_range_native_fixture_773.oracle`; source-only envelope via real SQLite USER policy/sheet/current F1/F5/JEF admission, exact original Run117CM `SYSTEM`, no typed JEF action/oracle in model messages. Verify table hash, disjointness, source hashes, exact source role lineage before native. Labels scorer-only.

## Frozen native protocol and falsification

Exactly **12×2 models×2 decoding modes = 48 serial Linux-native C3 calls**, no parallel model loads. Models unchanged: LFM2.5-350M-QAD-Q4_0.gguf revision `657e078c94084481950a2d555a941481f715536b` SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; Qwen3.5-0.8B-Q4_0.gguf revision `8fea620810c4afa23dd6443f999a48574c1611a3` SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`; pinned llama.cpp b10964 SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Same two source-only messages per row across four arms. Decoding arms `SCHEMA` exact frozen Run68 action schema and `UNCONSTRAINED` `schema=None`; temperature0, seed117053, two threads, max128 tokens, 120s per call. Rotate arm order by row index over `(LFM_SCHEMA, QWEN_UNCONSTRAINED, LFM_UNCONSTRAINED, QWEN_SCHEMA)` to balance order. Unconstrained text is scored **strict JSON only** with the original Run75 scorer; never award semantic partial credit. Save raw even on failure, actual model, source/message SHA, native metrics, process-reaped proof, no output delivery.

Primary within-model contrast: strict exact action score schema vs unconstrained /12; paired gains/losses, NONE-only frequency and non-NONE accuracy /8. Exploratory schema-decoding signal only if one model's UNCONSTRAINED >=7/12, paired net >=3 and >=5/8 correct non-NONE, with **all 48** FINAL/reaped/hash-bound; otherwise `NO_EXPLORATORY_SCHEMA_SIGNAL` or `STRUCTURAL_RED`. This is a small known synthetic source task, not independent real-world reasoning or STEP2 acceptance. No model weight training, no teacher/typed action, no native Body/JEF/C2, no Redmi. Preserve all failures, licenses/provenance and negative gates.

## Ownership

Run117CY native real Store source callback is an independent owner. **Do not launch Run117DA heavy native until CY terminal**. Use same concurrency group `v13-native-c3-ag12-20261030`, cancel-in-progress false. First software preflight, independent review, original ZIP CRC/inner hash and private Library backup. No rejected anyone-writable Drive retry, no production merge. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no whole-system promotion.
