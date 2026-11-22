# Per-event local-error and route-worker preview — 2026-11-09

Status: **source-bound SHADOW diagnostic candidate**, child of
[#1632](https://github.com/RedMentos/Aii/pull/1632) at
`2c6cdcf7f75f19c6a7626a095d685512047331a3`. No runtime hook, optimizer step,
checkpoint, native model weight update or decision authority is added.
Research mapping for the user's weight-space/error-learning idea is recorded
in [#1602](https://github.com/RedMentos/Aii/pull/1602).

## Why event binding matters

The existing `Neuromod.local_update` is not used by the route optimizer. It
defaults to the **last** mapped path delta. In a real Store counterexample, a
later route trace without a matching outcome still returned the prior event's
nonzero delta. A second counterexample used the exact F4 route-learning packet
shape in `learning.py`: it contains `task_success=0` while `values_status`
explicitly says task success is **not an optimizer reward**. The existing N10
legacy mapping nevertheless treated that placeholder as an outcome and
produced `delta=-0.5` and a negative local scale. These are risks for a future
connection, not a claim that today's worker already applies those values.

## Candidate

`local_error_route_shadow_candidate.preview` joins the real T8 action and
source-checked answer to **one active explicit F5 route correction** with
`permission='learn'`, an event-bound LearningTrace and a unique, typed N10
human-correction outcome whose source references include the original input and
the route label. Its binary outcome must equal the observed-versus-requested
route comparison. A placeholder, ambiguous signal, old event delta, changed or
revoked source, record-only label, active N10 mode or disagreeing outcome is
rejected or reported unavailable. It rechecks evidence after reading N10;
N10 synchronization can update its own derived diagnostic state, but there is
no optimizer or checkpoint mutation.

For valid evidence, the candidate calls the existing `learning_worker`
cross-entropy objective on the **corrected** route, computes its gradient, and
reports a hypothetical gradient norm weighted by the nonnegative magnitude of
the event's local N10 scale. A negative scale is not used as a negative loss
or to imitate the observed wrong route. This is a bounded preview: the caller
supplies an unverified embedding, and the preview uses a zero-initialized
readout rather than the active checkpoint. Route agreement is an operator
label, not factual answer correctness. No producer is automatically wired to
emit the newly required typed packet.

## Verification and next work

`PYTHONPATH=.:tests:scripts /tmp/v13-online-review-venv/bin/python -m pytest -q tests/test_local_error_route_shadow_candidate_20261109.py tests/test_local_updates.py tests/test_neuromod.py tests/test_learning_worker.py tests/test_world_semantic_evidence_candidate_20261109.py`: **42 passed**. Tests use actual Runtime/SQLite and the actual NumPy objective, with synthetic C3 output and embeddings; they cover both counterexamples, source revocation, permission, duplicate signals, active-mode rejection and source-hash mismatch.

An actual training experiment still needs genuine source-bound encoder output,
explicit activation/Age and data-use gates, a source-revocation-safe checkpoint
protocol, a separately preregistered equal-budget correction-only baseline and
shuffled-error control, fresh held-out tasks, retention and performance checks.
The preview's cross-process evidence check is not atomic with a future update.
No native/Redmi result or STEP2/B3/JEPA/age promotion is inferred.

Parallel update: #1634–#1639 extend Body-JEPA device placement, bounded anchor
cache, EMA swap, finite-gradient validation and staged EMA target updates.
Their combined focused run on exact #1639 source reported **45 passed, 3 CUDA
skipped** here; privacy scan CLEAN. Subsequent independent counterexamples
found that an injected second EMA copy failure can still partially change an
earlier shadow tensor, and a nonfinite optimizer moment can poison parameters
despite finite gradients. Those Body-JEPA fixes are a separate review package;
no source from the other branch is silently replaced.
