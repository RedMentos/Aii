# Core handoff — C4 body diversity + arithmetic fastpath guard

**Date:** 2026-11-21  
**Owner:** Core & Harness  
**Base:** gpt6/v13-private-remote-bridge-20261111 at 4a471ae40dd9b768c8130fafdba51900b5417800  
**Status:** candidate implementation; CI pending; NOT_RELEASED; REDMI_UNVERIFIED.

## Functional hypothesis

FocalLoop.admit() applies one lexical redundancy penalty to every active item. That treats a B1_DETAIL offer and a B2_GIST offer as duplicates when their summaries overlap, even though the two bodies are intended to operate at different representational scales. A lower-priority cross-scale offer can consequently fall below the coalition threshold before analyst_context() builds the C3 hypothesis layer.

The staged C4 overlay discounts only B1↔B2 redundancy by an explicitly uncalibrated engineering factor of 0.15. Same-role duplication and body↔memory redundancy retain the original full penalty. Coalition capacity, source checks, C5 authority, model selection and all learning/permission gates are unchanged.

The staged arithmetic overlay adds a narrow negative guard for bare year-month forms such as 2026-11, 2026/11 and “What is 2026-11?”. Explicit “calculate” / “berechne” prefixes remain eligible. This is not a general date parser; small two-number subtraction and division remain as before.

## Implementation

- v13/code/scripts/integrated_focal_scale_diversity_candidate_20261121.py: source-hash-bound patch of only the staged C4 redundancy calculation.
- v13/code/scripts/stage_v14_focal_scale_diversity_candidate_20261121.py: wraps the existing pinned integrated stager, applies the overlay in a disposable review tree, refreshes its manifest, and never edits the source Runtime or installed launcher.
- v13/code/tests/test_v14_focal_scale_diversity_20261121.py: direct C4 negative controls plus a real staged Runtime/SQLite synthetic turn. It checks that overlapping B1/B2 offers both survive C4 and both are present in the actual C3 prompt.
- .github/workflows/v14-core-focal-scale-diversity.yml: Python 3.13/3.14 exact-branch compile, staged Runtime, existing focal and base-stage regressions.

## Evidence

- LOCAL_LINUX isolated algorithm: PASS — cross-scale overlap becomes 0.15; same-role duplicate remains 1.0.
- LOCAL_LINUX overlay/stager/test syntax: PASS.
- LOCAL_LINUX arithmetic-overlay anchor/regex fixture: PASS — year-month forms are rejected; explicit calculate/berechne forms remain eligible.
- LOCAL_LINUX full repository stage / Runtime test: BLOCKED — no local checkout; git ls-remote https://github.com/RedMentos/Aii.git HEAD failed because github.com could not be resolved.
- CI: PENDING until exact branch workflow completes.
- REDMI/TERMUX: UNVERIFIED. No live phone receipt or native B1/B2/C3 process was available.
- This is synthetic Runtime/SQLite consumer evidence only if the CI test passes; it is not proof of native model quality, TTFT/RSS improvement, trained latent coupling or a Redmi fix.

## User impact and limits

If accepted into the normal stage builder, overlapping B1 and B2 hypotheses will be less likely to suppress one another before C3 context assembly. The arithmetic guard prevents year-month strings from being answered as subtraction/division unless the user explicitly marks the request as a calculation. Neither change bypasses source validation or changes model/weight, Age, permission, Termux installation or user data. The review stager is not wired into the normal updater and is not a deployment.

## Next executable step

Verify exact-head Python 3.13/3.14 CI, including the staged C4→C3 consumer and arithmetic date-negative controls. If green, ask Boss to review the 0.15 scale-diversity default and date guard, then coordinate their inclusion in the normal stage chain without colliding with the stale RAW EAR consumer branch #2158. Finally measure native arithmetic correctness and actual Redmi OfferPacket selection/C3 prompt delivery through the authorized private diagnostic relay; until those receipts exist, keep REDMI_UNVERIFIED.
