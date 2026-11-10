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
not pass; do not backfill it based on a later state. Ten new and six existing
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

## A1/A5: source-span offset and long-whitespace defects

`cognition.segments` and `episodes.text_segments` derive segment references
from local zero-based offsets even when their input `SourceRef` begins later in
the original source. Confirmed with real Store: source `Alpha Beta Gamma`,
span `Beta` at 6:10 yields legacy chunk text `Beta` but reference 0:4 reads
`Alph`. Current event call sites found so far use full sources beginning at 0;
impact on a current end-to-end turn has not been demonstrated. A separate
`episodes.text_segments` failure occurs for an overlong leading whitespace
unit, where `gist.group` returns zero groups and `pieces[-1]` raises IndexError.

New `v13/code/v13/percept_subspan_candidate.py` reads an actual Store SourceRef,
validates/tiles all segments exactly and maps local offsets back to absolute
Python character indices; long whitespace receives a labeled fixed-mode
source-exact fallback. `v13/code/tests/test_percept_subspan_candidate_20261110.py`
contains eight real-Store synthetic tests including Unicode, nested subspans,
source corruption/deletion, zero-offset compatibility and the original error.
The candidate is isolated and **not wired into the current runtime**. Reconcile
the callable contract with `cognition.percept`, `cognition.offer` and the
`runtime.py` PerceptPacket path after the frozen source cohort is released;
verify span tiling, provenance and default behavior before any integration.
No claim of grapheme-aware boundaries, native models or Android performance.

Combined local check, including existing A-plane and segmentation tests:

```sh
cd v13/code
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B -m unittest -v tests.test_aplane_gate_bound_candidate_20261110 tests.test_aplane tests.test_jepa_bounded_replay_ablation_20261110 tests.test_percept_subspan_candidate_20261110 tests.test_text_segments
```

28/28 PASS on Linux x86_64 with synthetic fixtures. Full captured output is
`v13/bench-results/research-percept-subspan-20261110/test-output.txt`.
A narrow GitHub workflow is included; its remote run must be checked at its
exact head before claiming CI success.

## Independent review and race fixes

Independent read-only review reproduced two candidate-specific races and two
evidence limitations. A3 feature verification used to hash a file and then
read it separately, permitting different bytes to be parsed. It now reads at
most 1 MiB + 1 once and hashes and parses exactly those bytes; a negative test
would have triggered the old hash/read swap. The A1 wrapper now snapshots the
input SourceRef and passes a separate copy to `read_source`, so mutation of
either the caller's dictionary or the Store argument cannot retarget output
spans; a test demonstrates both mutations during the read.

The A3 assessment now reports `unique_source_hashes` as an informational
measure. Fifty distinct events can still contain one repeated source; no new
mandatory diversity threshold was invented. The candidate checks each item
separately, not in a single consistent DB/filesystem snapshot: deletion or
checkpoint mutation between reads or between gate and use can stale its result.
Furthermore current feature payloads do not prove that the identified A3
model actually produced that source's features: 50 distinct events can point
at one feature blob. The future producer must bind trusted source/event,
feature, model and teacher provenance around inference; an independently
authenticated snapshot/lease must protect the actual routing decision and
source deletion. Caller-supplied fields alone are insufficient. **This
diagnostic `pass` remains non-authorizing and cannot be promoted yet.**

Earlier exact head `815d181e35adf3a350beb19c8ea6e491347b4868` had focused
GitHub Actions run 42832709062 GREEN (28 tests). The later local race-corrected
check passed 32/32; see
`v13/bench-results/research-percept-subspan-20261110/test-output-race-fixes.txt`.
The newer head needs its own GitHub Actions verification.

The independent review also showed that opening a FIFO as an A3 feature file
could block. The candidate now uses a nonblocking, no-follow descriptor where
those OS flags are available, validates the opened descriptor as a regular
file with `fstat`, and reads at most 1 MiB + 1. A subprocess test with a real
FIFO proves this fixture returns instead of hanging. This does not eliminate
parent-directory/path races, later file replacement, the initial checkpoint
hash/use race, or the lack of a transactional evidence snapshot. Initial test
harness attempts failed because Store expected a Path and then because the
parent held the Store's exclusive lock; the harness was corrected to pass a
Path and close/reopen the parent Store, after which 32 tests passed.
