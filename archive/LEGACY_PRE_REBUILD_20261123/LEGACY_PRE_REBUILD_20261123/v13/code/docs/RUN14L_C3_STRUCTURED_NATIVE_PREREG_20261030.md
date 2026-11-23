# Run14L — preregistered disjoint pinned C3 structured JSON vs copy native (2026-10-30)

Owner: GPT-6 V13 continuation. Review-only child of Run14K PR #1328, commit `033cd9326cb2c7b8329f577b8eb32ded3839987c`. This preregistration is committed **before** creating the fixture, test, native runner, verifier or launching native calls. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Run14K structured module blob `41ae26e01932ea7e89188e3a544bef103f1b3ec6`; Run13M fidelity blob `82d1f1e2af5bf565f9d5f081844e1da55c88084c`. Original Run13J/K/L/T cohorts, raw and negative outcomes stay frozen.

## Research question and limits

Run13T seed283 strict-copy native gave 0/8 exact copies in both arms, with strict-copy source-facts 0/8 vs baseline 3/8 (FIDELITY_HURT). Run14K adds a deterministic six-slot source-bound JSON SHADOW verifier, not a model improvement. Does the pinned native C3 produce **more fully source-faithful outputs** under the Run14K JSON protocol than under the existing Run13L copy protocol on a **new disjoint** set? The two arms differ in both user and system prompts, so any difference is attributable only to the **combined protocol**, not the system instruction or JSON alone.

## Locked cohort and experiment

Seed **307**, exactly eight invented cases in this exact order. Each row: project, budget, option A, A cost, A days, option B, B cost, B days.

1. Aster307, 6800, Lumen, 2370, 9, Coral, 3185, 12.
2. Birch307, 9200, Onyx, 4860, 16, Moss, 3545, 8.
3. Cedar307, 11300, Amber, 5290, 13, Quartz, 6575, 17.
4. Dune307, 7800, Slate, 3045, 19, Pearl, 4205, 15.
5. Echo307, 12500, Iris, 6910, 7, Flint, 5725, 11.
6. Fable307, 10400, Ruby, 3960, 23, Opal, 5120, 18.
7. Grove307, 8900, Cobalt, 4375, 6, Sable, 2980, 14.
8. Harbor307, 14200, Ash, 7080, 21, Jade, 6340, 10.

Canonical `json.dumps(tuple(cases),sort_keys=True,separators=(',',':'))` SHA256: `a598c5f6eed3c956c3aa2f1e6f9419b8054d155e1f145aa0ca58776b26f1ffd1`. Fixture is frozen before native. Two arms/case = **16 actual native calls** with parity-counterbalanced order. `COPY_BASELINE`: existing Run13L `SYSTEM_COPY` and Run13K `COPY_DIRECT` user prompt. `STRUCTURED_JSON`: **exact Run14K** `SYSTEM` and `PREFIX + verified JEF answer`. The underlying Store/ContextOS/JEF source and answer must be identical across arms in each fresh per-case Store. Native model is pinned `LFM2.5-350M-QAD-Q4_0.gguf`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, revision `657e078c94084481950a2d555a941481f715536b`. No new model selection. Age0 RECORD_ONLY, seed307, temperature0, 128 output tokens, context1024, deadline180s; model reaped between calls; no assistant message egress. Single serialized GitHub Linux-native job, never competing with active native owner.

## Frozen scoring and evidence requirements

For COPY_BASELINE: exact bytes of JEF answer, deterministic Run13M four-fact grammar (fully correct source facts), and original Run13J numeric/faster/strict-full score. For STRUCTURED_JSON: strict Run14K `audit_slots` exactly six source-verified typed fields, no extra keys, duplicate fields or commentary; original Run13J text scorer is **not** applied to JSON. Comparable primary endpoint is **full source-faithful output**: Run13M FACTS_EXACT (copy) vs Run14K SLOTS_EXACT (structured), 0–8 each. Exploratory protocol signal only if structured >= copy +2 cases, all 16 native FINAL/reaped, zero autonomous egress and no wrong accepted facts; otherwise `NO_BOUNDED_FIDELITY_SIGNAL` (or `FIDELITY_HURT` if structured below copy). Report 6-slot success, copy exact, numeric/faster baseline separately, per-case raw and prompt/system/model/source/answer/output hashes. An independent verifier must reconstruct prompts, source answers, expected slots and both scores from original fixture, reject missing/duplicate/tampered rows, nonfinite JSON, reused PIDs, missing native metrics or wrong negative gates. Never infer production quality from a synthetic eight-case sample.

Prerequisite sequence: prereg commit -> fixture/runner/verifier/test commits -> source-only CI GREEN -> check active native owners -> native CI (keep all original raw including failures) -> independent raw replay -> ZIP SHA256/CRC/inner SHA256SUMS and durable permitted backup/readback -> checkpoint. Native failures remain failures; no reroll.

## Containment and negatives

No model training, adapters, auto chat delivery, tools, weight updates, new Age authority or whole-system gate. No production merge. STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi unmeasured; whole V13 incomplete. Native execution is Linux-native only, not Android proof. Existing Canon and safety/approval gates unchanged.
