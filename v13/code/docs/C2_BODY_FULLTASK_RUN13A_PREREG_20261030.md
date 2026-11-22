# Run13A — prospective full-task native C2/C3/B1/B2 utility, seed211 (2026-10-30)

Review-only **new disjoint cohort**, preregistered before any Run13A native execution. Parent PR #1276 HEAD `e5529bea8316b0c05825f3efcf14dac7a665ca0e`. This does **not** revise or rerun original Run12N seed197, original Run12M seed181, Run11Y seed197 (different source names), any failed raw, frozen Run11V scorer or production routing.

## Frozen task source, exact baseline and models

- `docs/fixtures/c2_body_fulltask_run13a_seed211_20261030.json`, schema `v13.c2_c3_body.fulltask.run13a.fixture.v1`, seed **211**, **eight** new project sources. Canonical SHA256 of `json.dumps(tuple(cases),sort_keys=True,separators=(',',':'))`: **`e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f`**.
- Projects: Beacon211 (487; Cedar318/6d, Quartz429/2d), Lantern211 (653; Maple477/3d, Briar588/9d), Nimbus211 (734; Aspen516/8d, Delta642/4d), Harbor211 (568; Slate394/5d, Opal507/1d), Prism211 (821; Pine605/2d, Frost748/7d), Orion211 (469; Moss337/9d, Larch411/6d), Summit211 (912; Echo699/4d, River835/3d), Meadow211 (397; Flint248/7d, Willow351/5d).
- Source prompt exactly frozen Run11V `frozen.prompt(fixture)` style one; both arithmetic remainders and faster option omitted from prompt, scaffold simple; reject any duplicate project, leak or previous full-prompt match. Eight Latin-square cycles across four arms: A_C3_ONLY simple, B_B1_ONLY detail, C_B2_ONLY gist, F_NATIVE_AUTO auto, **observer OFF in all arms**. **32 isolated Linux-native Store turns**, 8 per arm. No background body offers allowed.
- Frozen Run12N pinned models/source/Runtime/C2 strict admission and Run11V contradiction-veto `score_pair` **numeric** scorer remain unchanged. New full-task component is a **prospectively frozen** explicit faster-choice lexical parser `scripts/c2_body_run12n_fulltask_readonly.py::explicit_faster_claim` (blob `7324f5c8c09d5e5706c40887f755285dcdcbb9a8`), not semantic entailment. An explicit wrong/ambiguous/abstained faster choice scores zero; require both numeric remainders **and** correct faster claim for a strict whole-turn point. Record 0–3 component score per turn and strict full-answer 0/1, alongside unchanged numeric primary/secondary scores. No posthoc exclusions.
- Existing JEF Run11Y `budget_en_source_shadow.propose` is a **separate no-model, source-bound SHADOW baseline**: must return 8/8 exact budget remainders and faster option on the same frozen prompts with zero authority/native calls, or fail preflight. It is NOT an active repair, training target or fair general-language comparator.

## Frozen prospective acceptance (pilot only)

1. Source preflight: fixture SHA and disjointness, source answer-leak checks, 8/8 JEF SHADOW proposals, negative controls, actual Runtime API contract, full-task scorer counterexamples and privacy; exact hashes committed before native.
2. Native structural: **32/32** original raw+preclose+postclose source-bound valid, **8/8** F native C2 invocation/reap and strict unique-tool admission, zero observer offers, model hash pins, original ZIP SHA256/CRC/manifest and private byte-exact backup. Preserve every RED row, no deletion or retry-based filtering.
3. Exploratory comparative signal (NOT STEP2): at least **2/8** F native non-simple routes; F numeric primary >= best of A/B/C **+3/16**, AND F strict full answers >= best A/B/C **+2/8**. Report all arms and the JEF baseline separately. No threshold change on failure; this is small synthetic evidence, not generalization.

## Safety, blockers, next exact command

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole V13 incomplete. No production routing changes, no JEF/tool authority, no model training or paid provisioning.

Next: implement a new Run13A runner/verifier derived from corrected Run12N actual Runtime API, preserving the seed211 frozen fixture and exact existing scorer. Add independent source-only tests and CI. Only after GREEN and no active heavy owner, launch one serialized native job in `v13-step2-budget-paired-native-20261030` concurrency group. Independently audit original ZIP and backup privately. On native RED, preserve failed attempts and continue another independent canonical package.
