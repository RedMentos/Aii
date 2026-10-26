# Run491 — prospective source-only preregistration for a new STEP2 ten-episode native cohort

**Registered 2026-10-26 before Run491 inference or fixture script CI.** This is a *new* held-out fixture set, not a replacement or reinterpretation of Run394/397/479, Z2, or canonical STEP2 gates. Source-only preparation does **not** count as native evidence.

## Frozen source, models and cohort

- Fixture constructor: unchanged `v13/code/scripts/step2_z2_timescale.py`, Git blob `2ad62fbbf1f6463d99360cdb8198f1104cfdfaf7`, specifically `episode`, `sheet`, `eligibility.recipe` and 3 preparation turns.
- New fixtures (name, type, rules budget/deadline/local-only, Option A cost/days/local, Option B):
  - Vesper SPLIT (113,6,true) (72,5,true) (61,7,false)
  - Willow SPLIT (96,4,false) (80,6,true) (92,3,false)
  - Xenia SPLIT (88,7,true) (62,4,false) (73,5,true)
  - Yarrow SPLIT (104,3,true) (90,2,false) (111,2,true)
  - Crescent SPLIT (127,8,false) (93,7,false) (89,6,true)
  - Asteria SPLIT (78,5,true) (55,4,true) (54,5,true)
  - Boreal RULE (142,4,true) (120,3,true) (110,5,false)
  - Cascade RULE (91,6,false) (88,5,false) (76,7,true)
  - Drift DETAIL (107,7,true) (103,4,true) (95,6,false)
  - Eon DETAIL (84,4,false) (79,3,false) (68,4,true)
- Oracle actions (in order): A, B, B, NONE, B, B, A, A, A, B. **Never UNKNOWN.** Exactly 6 SPLIT / 2 RULE / 2 DETAIL. The options in SPLIT/DETAIL history begin after source character 240 and before 600; B2 240-char excerpt lacks them, B1 600-char recent window includes them.
- Canonical JSON `json.dumps(fixtures,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)` SHA256: **`c434a5765ed85b7c51022c5aaea0ba4c3150ef0f1490f466b4a8833e41b44c63`**. Do not regenerate with different values, IDs, type ratios, order or schema.
- Native model/runner baseline hashes from original Run479 source receipts, **not a claim they are available now**: B1_DETAIL `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, B2_GIST `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, C3_LANGUAGE `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, llama-server `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Exact model revisions B1 `6767265158422fb8a19c62ceb45f16f05363615b`, B2 `8fea620810c4afa23dd6443f999a48574c1611a3`, C3 `657e078c94084481950a2d555a941481f715536b`.
- Planned **new** seeds: 31, 32, 33. Do not mutate any older registered seed. Models must be retrieved only from pinned public, license-verified sources and SHA-checked before a real run. Never substitute a model or claim native evidence from a synthetic fixture test.

## Frozen candidate and controls

Reuse original seven STEP2 variants (b1_only, b2_only, both_none, both_exact, both_control, same_policy_dual, prompt_only_dual), real B1/B2 distinct weights and the unchanged WP-Z2 arms A/B/C/D/E (quote context, recent B1 horizon, shared-body control). Primary C two-body with B1 window 600 and B2 long window, D shared-body control; compare B1-only, B2-only, same-policy dual and prompt-only dual. Read decision fields using existing deterministic `eligibility.read_fixed` with source-verified quotes; no oracle in native messages or model prompts. C3 remains a separately measured language/answer path, never silently removed from the full V13 acceptance.

## Acceptance criteria fixed before native execution

A native trial is **not** accepted unless every registered fixture/variant/seed/arm row is complete and hash-bound; independent source/consumer quote provenance is verified; no data leaks or invalid scores; B1/B2 have distinct and complementary field error profiles (option and rule advantages each >= 0.25), each body wins at least one episode against the other, C both_exact exceeds C best single, same-policy dual, D prompt-only dual, and D both_exact, with paired seed/fixture reports and no wrong committed unsupported actions. Negative evidence and timeouts are retained. Additional requirements of the full canonical ten-episode STEP2 gate, B3 receiver, native JEPA and Redmi are **not waived**; this new experiment alone cannot promote STEP2, B3, Body-JEPA, jepa_weight or Age.

## Staging / ownership

Stage 0: source-only frozen-fixture generator, hash/role-isolation tests and independent review. Stage 1: source/model license and SHA preflight, original owner/active-job check, source-only installation proof. Stage 2: serialized native pilot with explicit first two fixtures/one seed, preserving RED, then full 5-arm × 3-seed × 10-fixture × 7-variant **1,050 consumer rows** only if native capacity and budgets allow. No paid provisioning or device assumption. Stage 3: independent receipt/utility/causal-control audit and Redmi confirmation if possible. A source-only PASS is **not** Stage 2.

**Current gates:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, Redmi unmeasured, Age0/approval unchanged.
