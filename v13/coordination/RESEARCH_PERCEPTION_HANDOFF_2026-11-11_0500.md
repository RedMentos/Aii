# Research & Perception handoff — 2026-11-11 05:00 Europe/Berlin

## Scope and evidence
Candidate-only opt-in A0(text SourceRef) -> existing Cognition.percept (A1/A3/A5) -> persisted PerceptPacket -> source-exact B1/B2 views. Does not patch frozen Runtime, install weights, invoke B native inference, promote A3 or claim Android verification.

Parent: PR #1731 (A3 checkpoint structural audit); earlier PRs #1729, #1687. Source contract: v13/code/v13/cognition.py, contracts.py, store.py, percept_subspan_candidate.py. Team plan PR #1668.

Run from v13/code:
```
PYTHONPATH=. python -B -m unittest -v tests.test_percept_runtime_route_candidate_20261111
```

Synthetic test coverage: real Store, Cognition.percept and persisted PerceptPacket with no A3 student weights; B1 fixed and B2 event SourceRef exact replay; bad digest rejection; nonzero source span rejected before writing because frozen A5 segmenter currently uses local offsets. Test execution not verified in this automation environment; remote GitHub CI pending. Native Redmi and teacher truth remain UNVERIFIED. No new input modality: TEXT ONLY.

## Open blocker
Current A5 `segments(text, e['source_ref'],...)` uses local indices for subspans. Before allowing nonzero spans, integrate source_segments into frozen Cognition.percept with cross-owner approval and add restart tests. Verify actual A3 with pinned teacher checkpoint separately; this candidate has A3 UNAVAILABLE in the synthetic fixture.

## Gates
Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, world JEPA SHADOW. No promotion or new permissions. Privacy scan, full suite and independent review still required.
