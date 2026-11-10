# Research & Perception handoff — 2026-11-10

**Owner:** A0–A5 / research; integration review branch
`research-perception/jepa-replay-ablation-20261110-1457`, draft PR #1687,
based on #1683 (`abfd31a2651b418e1ef3f9a10bf089983d299984`). The separate
JEPA agent's latest cursor validation #1685 is not in this branch. Do not
blindly merge either branch or alter the frozen SourceHandoff sources. The
pre-research parent and exact remote state must be rechecked at the next run.

## Completed: research and reproducible A→B→A run

Committed preregistration `94813d7a361fb64f8b71e179bf80c15a11d5cec3`
before the experiment, and research runner/results at `db2c137c3a1fe3cfff91d52e1b4e1d050a64fec2`.
The original three-seed paired control and its primary research sources,
limits, complete JSON, SHA-256 and independent review caveats are in
`v13/bench-results/research-jepa-replay-20261110/README.md`. Four local
stdlib tests pass. This shows real NumPy updates on synthetic data only, no
JEPA-TTT replication, no E2E V13 utility and no Android measurement. Do not
promote any existing gate. The replay-buffer memory figure is nominal payload,
not RSS. Independent reviewer found action-imbalance confounding in replay
subsamples; preserve raw results, use stratified sampling and new holdouts in
any next preregistered run.

## A3: confirmed student-gate defects and isolated candidate

`v13/code/v13/aplane.py:student_gate` currently counts the newest evaluation
packets, including repeated evaluations of one event and evaluations from old
brain generations. Real temporary Store/SQLite reproduction: 50 evaluations
of a single event pass the existing gate; 50 old-generation matching
observations also remain passing after A3 checkpoint rotation. The bad gate is
used by `set_student_mode` and by `student_fallback`; that is a real code-path
risk, not proof of on-device exploitation. A3 still only routes when the
separate explicit fallback mode and other preconditions hold.

`v13/code/v13/aplane_gate_bound_candidate.py` and
`v13/code/tests/test_aplane_gate_bound_candidate_20261110.py` implement and
exercise an isolated evidence-only assessment: latest evaluation per event,
current generation, artifact checksum and route/A3/C2 snapshot identity,
source and feature checks, plus retention and generation-drift negative
controls. Legacy records do not include `candidate_model_binding`, so they do
not pass; do not backfill it based on a later state. Seven new and six existing
A-plane tests pass using real local SQLite and synthetic checkpoints. The
candidate does not change runtime, mode, authorization or shadow recording.

**Remaining integration:** the current producer in
`learning.py:compare_student_route` must capture model/teacher identities
around actual inference, and the existing user fallback approval must be
bound to that same snapshot. `aplane.student_fallback` needs an atomic or
otherwise proven generation/identity check through decision *and use*; the
candidate's terminal check alone cannot close a concurrent promotion race.
Review the actual active-registry representation and actual source feature
format before wiring. Ensure legitimate fresh evidence can accumulate without
blocking ordinary shadow learning. Pin a replacement cohort and independently
review SourceHandoff freeze rules before changing its runtime code. Until then,
**the existing gate remains unfixed** and the candidate must not be called a
production remedy.

Focused verification:

```sh
cd v13/code
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest -v tests.test_aplane_gate_bound_candidate_20261110 tests.test_aplane
OPENBLAS_NUM_THREADS=1 PYTHONPATH=. python -m unittest -v tests.test_jepa_bounded_replay_ablation_20261110
```

Full repository tests, native C2/A3 inference, mobile memory, thermal and
latency remain unverified. `pytest` was absent from this environment. STEP2,
B3 and other canonical negative gates remain unchanged.
