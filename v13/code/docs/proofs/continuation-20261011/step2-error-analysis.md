# STEP2 error analysis — frozen native cohort, 2026-10-11

Snapshot: 2026-10-11T03:51:00.817440+00:00; report SHA256 `baa9bfb3d661e5fa8c36ccacd0d0c1e8544dc66a5f5a6a3748d260433863895b`; status `RUNNING`; completed rows **20/70**. This is an interim analysis, not the final paired utility verdict. Neither the frozen runtime nor the scorer has been changed for this analysis.

## What the completed rows show

| Variant | Rows | Mean strict field utility | Exact decisions | Structural failures |
|---|---:|---:|---:|---:|
| b1_only | 3 | 0.388889 | 0 | 0 |
| b2_only | 3 | 0.222222 | 0 | 0 |
| both_none | 3 | 0.388889 | 0 | 0 |
| both_exact | 3 | 0.361111 | 0 | 0 |
| both_control | 3 | 0.388889 | 0 | 0 |
| same_policy_dual | 3 | 0.416667 | 0 | 0 |
| prompt_only_dual | 2 | 0.333333 | 0 | 0 |

These prefix means must not be compared as the final gate while variants cover different fixture counts. `RECORDED` means the structural checks and real FINAL call completed; it does not mean a semantically correct decision. All completed rows remain in the proof, including malformed duplicate entities.

## Producer failure: available earlier source is not offered as decision evidence

Aurora / `b2_only` has a validated earlier source in B2's bounded context: `Project Aurora. Budget 100 euros. Deadline 5 days. Local-only requirement: true.` The offer records a prior `context_source_ref`, and `source_evidence` can read that exact source. B2's actual offer instead says:

```json
{
  "needs_reentry": true,
  "quotes": [
    "Project Aurora.",
    "local false"
  ],
  "summary": "The system is in NO_OBSERVATIONS mode with no prior facts or external tools available to solve the constraint 'Local'.",
  "uncertainty": "High uncertainty regarding the feasibility"
}
```

Its `evidence_refs` verify only `Project Aurora.` and `local false` in the current source. The actual C3 user message includes current source plus those verified quotes; it does **not** include the earlier budget/deadline/local-only source. The report-level `source_evidence` is an audit inventory, not the native consumer input. This difference is deliberate in the frozen preregistered fixture: bodies must contribute prior rules through their offers; copying the oracle or whole earlier source directly into the proof consumer would change the experiment.

Therefore this row does not prove that C3 ignored a supplied budget of 100. It proves that B2 had the retained source, did not produce the relevant source-bound evidence, and C3 subsequently invented a decision despite unavailable rules. Source validation/persistence succeeds; semantic retention/offer selection fails. B1's lack of prior after the intervening Zenith distractor is consistent with its registered one-offer short-window policy; expanding B1 memory would change that control.

## Likely producer contamination: own-action state is read as global ignorance or prohibition

B2 already emits the `NO_OBSERVATIONS` story on the original Aurora prior, where the raw source explicitly supplies all three rules. It later says the Cygnus local-only requirement is "explicitly forbidden by the system rules" although that is a source constraint, not a prohibition. These are unsupported hypotheses; their uncalibrated confidence remains zero.

The identifier comes from `v13/bodyview.py::body_state`: `world.mode` defaults to `NO_OBSERVATIONS`, meaning no world/action observations in that component. `v13/world.py::world_state` uses the same default. Cognition puts this own-state view in the model query as `body_state`, with `authority=STATE_NOT_FACT` and an instruction that it is not a fact. B2 repeatedly broadens it to "no prior facts or external tools". This is a strong implementation hypothesis for a future preregistered body-state on/off ablation, **not yet a proven causal mechanism**. Turning off all body state as a scored-run repair, or marking it solved from this correlation, would be unjustified.

## Consumer failures: missing-rule abstention and entity/calculation binding

Aurora / `b2_only`: C3 receives no budget/deadline rules. Its explicit system instruction requires `UNKNOWN` and null `remaining`/`eligible` when a required earlier rule is missing. The actual result says `NONE`, uses residuals 30/20, and asserts eligibilities. It also chooses no option while marking A eligible. This is consumer noncompliance in addition to the upstream producer omission; the actual oracle remains A with residuals 60/30, so utility remains 8/12, not a successful answer.

Borealis / `both_exact`: C3's current source clearly assigns cost55/days5/localtrue to A and cost65/days3/localtrue to B. The raw answer labels both objects B, invents residuals10/5, and reverses eligibility. Its earlier rules are also absent from verified offer evidence, but duplicate entity identity is an independent failure on information explicitly present in C3's current source:

```json
{
  "action": "NONE",
  "options": [
    {
      "cost": 55,
      "days": 5,
      "eligible": true,
      "entity": "B",
      "local": true,
      "remaining": 10
    },
    {
      "cost": 65,
      "days": 3,
      "eligible": false,
      "entity": "B",
      "local": true,
      "remaining": 5
    }
  ],
  "project": "Project Borealis"
}
```

The original scorer correctly records `invalid:duplicate/invalid entity` and utility0. No entity normalization, project-name cleanup, handcrafted arithmetic replacement, or post-hoc gate weakening is appropriate. A syntactically valid native JSON result is not a semantically valid entity mapping.

Cygnus / `b1_only` is an independent available-evidence consumer case: the **current_source itself** explicitly overrides prior rules to budget75/deadline6/local-onlytrue. C3 returns residual75 for both options, eligibilitytrue for cost80 and eligibilityfalse for cost60, and actionNONE. This cannot be explained only by absent earlier source; the current rules are already supplied to C3. Actual expected residuals are -5/15 and actionB.

```json
{
  "action": "NONE",
  "options": [
    {
      "cost": 80,
      "days": 2,
      "eligible": true,
      "entity": "A",
      "local": true,
      "remaining": 75
    },
    {
      "cost": 60,
      "days": 4,
      "eligible": false,
      "entity": "B",
      "local": true,
      "remaining": 75
    }
  ],
  "project": "Project Cygnus"
}
```

## Native firing proof remains execution evidence

`native-firing-smoke-library-bound/report.json` has `PASS_EXECUTION_ONLY`, three request-bound audit observations and six passing checks. Only the nonzero unguarded synthetic row fires; the impossible entity row is blocked; the zero-valued row produces no writes. Audit-off/on answers and prompt counts are identical. This establishes actual numerical write instrumentation and guard operation for the bound launcher/shared libraries/model, not learned recall, semantic quality, utility or activation authority. `memory_origin=SYNTHETIC_PROTOCOL_FIXTURE`, `learned_recall_proven=false`, `activation_authorized=false`, and `phone_measured=false` remain correct.

`native-vertical-summary.json` separately reports real completed body/C3/Needle execution with all audit checks but wrong Blue remaining budgets (required10; emitted30 or110). Structural PASS already coexists with semantic failure. This older proof has a different runner/source binding and must not be merged into the current STEP2 cohort as a quality pass.

## Next implementation work justified by this evidence

1. Finish and preserve all70 fixed variants first, then compute the existing paired comparison. No early subset is the gate.
2. Add evidence-transport diagnostics that distinguish a source merely available to a producer from a quote actually delivered to its consumer. Preserve explicit source IDs/hashes/spans and flag unsupported hypotheses without copying the expected answer.
3. After the frozen run, measure a separate body-state on/off ablation on distinct inputs; make own world/action state semantically explicit if measured evidence supports the change. Keep uncertainty and provenance separate from fact authority.
4. Measure C3 calculation/entity binding and missing-rule abstention separately from body complementarity using real native outputs and source-disjoint cases. Improving an offer cannot by itself fix the demonstrated current-source calculation errors.
5. Keep native Sparse-body/B3 trained utility, genuine labelled training, and sustained target-Redmi resource/thermal measurements open. No software-only diagnostic promotes these capabilities.

## Plan consistency

`specs/component-contracts.json` keeps B1 sparse expert training unavailable, B2 semantic complementarity unproven and native B3 latent authority zero. `docs/REMAINING_IMPLEMENTATION.md` explicitly says its old 2026-09-29 table is stale, and directs current status to project `ROADMAP.md` / `ABDECKUNG.md`; its later 2026-10-09 continuation already reports a prior70-row UTILITY_FAIL. This new run is a fresh source/library-bound cohort, not a reset that erases that failure. Current Drive plans must be reconciled separately by the plan audit before proposing a wider architecture change.

## Historical cohort comparison limits

The recovered `v13/bench-results/step2-two-body-20261009/step2_utility.json` is a complete70/70 `UTILITY_FAIL` with the same fixture hash and variant specification. Its mean utilities are B1=.5, B2=.0916667, `both_exact`=.3416667; B1 remained stronger. Historical Aurora `both_none` scored11/12 and its B2 summary explicitly included budget100/deadline5. The present producer instead emits the unsupported NO_OBSERVATIONS interpretation.

This is not an isolated before/after regression experiment. Historical C3 model SHA was `e75f83268de11b2a1bcfab5f3b5c5c0c97569ddbbc0990aad88437e45b8ba292` / revision `cdf97bd8205908758f44aec508d68ac1aef98f5c` (230M); current C3 SHA is `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` (350M). Runtime source, native runner/library binding and configuration also changed. Do not attribute aggregate utility differences to C3 size, own-state injection or one prompt change without a separately frozen ablation. The present direct harness call supplies no `first_token_bias` and logs no active output-adapter-first-step metric, so these specific current structured-output failures are not evidence of an active learned C3 output delta.

The project-name field often contains `Project Aurora` rather than bare `Aurora`. The frozen schema declares only a string, without an explicit bare-name description; this accounts for one strict field failure, and cannot explain wrong budget arithmetic, duplicate entities or unsupported certainty. A later separately measured schema-description improvement is possible. Post-hoc normalization in this cohort remains inappropriate.
