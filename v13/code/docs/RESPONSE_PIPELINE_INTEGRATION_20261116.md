# Connected response pipeline review — 2026-11-16

Release ancestor: `858d83c304bfcdf29455bf055ed740fbc24e016f`.
Review branch: `codex/v13-arithmetic-staged-integration-20261116`.
Related: full Canon #1984 and real-Redmi blocker #1904.

## Behavior and existing work reconciled

The arithmetic source parser from #1987/#1989 is retained, including its exact
`Fraction` calculation, two bounded signed integers and abstention on ambiguous
language or division by zero. The reviewed #1989 head is
`e465406d6e77509c70907d05e2ca98f2029118bc`. Its original failing CI remains
evidence: the Broker packet contract omitted the new authority, and direct
Runtime edits broke the existing frozen-source stage. This branch composes
the function after the established recovery layers; no original runtime,
source freeze, old cohort or model pin is rewritten.

The direct arithmetic path now produces a minimal source-bound A5 percept,
retains C1/JEF state, passes a distinct local C5 action, and writes a checked
`TEXT_REPORT` through C6/C7. It bypasses optional native perception and recall,
C2 control, B observers and C3 decoding for this narrow input class. It never
claims a model answer or a source copy. Approved exact rules retain precedence;
explicit copy requests retain their original behavior. Broker failure still
checks the computed output as `TEXT_REPORT`; pre-output failures use a genuine
system diagnostic. World timing/transition receipts distinguish deterministic
arithmetic from native roles.

Normal requests keep the B1/detail and B2/gist -> C4 -> C3 route. The sequential
observer scheduler reserves a share of the remaining pre-answer window for
each pending role. A B1 timeout that respects its allocated deadline can no
longer consume B2's entire slice. Parallel scheduling, peer exchange,
cancellation, re-entry and the total turn deadline retain their contracts.
Recovery from native C3 prefill failures requires genuine C3 token evidence;
deterministic arithmetic responses do not count as successful native decoding.

## Acceptance and proof limits

Canon mapping: W3–W6, IH-H12/IH-H13, C1/JEF, C4/C5, C6/C7 and sequential
observer scheduling §22.2.4. Tests execute the materialized stage with real
Runtime, SQLite, source refs, action/egress packets and restart. Native model
boundaries in these checks are explicit test drivers. No real phone, GGUF
inference, latency improvement, learning utility or latent communication is
proven by them.

Existing World training cohort role dimensions remain frozen. Arithmetic
timing and source-bound digital outcomes are supported; an arithmetic model
training cohort is not introduced or silently aliased to `SOURCE_COPY`.
Age 0 remains `RECORD_ONLY`; STEP2 `UTILITY_FAIL`, B3 failures, all source
rights and both false whole-system completion flags remain unchanged.

Validation on the final composed local sources (Python 3.12.14):

- Shared stage/runtime suite: **105 passed, 9 intentional skips, 29 subtests**.
- Same-stage organ/memory/JEPA/LoRA regression: **415 passed, 3 CUDA skips,
  58 subtests**; the outer wrapper also passed.
- New arithmetic + existing broker/fixed-policy cases: **42 passed,
  37 subtests** inside the shared stage; observer wrapper **2 passed** with
  six disposable cases, including real Cognition quote parsing/storage.
- Recovery shell syntax and Git whitespace checks pass. Independent source
  review found no remaining blocking code defect in the scoped changes.
- The earlier attempt recorded 19 failures at the new World dependency pin.
  The final layer rebinds only the exact reviewed World, semantic-evidence
  and local-error sources; the corruption counterexample still rejects.
- A prior 160-turn fixture had one wait-time failure during dependency setup;
  its isolated retry and the final shared/integrated runs passed. Failed
  attempts remain in the session logs and are not reclassified as passes.

CI checks out the explicit PR head SHA. Remote results must be read on
[PR #1990](https://github.com/RedMentos/Aii/pull/1990). The separate
`safe additive` workflow correctly rejects this package as `not a strictly
additive PR`: it changes the existing stage and needs Boss/Integration review.
That automatic integration restriction has not been weakened.

Reproduce from `v13/code` with the pinned CI dependencies:

```sh
python -m pytest -q -s tests/test_arithmetic_stage_20261116.py tests/test_observer_fair_budget_stage_20261116.py
python -m pytest -q -s tests/test_staged_integrated_regression_20261111.py
```

## Release and next owner

Status: review candidate, NOT_RELEASED, REDMI_UNVERIFIED. Boss/Integration must
review the final composed source and exact-commit CI before the fixed phone
release train can install it. This package reconciles the arithmetic and
sequential-budget candidates; it does not close the full-Canon or Redmi epic.
Next measured gate: 20+ diverse real Redmi turns, first-token/total latency,
correct visible answers, valid B1/B2 offers actually consumed by C4/C3,
verified installed SHA and PSS/RSS. A native runner that ignores its deadline
can still overrun a reserved slice and needs separate device evidence.
