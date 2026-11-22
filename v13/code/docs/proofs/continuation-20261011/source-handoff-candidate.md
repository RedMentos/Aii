# Source handoff candidate — isolated during the frozen STEP2 cohort

This candidate repairs an explicit source-transport boundary and disambiguates
own action state. It does not claim native-model semantic improvement. The
original 70-case report, fixture, scorer and runtime remain unchanged while that
cohort is running. The current candidate has no model calls in its validation.

## Observed defect and scope

The Aurora B2 offer has a valid prior source containing earlier constraints but
quotes only current source text. Its summary treats `NO_OBSERVATIONS` as global
absence of facts. C3 therefore receives no quoted earlier rules. The existing
quote validator already permits exact quotations from retained source excerpts;
the defect is not an inability to verify those spans. `world.mode` describes own
digital action outcomes, not knowledge available in supplied text. The current
utility report also contains independent C3 arithmetic/entity errors; this patch
does not solve them by replacing native answers with computed expected values.

The runtime answer path additionally serializes only each raw `offer` object.
That object includes both accepted and rejected model-proposed quotations,
without conveying their validation distinction. The candidate renders selected
offers as fallible hypotheses with separate source-verified quotation records.
The existing STEP2 fixture already makes this distinction explicitly. No
complete retained source is injected into its consumer by this candidate.

## Implementation

* `bodyview.py`: own-world state gains the narrow
  `OWN_DIGITAL_ACTION_OUTCOMES_ONLY` scope. Its empty state is rendered as
  `NO_COMPLETED_OWN_DIGITAL_ACTIONS`. Durable world state and measured action
  accounting stay unchanged.
* `cognition.py`: source-reading instructions explicitly distinguish action
  history/tool-execution permissions from reading supplied source constraints.
  Relevant earlier rules should be quoted exactly; explicit current revisions
  take precedence. Missing required evidence remains unresolved uncertainty.
* `Cognition.analyst_context`: stored offer/query equality, current turn,
  generation, state version, model revision, quote/source scope, exact string
  equality and source hash are rechecked at consumption. Only actual
  `evidence_refs` are delivered. Source existence or a broad provenance entry
  alone does not authorize a new quotation. Invalid/deleted/tampered evidence
  fails closed.
* `runtime.py`: the HYPOTHESES layer uses that rendering, with rejected raw
  quotes omitted. Exact quotation spans also enter durable output lineage.

Every delivered quote includes its stable source identifier, full source digest
and character span, together with `EXACT_SOURCE_SUBSTRING_ONLY` and
`semantic_truth_authority=false`. This proves exact text delivery, not a true
world fact or a correct analyst inference. Learned authority, native B3 latent
rights, receiver activation and source admission are unchanged. B1's short
window, B2 retained context capacity and all existing ablation exclusions remain
unchanged.

## Validation and application

`scripts/source_handoff_candidate.py` constructs the three-file patch from a
digest-bound frozen baseline. Its loader accepts only the complete exact
baseline or the complete reviewed candidate. Mixed source states, changed
baseline snapshots and unrelated runtime edits are rejected rather than
silently falling back. The snapshot is in `source-handoff-baseline/` beside this
file, including a digest manifest.

The focused run passes 28 tests: 11 new candidate regressions, 8 ablation
lifecycle/transport regressions and 9 existing body-state/view tests. The new
cases use real SQLite events, persisted Query/
Offer packets and real source blobs with stubbed inference, including prior
quote transport, missing evidence, rejected/own-state quotations, mutable
packets, wrong turn/version/model, query scope changes, unrelated sources,
deleted/corrupt blobs, state-off behavior and complete/mixed patch states.
`git apply --check` succeeds. See `source-handoff-candidate-tests.log`.

After the 70-case process ends and its complete report and source binding are
preserved, apply `source-handoff-candidate.patch` atomically from the code root.
Rerun the focused suite against the integrated sources, then the normal package
suite. The candidate's strict source guard remains runnable after this exact
application. Further unrelated changes need an explicit new candidate revision
or migration of the regression tests to the permanent integrated API; they must
not be hidden behind a permissive snapshot fallback.

Before claiming a producer repair, conduct a separate source-disjoint native
ablation with cold starts and fixed deadlines: original state/instructions;
state disabled; explicit own-action state semantics alone; complete candidate.
Record which exact retained spans were available to B2, which were offered,
which were verified, and which were actually supplied to C3. Never fill absent
offers with the full prior. Preserve every native failure and zero score. This
ablation diagnoses transport and own-state contamination; full STEP2 quality,
native complementarity, body training and target-phone thermal performance
remain separate open gates.

## Ready-to-run separate native ablation

`scripts/source_handoff_ablation.py` freezes four new named cases (Mira, Lumen,
Nacre, Tessera) and four arms, for 16 current decisions. They cover retained
rules, explicit current overrides, missing rules and an intentionally corrupted
prior blob. The corrupt source must be excluded, never silently repaired or
copied into C3. Every arm makes a genuine prior B2 call, a cold current B2 call,
and a cold C3 call. All arms use the identical verified-quote consumer boundary;
this experiment isolates producer-state/source-instruction effects rather than
confounding them with differing C3 serialization. The runtime transport patch
is checked independently by the store regressions.

The runner rejects a still-running or incomplete original STEP2 report. It
records inputs, oracle, consumer schema, system prompt, exact per-arm code,
runtime/script/baseline hashes, model revisions and model/launcher/shared-library
digests before inference. Sampling is fixed at seed13 and temperature0, with
two CPU threads, an observer45-second budget and a current turn120-second
budget. There is no history, active memory injection, teacher or learning
update. All source rules and expected results stay distinct: only current text
and actually selected verified quotes reach native C3.

After integration and the original 70-row completion, first run the registration
only command and preserve its preregistration JSON in the GitHub checkpoint:

```bash
python3 scripts/source_handoff_ablation.py \
  --installed-home /workspace/scratch/5a9214d3f329/native-audit-cache \
  --step2-report docs/proofs/continuation-20261011/step2-webchat-70/report.json \
  --out docs/proofs/continuation-20261011/source-handoff-ablation/report.json \
  --register-only
```

Run the same command without `--register-only` to infer. Each completed/error
row is atomically checkpointed with a content digest. Resume is automatic only
under the exact preregistration/native/source binding and unmodified recorded
row hashes; failed rows remain scored zero. Interrupted completed rows are
retained, not retried into successes. Artifact changes stop the cohort with
`ARTIFACT_CHANGED`. Work directories end in `.checkpoint` and must not be
published as live SQLite state. The final report remains a small diagnostic
cohort with `canonical_gate_pass=false`, even if every decision is exact.
