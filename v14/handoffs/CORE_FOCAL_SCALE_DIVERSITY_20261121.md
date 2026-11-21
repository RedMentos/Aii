# Core handoff — source-span C4 admission + arithmetic date guard

**Date:** 2026-11-21  
**Owner:** Core & Harness  
**Base:** gpt6/v13-private-remote-bridge-20261111 at 4a471ae40dd9b768c8130fafdba51900b5417800  
**Status:** candidate implementation; CI pending; NOT_RELEASED; REDMI_UNVERIFIED.

## Functional hypothesis

FocalLoop.admit() applies one lexical redundancy penalty to every active item. That treats a B1_DETAIL offer and a B2_GIST offer as duplicates when their summaries overlap, even though the two bodies are intended to operate at different representational scales. A lower-priority cross-scale offer can consequently fall below the coalition threshold before analyst_context() builds the C3 hypothesis layer.

The C4 overlay discounts cross-scale lexical overlap only when both offers carry exact spans from the same source ID, digest and modality and those spans do not overlap. Same-role, overlapping, cross-source, missing-reference and body↔memory cases retain the full existing penalty. No numeric discount is calibrated or asserted. Coalition capacity, C5 authority, model selection and all learning/permission gates are unchanged.

The staged arithmetic overlay adds a narrow negative guard for bare year-month forms such as 2026-11, 2026/11 and “What is 2026-11?”. Explicit “calculate” / “berechne” prefixes remain eligible. This is not a general date parser; small two-number subtraction and division remain as before.

## Implementation

- v13/code/scripts/integrated_focal_scale_diversity_candidate_20261121.py: source-hash-bound patch of only the staged C4 redundancy calculation.
- v13/code/scripts/stage_v14_focal_scale_diversity_candidate_20261121.py: wraps the existing pinned integrated stager, applies the overlay in a disposable review tree, refreshes its manifest, and never edits the source Runtime or installed launcher.
- v13/code/tests/test_v14_focal_scale_diversity_20261121.py: direct C4 negative controls plus a real staged Runtime/SQLite synthetic turn. It checks that same-source non-overlapping B1/B2 evidence survives C4 and both offers/quotes reach the actual C3 prompt; overlapping, cross-source, hash-mismatched, same-role, memory and capacity controls retain the original penalty.
- .github/workflows/v14-core-focal-scale-diversity.yml: Python 3.13/3.14 exact-branch compile, staged Runtime, existing focal and base-stage regressions.

## Evidence

- LOCAL_LINUX isolated algorithm: PENDING — source-span complementarity rule replaces the uncalibrated numeric factor.
- LOCAL_LINUX overlay/stager/test syntax: PASS.
- LOCAL_LINUX arithmetic-overlay anchor/regex fixture: PASS — year-month forms are rejected; explicit calculate/berechne forms remain eligible.
- LOCAL_LINUX full repository stage / Runtime test: BLOCKED — no local checkout; git ls-remote https://github.com/RedMentos/Aii.git HEAD failed because github.com could not be resolved.
- CI: PENDING until exact branch workflow completes.
- REDMI/TERMUX: UNVERIFIED. No live phone receipt or native B1/B2/C3 process was available.
- This is synthetic Runtime/SQLite consumer evidence only if the CI test passes; it is not proof of native model quality, TTFT/RSS improvement, trained latent coupling or a Redmi fix.

## User impact and limits

If accepted into the normal stage builder, overlapping B1 and B2 hypotheses will be less likely to suppress one another before C3 context assembly. The arithmetic guard prevents year-month strings from being answered as subtraction/division unless the user explicitly marks the request as a calculation. Neither change bypasses source validation or changes model/weight, Age, permission, Termux installation or user data. The review stager is not yet wired into the normal pinned stage builder or deployed to Redmi.

## Next executable step

Verify exact-head Python 3.13/3.14 CI for the source-span C4→C3 consumer and arithmetic date-negative controls. If green, Boss reviews the conservative admission rule and the high-authority stage/deployer integration separately. Then measure native B1/B2 OfferPacket selection and C3 consumption on a consented Redmi receipt; until that receipt exists, keep REDMI_UNVERIFIED.
