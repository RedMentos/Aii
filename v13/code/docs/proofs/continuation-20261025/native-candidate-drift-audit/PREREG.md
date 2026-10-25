# Native-firing candidate vs integrated live source drift — prereg (2026-10-25)

Base: PR255 exact full-suite CI head `0c8dbb233a4541edb4049e5fa19deac91190f8a7`. Exclusive ownership: new read-only diagnostic script, new tests, new CI workflow and this proof folder. No changes to `integrated_candidates.py`, historical snapshots, `native_firing_runtime_candidate.py`, Runtime, live runner, models, registered cohorts, Age, WorldModel, LP3 or any active owner.

Problem: Run221 full suite had 36 errors from `ValueError('Live sources differ from complete baseline/candidate')` in `native_firing_runtime_candidate.sources` and merged tests. The integrated chain `integrated_candidates.overlay` accepts live source only when byte-equal to a frozen historical composition. Later reviewed changes may have legitimately diverged, but this must be established byte-exactly, not guessed or bypassed.

Preregistered diagnostic:
1. Compute `integrated_candidates.integrated_sources(root)` from pinned historical baseline without modifying source.
2. Read the current live four files (runners.py, memory_server.py, runtime.py, store.py), calculate SHA256 of expected/live, count differing lines and preserve a complete unified diff artifact.
3. Assert audit code detects a deliberately mismatched synthetic pair; no hidden success if drift exists. `candidate_gate=FAIL_SOURCE_DRIFT` until an independently reviewed source-bound rebase.
4. Do not change frozen manifests or automatically rebind candidate. No native execution, model download, learned authority, source omission, or gate promotion.
5. Save full raw diff, manifest and source hashes in GitHub Actions artifact, with official privacy scan. CI diagnostic success means correct detection only, NOT native candidate PASS.

Follow-up after exact diff: determine whether current live modifications can be composed as reviewed transforms without losing new functionality; preregister a separate candidate update and full ablations. Original 36 ERROR evidence retained.
