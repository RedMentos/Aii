# V13 disjoint C2/Body controlled utility pilot prereg — 2026-10-30

**Owner:** `codex/v13-c2-body-controlled-native-20261030-hourly11c` (independent child of PR #1210 HEAD `373d50e92c698163aa4ac773f46f27ec13379e85`). **Frozen before script/tests/CI/native.** Original v2/v3 cohorts, seed47 auto smoke, original scorer and raw are immutable. Review-only; no main merge, no production authority, no model/source/catalog edits.

## Hypothesis and controls

Does a genuinely distinct B1+B2 pair improve source-bound budget remainder answers over C3-only, B1-only, B2-only and same-model dual-state controls? Does genuine native C2 auto routing select a different route than scaffold, and does it help? Previous original v3 27 native rows scored 0/10/9 lexical A/B/C, expression-only posthoc identified 3 correct C3 equations; seed47 native C2 3/3 invoked but 0/3 selected, Body final 2/6 remainders exploratory. These are not utility proof.

**Fresh fixed seed 53, four unseen disjoint synthetic tasks**, canonical compact sorted-key JSON fixture SHA256 `7c5da29e274c3d63a34b68baac6ac9b6e31a968d5632b938eff7de01cf2f24d4`. Fixture tuples (project, budget, option A/cost/days, option B/cost/days; expected remainders):
- Cedar53, 382, Sable/241/6, Tern/317/3; 141/65.
- Flint53, 293, Lark/169/2, Ember/257/8; 124/36.
- Quartz53, 417, Mica/286/7, Dune/359/4; 131/58.
- Vale53, 264, Reed/187/5, Fawn/239/9; 77/25.

Prompt grammar exactly the previous seed47 source grammar, without expected remainders. **Six arms** per fixture, 24 distinct isolated Age0 Runtime instances, cyclic arm order shifted by fixture index, no shared history or learned state:

A_C3_ONLY: route_override=simple, observer off, no installed B1/B2; expected C3 FINAL.
B_B1_ONLY: route_override=detail, observer background, two_body catalog; expected B1 observer + B1 FINAL.
C_B2_ONLY: route_override=gist, observer background, two_body catalog; expected B2 observer + B2 FINAL.
D_DISTINCT_BOTH: route_override=both, observer background, two_body; expected B1+B2 offers and one Body FINAL.
E_SHARED_DUAL_COLD: route_override=both, observer background, b2_control=shared_body_dual_state; expected both roles from same Body model and one Body FINAL. **Cold-start identity control only**, not proof of learned temporal-state divergence.
F_NATIVE_AUTO: route_override=auto, observer background, two_body; genuine C2/Needle C/FINAL invocation, ExecutiveControlContext source/event/session binding and native process reaping; actual selected route separately from mere invocation. No forced native authority, no scorer/route calibration changes.

All arms seed53, Age0 RECORD_ONLY, stage0, latents false, teacher off, jepa_weight=0, history_turns=0. No external tools/actions, no user data. Same pinned model files, revision and source hash checks. All heavy inference serialized under existing concurrency group; no overlapping native owners.

**Predeclared score:** each option earns one point only if its exact source budget-minus-option-cost remainder is explicitly and unambiguously claimed. Reuse frozen `semantic_diagnostic` lexical and `equation_diagnostic` explicit source-equation parser; accept CORRECT from one only when the other is CORRECT or MISSING, veto any WRONG/CONTRADICTORY/AMBIGUOUS/INVALID_OPERANDS on either. Never infer correctness from a bare cost echo, reversed equation or foreign option. Max 8 points per arm; invalid native/source/route/reaping row scores zero and is retained. Duration tradeoff and route selection are separate descriptive metrics, not part of this score.

**Exploratory pilot signal only**: all 24 rows valid, D_DISTINCT_BOTH >= max(A,B,C)+2 and D >= E+2. This tiny study is not an original STEP2 gate or statistically powered acceptance; no automatic gate promotion even if signal true. Report all raw outputs, source refs, event/session bindings, role/model, offer identities, process releases, native C2 invocation vs actual route selection, exact per-arm scores, timing, failures, negative gates. A missing Body path, unexpected fallback or non-reaped process invalidates its arm. Keep every failed attempt, never silently retry or substitute.

## Execution and acceptance

Implement new isolated runner and adversarial software tests without modifying existing frozen runtime, scorer, source, model, seed or fixture. Preflight software CI with source/prereg/Canon/catalog/tool Git blob checks, compile, privacy, diff, closed SHA256SUMS and raw artifact. Independent review before native. Native workflow after preflight, pinned bootstrap, same serial heavy group, bounded 24 calls, original raw closure and private byte-identical backup. A native RED remains RED; no synthetic-to-native inference.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; no Redmi; historical full-suite Run34/Run37 RED; whole-system incomplete. No device interaction, paid provisioning or approval escalation.

Next command after preflight: verify original software artifact SHA/CRC/SHA256SUMS and all adversarial tests; launch native only after confirming heavy owners released, then independently audit each raw row and backup. Do not change this prereg after source implementation.
