# Run338 preregistration — exact-head current integration full Python suite

2026-10-25 UTC. Owner: isolated Run338 CI workflow/proof only, based on Run337 PR #333 exact head `e7e7199353f3298f5eac139e503380e03afb1ae4` (Run336 PR #332 and Run334 PR #331 underneath). This is **not** a production merge and cannot establish native/Redmi learning.

## Gap

Run336 exercises C3 pinned native training and focused source tests; Run337 has 12 adversarial raw ZIP tests. The complete current integration branch Python suite has not yet been run on this exact newer chain. Earlier Run113/173/176 full-suite workflows bind older snapshots and/or extra historical LP3 fixtures; their results cannot be silently inherited.

## Predeclared test

Add a separate `run338-fullsuite-source-proof.yml` that checks out **exact PR head SHA**, installs isolated pinned CPU-only `numpy==2.3.5`, `prompt-toolkit==3.0.52`, `torch==2.9.1+cpu` from the official PyTorch CPU index, sets model downloads/telemetry OFF, compiles `v13` and `tests`, and runs `python -m unittest discover -s tests -p 'test_*.py' -v` under a bounded timeout. Preserve raw stdout/stderr, dependency versions, host/head/source hashes, failures, privacy scan and complete SHA256 manifest in a 30-day CI artifact. Do not reclassify missing native hardware as PASS; report skips and failures verbatim. No models/weights downloaded or published.

**Heavy job serialization:** reuse `v13-native-c3-run131-serialized` concurrency group, `cancel-in-progress: false`, so the full-suite CPU dependency/test run does not compete with active Run336 native model work.

## Acceptance and limits

A green result means only source-level full-suite regressions pass on the exact branch; it does not override STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Redmi MISSING, V13 INCOMPLETE. If dependencies/fixtures fail, preserve raw RED and continue independent packages; never change frozen cohorts, Canon, native training, approval/age or existing CI owners. Next after this run: independently inspect raw artifact and the separate Run336 three-arm native result, then prioritize actual learned utility.
