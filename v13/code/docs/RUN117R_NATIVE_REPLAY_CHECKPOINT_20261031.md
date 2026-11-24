# Run117R — original Run116 native C3 text replayed through new Run117P postgen guard

## Scope and provenance

Review-only branch `assistant/v13-run117r-native-output-replay-postgen-20261031-hourly11`, parent `acc014728918a2d1cf1c382693996243a8ab7fa6` (Run117Q #1497, itself stacked on Run117P #1496 and Run116 #1495/#1494). No original model/source/seed/fixture changes; original Run116 artifact 13051756857 SHA256 `71de9bb7bc2899f5aee67f58b55d13514d0a9b0d870cd98ae5e8f2f1850d11c5`, native source HEAD `df08a4ce311317bdfd322ba7c7520d9fe8fb2b93`. Canon, AGENTS, registered cohorts, user decisions and all negative gates unchanged.

## Executable integration evidence

`run117r_native_output_postgen_replay.py` first calls Run117Q's original ZIP+fixture+score auditor, then reconstructs six exact USER text pairs as **new real SQLite Store events** and produces intentionally wrong **synthetic B1/B2** offers. It invokes the new Run117P default-OFF post-generation guard with explicit operator/callback opt-ins, passing the exact recorded **original native C3 output strings** as callback returns. It checks prompt/source/offer/JEF/ContextPlan revalidation, correct JSON `choice` **and** `remaining`, zero output/tool/learning authority and no Store actions. The original native text is not regenerated or modified; replay's new Store event IDs and synthetic Body offers are not original native provenance.

**Result:** on six cases, RAW_TWO_SOURCE_ROLE outputs accepted **1/6** and refused **5/6**; TYPED_JEF_ROLE accepted **6/6**; TYPED_JEF_WITH_BODY_ROLE accepted **6/6**. All 18 guard evaluations performed exact source rechecks, all left output/tool/learning authority at zero. The result agrees with independent original-native scores. This is **software replay of original native text**, not new native inference, not real native Body+guard integration, and not proof of C3 reasoning, B1/B2 complementarity or learning. The typed candidate was the deterministic oracle already present in C3's USER-role prompt.

Local replay JSON SHA256 `7614df23523938da23fbe0d903f329b8d3cfcbefc8343fef0ba436841fac601f`; new 3 synthetic ZIP tamper tests PASS (forged native score, wrong outer hash, wrong raw output refused). **Combined 67/67** new + inherited source tests PASS, compile PASS, Python 3.13 Linux/software; combined raw SHA256 `5241e2fe3b80c40af2ffe8211fa59d19189495b844774993b45d5dfa68dfdbcc`. Source SHA256 `8b8b72199a0245827e4fc72a7bd541e6fb59c4914438fea371ad425f45d21503` / Git blob `c3888048641b9cb126c54b5c6561c0ac633799f8`; tests SHA256 `bf98ca2748179c1b3cece69b5c59ca51e8180cb50d43aa152828f0405f4f4397` / Git blob `2f9f37c95a26c8c650bdf4fcac0533f99b837092`, fetched remote. Private checkpoint `/V13-Checkpoints/2026-10-31/Run117R-Replay/`.

## Next, blocked, negative gates

- CI: Actions downloads exact original Run116 artifact, validates SHA/CRC and source pins, runs replay + 67 focused tests + compile/privacy/diff, retains raw receipt. Download and independently verify CI artifact bytes, inner hashes and replay JSON; back up privately. No native model download is required for replay.
- Next **substantive functional work**: preregister new disjoint Body-complementarity cases where B1/B2 provide independently source-verified useful information beyond deterministic typed JEF. Include raw and deterministic source-selection controls; run actual native B1/B2/C3 with pinned models and separate raw evidence. Avoid claiming benefit from this six-case copy task.
- Original Redmi unavailable; native JEF/C2 not measured by Run116; STEP2 remains UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA unavailable, World-JEPA SHADOW, `jepa_weight=0`, Age0 RECORD_ONLY, no live output or tool authorization, whole V13 incomplete. No approval receipt accepted.

Reproduce with original artifact and review source:

```sh
cd v13/code
python -m scripts.run117r_native_output_postgen_replay --original-zip ORIGINAL_RUN116.zip --out REPLAY.json
PYTHONPATH=. python -m unittest -v tests.test_run117r_native_output_postgen_replay
```
