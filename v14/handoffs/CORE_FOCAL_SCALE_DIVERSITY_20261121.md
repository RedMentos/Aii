# Core handoff — C4 cross-scale B1/B2 admission

**Date:** 2026-11-21  
**Owner:** Core & Harness  
**Base:** gpt6/v13-private-remote-bridge-20261111 at 4a471ae40dd9b768c8130fafdba51900b5417800  
**Status:** candidate implementation; CI pending; NOT_RELEASED; REDMI_UNVERIFIED.

## Functional hypothesis

FocalLoop.admit() applies one lexical redundancy penalty to every active item. That treats a B1_DETAIL offer and a B2_GIST offer as duplicates when their summaries overlap, even though the two bodies are intended to operate at different representational scales. A lower-priority cross-scale offer can consequently fall below the coalition threshold before analyst_context() builds the C3 hypothesis layer.

The staged overlay discounts only B1↔B2 redundancy by an explicitly uncalibrated engineering factor of 0.15. Same-role duplication and body↔memory redundancy retain the original full penalty. Coalition capacity, source checks, C5 authority, model selection and all learning/permission gates are unchanged.

## Implementation

- v13/code/scripts/integrated_focal_scale_diversity_candidate_20261121.py: source-hash-bound patch of only the staged C4 redundancy calculation.
- v13/code/scripts/stage_v14_focal_scale_diversity_candidate_20261121.py: wraps the existing pinned integrated stager, applies the overlay in a disposable review tree, refreshes its manifest, and never edits the source Runtime or installed launcher.
- v13/code/tests/test_v14_focal_scale_diversity_20261121.py: direct C4 negative controls plus a real staged Runtime/SQLite synthetic turn. It checks that overlapping B1/B2 offers both survive C4 and both are present in the actual C3 prompt.
- .github/workflows/v14-core-focal-scale-diversity.yml: Python 3.13/3.14 exact-branch compile, staged Runtime, existing focal and base-stage regressions.

## Evidence

- LOCAL_LINUX isolated algorithm: PASS — cross-scale overlap becomes 0.15; same-role duplicate remains 1.0.
- LOCAL_LINUX overlay/stager/test syntax: PASS.
- LOCAL_LINUX full repository stage / Runtime test: BLOCKED — no local checkout; git ls-remote https://github.com/RedMentos/Aii.git HEAD failed because github.com could not be resolved.
- CI: PENDING until exact branch workflow completes.
- REDMI/TERMUX: UNVERIFIED. No live phone receipt or native B1/B2/C3 process was available.
- This is synthetic Runtime/SQLite consumer evidence only if the CI test passes; it is not proof of native model quality, TTFT/RSS improvement, trained latent coupling or a Redmi fix.

## User impact and limits

If accepted into the normal stage builder, overlapping B1 and B2 hypotheses will be less likely to suppress one another before C3 context assembly. This does not force both bodies through a one-slot coalition, does not bypass source validation, and does not change direct-answer fastpaths. No model, weight, Age, permission, Termux installation or user data was changed. The review stager is not wired into the normal updater and is not a deployment.

## Next executable step

Verify exact-head CI and independently inspect the staged C4→C3 prompt test. If green, ask Boss to review the scale-diversity policy and coordinate its inclusion in the current staged Runtime chain without colliding with the stale RAW EAR consumer branch #2158. Then measure actual Redmi OfferPacket selection and C3 prompt delivery under the authorized private diagnostic relay; until that receipt exists, keep REDMI_UNVERIFIED.
