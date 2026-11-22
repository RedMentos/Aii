# STEP2 error analysis — frozen native cohort, 2026-10-11

Final cohort snapshot: 2026-10-11T04:03:47.150472+00:00; report SHA256 `e32e18d50f590b35aef3c1dcd766ed1f06f4f96a143bf675b088d1b9b2b1b555`; status `UTILITY_FAIL`; completed rows **70/70**. All structural checks pass; frozen source and installed artifact bindings remain unchanged. The preregistered semantic gate fails. Neither runtime nor scorer was changed for this analysis.

## What the completed rows show

| Variant | Rows | Mean strict field utility | Exact decisions | Structural failures |
|---|---:|---:|---:|---:|
| b1_only | 10 | 0.508333 | 0 | 0 |
| b2_only | 10 | 0.166667 | 0 | 0 |
| both_none | 10 | 0.508333 | 0 | 0 |
| both_exact | 10 | 0.500000 | 0 | 0 |
| both_control | 10 | 0.500000 | 0 | 0 |
| same_policy_dual | 10 | 0.558333 | 0 | 0 |
| prompt_only_dual | 10 | 0.258333 | 0 | 0 |

The unchanged paired scorer reports primary `both_exact`=.5 versus best solo B1=.508333 and same-policy dual=.558333. Combination gain over best solo is -.008333. All70 native responses use action `NONE`; all70 are syntactically valid JSON, but22 contain invalid entity mappings under the original scorer. No answer is an exact decision. `RECORDED` means real FINAL inference and structural checks completed, not semantic correctness.

The independent source-transport analyzer reproduces all70 recorded scores exactly. Earlier source is available but not quoted in40/70 rows; actual quote transport from producer-selected evidence to C3 matches in70/70. Thus the loss is upstream of the selected-quote handoff, rather than a mismatch between those selected quotes and native input. Of28 current-override rows,21 permit field scoring and **all21** contain action/remaining/eligibility errors;7 are schema-invalid. The other42 rows are inapplicable to that specific override metric.

Of42 retained-rule rows,27 have a valid field structure and bound current source; all27 emit asserted rule-dependent values without any verified earlier-source quote. The remaining15 are schema-invalid. This diagnostic does not infer that any prior quote would cover all required rules. In Juno, the source explicitly lacks a budget: C3 still emits NONE and non-null residuals/eligibilities, which is an additional direct missing-data failure.

Native metrics report70/70 C3 FINAL and120/120 producer FINAL calls for recorded variants, excluding preparation calls. Maximum recorded per-call sampled native RSS is1,365,266,432 bytes. The analyzer preserves separate unavailable and inapplicable denominators; this is cold sequential Linux process evidence, not sustained target-phone memory or thermal proof.

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

1. The complete70-row fixed comparison is preserved and the existing paired scorer has been independently reproduced; retain its `UTILITY_FAIL` as the baseline for separately frozen changes.
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

## Executable offline diagnostics and next isolated probe

Run `python3 scripts/analyze_source_transport.py docs/proofs/continuation-20261011/step2-webchat-70/report.json --out <analysis.json>`. The standalone script requires actual recorded source text to check SHA256, exact spans, producer quote declaration, provenance containment, focal-offer ordering and actual C3 message content. Missing source/native metrics remain unavailable; it never calls a model or imports an oracle into production. Current-rule errors reuse `v13.utility.score_decision`; optional task assertions reuse the existing STEP2 analyzer. Sixteen focused new boundary tests plus sixteen existing scorer/analyzer regressions pass (32 total), log `source-transport-tests.log`.

`step2-source-transport.json` records this final cohort; `step2-historical-source-transport.json` separately analyzes the recovered previous70-row cohort and reproduces its original paired verdict and all70 scores. Its actions are65×A and5×UNKNOWN, demonstrating that the older receiver also has a constrained action pattern; it is not a demonstrated correct enum control.

A separate read-only source audit found that `common.dumps(sort_keys=True)` sorts the wire schema and that native grammar preserves that property order. Action is emitted before option calculations; within an option, eligibility precedes entity/locality/remaining. This is a plausible tiny-receiver decoding handicap, **not a causal conclusion from the cohort**. The separate `scripts/schema_action_probe.py` compares free, action-only, action-first and facts-first forms on generic cases after this baseline finished. Its later measurements must keep their own source/model/config bindings and cannot rewrite or promote the preserved STEP2 result.
