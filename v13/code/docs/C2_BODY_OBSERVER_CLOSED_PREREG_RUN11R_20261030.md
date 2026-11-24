# Run11R preregistration — C2/C3/Body observer-isolated, post-close paired pilot (2026-10-30)

Owner: GPT-6; review-only child of PR #1246 exact HEAD `5b6c515a058725fe3db88c0daf07505187ac5c72`. This preregistration MUST be committed before any new runner/test/workflow source. Do not modify original seed47/53/59, frozen Run11Q scorer, native outputs, model pins, Canon, or production Runtime.

## Question and disjoint controls
Previous original seed53 24-turn Linux-native pilot is **PILOT_PARTIAL_RED**: 8/24 rows invalid because background observers contaminated all B1-only and B2-only arms; seed59 one native B2 release receipt was sampled before `Runtime.close()`, invalidating 1/12. Neither result proves complementarity or C2 utility. The new cohort tests whether isolated single-organ baselines and post-close receipts yield valid paired evidence; native auto is evaluated separately from forced routing. Do not relabel historical RED.

Fixed new synthetic seed **163**, four fresh tasks (source project, budget, A/cost/days, B/cost/days; withheld exact remainders):
- Mistral163, 368, Cedar/219/5, Garnet/327/2; 149/41.
- Lyra163, 247, Haven/178/7, Violet/226/3; 69/21.
- Orion163, 431, Maple/294/4, Quartz/389/8; 137/42.
- Nova163, 312, Saffron/235/9, Juniper/283/1; 77/29.

Fixture list canonical JSON SHA256 `040e073bc1c544883a5d809d0883d6493366a8f241816c7e6dbefd30c87eaead`. Identical source prompt in all arms, using seed59-style simple-scaffold phrasing (`For PROJECT, I have a spending ceiling...`) with no answer leak. Require `scaffold_route(prompt) == "simple"` before running. Use same source per fixture, four independent fresh Age0 Runtime instances per arm? **One independent Runtime per fixture/arm: 24 total**, no shared history, cache, learning, or model mutation.

Six preregistered arms in cyclic order (rotate by fixture index):
A_C3_ONLY: forced simple, observer OFF, B1/B2 uninstalled, C3 FINAL.
B_B1_ONLY: forced detail, observer OFF, B1 FINAL, no B2 observer offer.
C_B2_ONLY: forced gist, observer OFF, B2 FINAL, no B1 observer offer.
D_DISTINCT_BOTH: forced both, observer BACKGROUND, two distinct B1/B2 model identities.
E_SHARED_DUAL_COLD: forced both, observer BACKGROUND, one Body model in two cold states (not evidence of learned state divergence).
F_NATIVE_AUTO: auto, observer BACKGROUND, same simple-scaffold prompt, genuine native Needle/C2 call and route selection measured separately; never infer selection from invocation.

All arms: `learning_mode=RECORD_ONLY`, `system_stage=0`, `user_stage_cap=0`, `latents_enabled=false`, `teacher_enabled=false`, `jepa_weight=0`, `history_turns=0`, no tools or external actions, exact installed model hashes checked. Preserve `b2_control` model identity and original catalog/Canon Git blobs. Serialize heavy calls under existing native concurrency owner; **software preflight only on push; native requires explicit separate trigger**.

## Evidence and frozen scoring
Capture exact original `audit_event`, source refs, session/event IDs, C2 control packet and native PID evidence, final runner role/model, B1/B2 offers, pre-close and **post-close** process release histories and native process reaping. For B/C with observer OFF, **zero observer offers required**; verify exactly the requested Body FINAL role/model and its own release after close. For D/E, both offers and both model identities required, with both process releases. For F, compare native C2 selected route with simple scaffold, and preserve BOOT_SCAFFOLD separately. Missing or unexpected observer/runner/model/release/source evidence invalidates row and scores zero. Retain failed attempts without retry/substitution. Do not equate an absent pre-close release with a leaked process.

**Primary fixed score:** Run11Q `score_option` narrow explicit option-linked remaining-Euro claim grammar; 1 point for each MATCH only, contradiction/conflict/unscored=0. All four tasks, max 8 points per arm. Secondary exploratory seed53 `score_pair` lexical+equation contradiction-veto readout reported separately; never choose the better result after observing outputs. Invalid native rows score zero in both. Report per-arm raw scores, invalid rows, route selection, source provenance and latencies. Descriptive pilot signal only: 24/24 valid, D primary >= max(A,B,C)+2 and D >= E+2; native auto utility separately requires >=1 actual selected route and F >= A+2. No statistical claim, no STEP2 gate.

## Acceptance and containment
New standalone runner and adversarial tests, software-only CI, exact prereg/source/canon hash checks, privacy scan, closed SHA256SUMS. Before native, verify current heavy owner and model availability; do not launch overlapping native jobs. Native result, if later executed, must be independently audited from original ZIP, CRC, inner hashes, 24 rows and reaped receipts and privately backed up. No software/synthetic result is Linux-native or Redmi evidence. Preserve Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight0, Redmi UNMEASURED, whole-system incomplete. Original seed53/59 RED and historical Run34/Run37 RED remain. No main merge or production promotion.
