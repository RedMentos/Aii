# Independent ToolForecast lifecycle recheck — 2026-10-16

Baseline: Claude M `1941d07afeb57299d7d5a466fd1eb44ec2569dfe`.
The actual newly integrated implementation was reviewed. The Oct13 isolated
candidate was not reused, and M's five fixes were not redone.

## Confirmed existing fixes

Independent positive controls cover ordinary bound restart and exactly-once
scoring; encoder/checkpoint replacement **before** observation; stale region
receipt rejection after an actual competence NPZ change; foreign raw-buffer
archival with original bytes intact; 66 predictions yielding exactly 64 matching
pending rows/context files; and failed state persistence preserving all 64 old
context files. Raw experience correctly remains reusable when only competence
changes: its taps depend on the encoder, whereas the adaptation receipt depends
on the region classifier.

The existing installer generation-switch test and six other focused M tests
also run unchanged. No live installer, native prefill, native compilation or
device action runs. Synthetic passing receipts used as loader fixtures are not
empirical learning/utility claims.

## One reproduced remaining source-change window

M explicitly documented that per-tap source snapshots were not adopted. The
review reproduced the concrete consequence: its initial observation guard
accepts tool A, but a different tool B can be installed at that same path during
the outcome prefill. The outcome is scored and appended to experience under A's
binding even though the stand-in encoder used B's actual file bytes.

The reproduction replaces actual owned temporary files plus `encoder.json` and
uses the real loader/checkpoint/StateBox/buffer/scoring paths; only native
inference is replaced with deterministic vectors. It is a software fault
injection, not evidence of an observed native/Redmi race or a new quality gate.

`baseline-toolforecast-1941d07.py` retains the exact reviewed source bytes.
`baseline-regression.txt` shows the regression failing against those bytes.
`reproduction-before.json` records `SCORED`, one experience row, and different
actual-outcome versus recorded encoder hashes.

## Narrow authorized production change

The coordinator assigned `v13/toolforecast.py` for this correction. `observe`
now snapshots encoder identity/file fingerprints and the actual small checkpoint
and competence hashes before the outcome tap. It re-resolves the encoder and
repeats the snapshot immediately afterward, before projection, scoring or an
experience append. Drift closes with `SOURCE_CHANGED_DURING_OBSERVE`; the normal
StateBox close removes its context only after the state write succeeds. A
changed checkpoint/competence source already present before tapping is also
refused. No mathematical fit, retention threshold, model selection, authority,
approval or tool-effect path is changed.

The encoder hash cache key now includes device, inode and ctime alongside path,
size and mtime. Normal replacement or a rewrite with restored mtime cannot reuse
a stale same-size cache entry. Unchanged large GGUFs retain cached hashes; the
fix does not hash the entire model on every binding check.

The corrected regression passes. Additional outcome-tap callbacks change private
checkpoint and competence files; both are discarded without scoring/experience.
An unchanged encoder still scores exactly once after restart. If state persistence
fails while closing the discarded forecast, the original pending record/context
survive and no new experience is appended. The existing best-effort telemetry
path can itself rethrow on persistence failure; that pre-existing behavior was
not expanded into this narrow change.

## Closed verification and limits

`run_review.py` verifies the retained baseline hash, runs the baseline failing
regression, runs 11 new plus 7 existing focused tests, and records both concrete
reproductions and all relevant source hashes. `report.json` contains actual
counts/timings; `SHA256SUMS.json` closes the proof files.

This is a bounded filesystem change detector, not an atomic read transaction or
a race-freedom guarantee. Current encoder records lack dynamic backend/library
hashes, so those changes are not covered. The added small-asset hashing/stat I/O
has not been measured on Redmi. The existing failed-prediction path may retain a
new uncommitted context file while preserving all old committed contexts. None
of this evidence promotes native quality, phone utility, STEP2 or B3 gates.

```bash
cd v13/code
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  python docs/proofs/continuation-20261016/toolforecast-review/run_review.py
```
