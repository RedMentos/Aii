# Run295 — genuine native B1 source placement, negative controls (NOT SUPPORTED)

2026-10-25 UTC. Exact code head `4d0c085befaf25ce5562b42c4d1a65c48bb30f41`, base verified Run294 checkpoint `75637b76b3520c444f79a1c8bae88ef69c1b6816`, draft PR295. Independent owner: new `scripts/run295_b1_source_placement.py`, `tests/test_run295_b1_source_placement.py`, dedicated serialized native workflow, this proof. No production runtime, prompts, model, seed, Canon, learning/age/approval gates or original registered cohort changed.

## Frozen actual native source

Run288 closed Linux-native raw `12600061321` (SHA256 `940a7a066521318137fb10a230bcd65969aeb3e440865fbd889efd59946026ca`) had B1 exact stored `400 Euro` correction delivered, but B1 ignored it. Run291 source-first *system suffix* was NOT_SUPPORTED. Run295 reconstructed the exact Run288 B1 two-message prompt from unchanged canonical prompt and deterministic JSON; frozen prompt SHA256 matched `54f859ca3667028b4ea83fbd91b46b4c5c85627868f795d1da3ed0e4c70d333c`. This is synthetic project text, not private user data.

Pinned native B1 model SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, model revision `6767265158422fb8a19c62ceb45f16f05363615b`; native server SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Runner source SHA256 `18db214f930953a5f781aa8aaa2b4425e048fd8bacf7848793c112a4e06af798`, prompt source SHA256 `198a7cbff32f7b1880b2398ed1e14f65d334aa212f3eab4a943c889c0f4a6e52`. Linux x86_64, seed 13, 64 tokens, sequential actual-weight generation, process unloaded after each of nine calls. No Redmi measurement.

## Frozen outcomes

| Arm | Matching project+topic | Wrong topic same project | Wrong project same topic | Safe candidate |
| --- | --- | --- | --- | --- |
| Baseline exact Run288 prompt | Does **not** use `400 Euro` | No `400 Euro` | No `400 Euro` | NO |
| Additional user-source message | Uses `400 Euro` | **Leaks `400 Euro` into team leadership** | **Falsely attributes `400 Euro` to Kelmo17** | **NO** |
| Plain-language system-source summary | Uses `400 Euro` | **Mentions irrelevant `400 Euro`** | **Misattributes `400 Euro` to Kelmo17** | **NO** |

All nine actual B1 generations completed FINAL, nonempty, and all nine unloads reported `process_reaped=true`. This is not a native utility success: the two candidate arms fix exact-value mention only by breaking topic/entity isolation. The Run295 diagnostic status is **`B1_NATIVE_PROMPT_NOT_SUPPORTED`**. Neither arm was integrated or enabled. Wrong-topic leakage remains a concrete safety/accuracy blocker.

## Test and raw evidence

- Source-only CI (same exact head): **8/8 PASS**, frozen SHA and source placement controls, privacy CLEAN. Independent local extracted Phone source: **8/8 PASS**.
- Native CI `40201285153`: bootstrap exit `0`, native exit `0`, privacy exit `0`, native validity `true`, but candidate verdict **NOT_SUPPORTED**. The workflow exit `0` means complete diagnostic, **not** a successful memory gate.
- Closed native raw GitHub Actions artifact `12601818140`, ZIP SHA256 `c17b2d18ba3c1e35396759b9dbf9b4f32f5739ad5363f6a9c20c7ed1a3297593`, contains all nine actual outputs, exact prompt hashes, source/model hashes, timings, failure classifications, bootstrap and privacy logs.
- Focused source-bound Phone ZIP artifact `12602135440`, outer ZIP SHA256 `94eae3ddeaea988efd58ec801e76da5778c2447cc971142135d307246643d20b`. This is a Linux source archive, not Android execution.
- Both raw native and source ZIPs saved to private Library `/V13-Inquisition/Proofs/Run295/`, materialized back and verified SHA256 plus byte equality. No anyone-writable Drive destination used.

## Interpretation, gates, exact next step

The bottleneck is not simply missing exact source bytes: B1 sees the source but ignores structured JSON; moving the same source to more salient prompt positions causes indiscriminate copying across unrelated questions. A future approach must bind *both* source value and query topic/entity, then verify the **actual output** before display. Do not promote this prompt-only path; preserve C3's earlier source-use observation and negative controls.

Next authorized independent package: preregister a topic/entity-bound source-use gate or constrained receiver with held-out wrong-topic and wrong-entity controls; do not alter PR284 Runtime or PR293 output-adapter owners. Alternatively pursue native STEP2 complementary utility or Body-JEPA interfaces on independent owned files. Before any native repeat, check active serialized owner and pinned model/source bytes. Never rerun this same failed prompt-only cohort expecting an improvement without a new technical mechanism.

Unchanged negative gates: `STEP2 UTILITY_FAIL`, `B3 L1 FAIL`, `Body-JEPA UNAVAILABLE`, `jepa_weight=0`, Redmi UNMEASURED, V13 INCOMPLETE. No user-brain training, no learning approval, no production prompt change.
