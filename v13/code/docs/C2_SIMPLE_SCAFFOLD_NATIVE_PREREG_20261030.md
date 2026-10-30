# V13 C2 actual route-selection utility cohort — prereg 2026-10-30

**Owner** `codex/v13-c2-simple-scaffold-native-20261030-hourly11d`, independent child of seed53 review branch at `e5d1c9b90670006989ac161246aa2793384fc319`. This prereg is frozen **before new source/tests/workflow**. Seed41 STEP2 v3, seed47 native smoke, seed53 six-arm cohort, original models and scorer are immutable.

## Question

Current `Runtime._route` only adopts a native C2 advisory proposal when `scaffold_route(text) == simple`. Seed47 and seed53 prompts begin “Compare” and scaffold to `both`, making actual native route selection structurally impossible even if C2 genuinely runs. Those are invocation/Body integration observations, **not tests of C2 routing benefit**. This new cohort uses source tasks with a deliberately simple scaffold, so native C2 can actually select a non-simple route without changing production authority or bypassing any gates.

**Seed 59, four fresh disjoint synthetic source tasks** with fixed compact sorted-key JSON SHA256 `610b7b1c2b2d203b6388a7717394cd9c7c8460f434509167286e7bf7a972e651`:
- Marlow59 ceiling 375 Euro, Citrine cost218/days6, Sparrow cost332/days3; remainders 157/43.
- Peregrine59 ceiling 294 Euro, Nectar cost183/days2, Saffron cost267/days7; remainders 111/27.
- Lantern59 ceiling 418 Euro, Beryl cost259/days8, Cypress cost386/days4; remainders 159/32.
- Tide59 ceiling 236 Euro, Mistral cost174/days5, Hearth cost211/days9; remainders 62/25.

Frozen prompt grammar: “For {project}, I have a spending ceiling of {budget} Euro. {a} uses {a_cost} Euro and needs {a_days} days. {b} uses {b_cost} Euro and needs {b_days} days. Everything stays local on my device; no cloud. How many Euro would remain after each named choice, and which one finishes sooner?” No remainder leaked. Assert the actual imported `scaffold_route` returns `simple` for all four before native.

**Three arms per fixture, 12 independent Age0 Runtime turns, cyclic arm order**:
- A_FORCED_SIMPLE: operator override `simple`, observers off, C3-only, no B1/B2.
- B_NATIVE_AUTO: `route_override=auto`, observers background, genuine native Needle/C2 C/FINAL with ExecutiveControlContext and exact source/event/session/PID/process-reap proof. Native-selected route is distinct from mere invocation and only credited if actual `NATIVE_C2_ADVISORY`.
- C_FORCED_BOTH: operator override `both`, observers background, distinct B1/B2 Qwen and LFM Body, no native C2 authority.

Seed59, no history, no learned state, stage0 RECORD_ONLY, jepa_weight=0, latents/teacher disabled, no external tools/actions, all pinned model bytes/versions. Same prompt per arm; fresh Runtime for every turn; no retries/substitutions; preserve every failed attempt. All heavy native inference serialized under existing `v13-step2-budget-paired-native-20261030` concurrency group; queue behind seed53 if still running.

**Preregistered score**: two option-bound exact source remainder points per row, using unchanged seed53 `score_pair` (frozen lexical + explicit-equation diagnostics, contradiction veto); max 8 per arm. Invalid source/model/route/role/reaping row scores zero. Route-selection rate, Body offer paths, time and process memory separate descriptive outputs. Exploratory signal only if all 12 native rows valid, B_NATIVE_AUTO actually selects a non-simple route on at least one task, and B scores at least A+2 while not worse than C. This is not powered for a gate; no STEP2 promotion regardless of result.

**Required raw proof:** immutable fixture/prompt/seed/model hash; route override vs native control; exact source/context/event/session; Needle process PID equals C2 metrics PID and reaped; native FINAL model role/name; B1/B2 offers and reaped receipts; source-bound final output and raw audit; scoring and negative gates. Any absent evidence is RED, not synthetic/native proof. Software preflight and original raw closure before native. Linux-native only; no Redmi evidence, no AGI/whole-system acceptance.

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, all approval/learning gates remain closed. Next: implement isolated source/tests; verify source-pinned software preflight; queue bounded native after seed53; independently audit raw ZIP and private backup.
