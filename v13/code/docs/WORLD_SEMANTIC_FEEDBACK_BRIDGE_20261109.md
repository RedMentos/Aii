# User feedback ↔ world action bridge — 2026-11-09

Status: **source-bound, read-only candidate; no runtime hook or model update**.
This is a child of AG4 fact-precedence PR
[#1629](https://github.com/RedMentos/Aii/pull/1629), exact source
`3c7b88ebe3e760e56179af71141222f8a4316dd7`. It can be composed in a disposable
copy with the separate online-world review candidate
[#1631](https://github.com/RedMentos/Aii/pull/1631), source
`4dd70336d408384c16fe9d5856a12d3cab152107`. Neither parent branch is changed.

## What the bridge does

`world_semantic_evidence_candidate.snapshot` identifies **one current T8
action** for a real stored event and binds it to its authoritative input,
unique FINAL answer, live context, committed C5 selection and active F5/F1
feedback sources. It returns the action ID, route, technical completion and a
fingerprint, without returning raw user/answer/correction text. Explicit user
quality ratings and user-supplied fact feedback are separate fields. An implicit
chat rating is not turned into an explicit rating; FINAL is not factual
correctness; absence of a correction is not a positive truth label. A factual
feedback item is evidence of what the user supplied, not proof that the prior
answer was factually wrong.

Active corrections retain `record` versus `learn` permission. Even `learn`
does **not** grant this candidate weight-update or decision authority; the
snapshot reports both as zero. Ambiguous, missing, altered or revoked source
lineage is rejected. Strict JSON admission rejects duplicate keys. The
fingerprint also covers source/permission/answer/selection/decision changes,
and `still_current` rebuilds the snapshot before a later consumer can use it.
The candidate checks exact hashes of its relevant source dependencies; accepted
`inputs.py` hashes cover the #1629 base and its exact candidate overlay.

`world_semantic_online_composition_candidate.build_sources` independently
checks the #1629 and #1631 source inputs and returns an overlay for a throwaway
tree. It preserves both candidates' operator changes and does not overwrite a
live source. The resulting real Runtime/SQLite test shows the technical
predictor's receipt and a source-bound user fact/rating refer to the **same
action**. The correction remains a separate observation; it is not yet
consumed by the predictor's gradients.

## Verification

* `PYTHONPATH=.:tests:scripts ... -m pytest -q tests/test_world_semantic_evidence_candidate_20261109.py tests/test_c5_feedback_shadow_store_candidate.py tests/test_c5_feedback_ledger_candidate.py tests/test_skill_parity_shadow_integration_20261108.py tests/test_ag4_fact_precedence_integration_20261108.py`: **54 passed, 7 subtests passed**.
* `V13_ONLINE_CANDIDATE_CODE=<PR-1631>/v13/code PYTHONPATH=.:tests:scripts ... -m pytest -q tests/test_world_semantic_evidence_candidate_20261109.py tests/test_world_semantic_online_composition_20261109.py`: **11 passed**; the nested disposable copy ran **41 passed** (30 online, 10 semantic, 1 joint Runtime/SQLite probe). Tests use real Runtime and SQLite but a synthetic C3 response seam; this is not native language-model evidence.

## Still required

There is no semantic-error gradient or automatic training from these
observations. Ratings measure user satisfaction and cannot by themselves label
factual truth; corrections may be new information. Any future training data
must honor the individual learning permission, distinguish those signals,
handle later revocation/correction through invalidation or a verifiable
rebuild, and keep evaluation data separate from training. `still_current` is
a point-in-time check and is not atomic with a future checkpoint commit.
Evaluate benefit and forgetting on fresh, consented examples before enabling
anything. No pretrained GGUF edit, native/Redmi measurement, STEP2/B3/JEPA
promotion or whole-project completion is claimed.
