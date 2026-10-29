# World-JEPA single-member donor integration — 2026-10-29

Owner: GPT-6 review integration, distinct from the P2X native/LoRA owner. Review-only child of PR #1090 exact `1aa13abec66eccd2df24942479e1194e826caa5e`. No production merge, frozen source/model/seed/cohort edits, or authority promotion.

Problem and original RED evidence: donor PR #957 / Run49 demonstrated that a positive-step WorldJEPA fit with only one predictor has zero *computed* ensemble spread and can incorrectly exceed CF_MIN. Original source blob `b95cd3fd9172ddef0fb88f0a7d70e2921c43e777`. RED Actions 40752223744, source-only test failure with confidence 0.63212056. Donor GREEN Actions 40752899144 on commit `5a37097d896521a1d217dd069c434b642f297a8a`. The original donor source patch blob `5ada6e93ae4cab2e3dedfec82c315d559fb9cd6b` and test blob from donor PR #957 will be transplanted unchanged, preserving provenance and independently retested on the newer integrated chain. This is integration/revalidation of existing work, not a novel algorithm.

Ownership: only `v13/code/v13/world_jepa.py`, new `v13/code/tests/test_run49_world_jepa_single_ensemble_confidence.py`, this prereg, a dedicated CI workflow, and additive review handoff. Do not touch P2X files, Runtime/Store, Canon, frozen registrations, or existing donor branch.

Acceptance: verify donor source/test blob equality on child; original parent blob exact; focused WorldJEPA tests (single-member uncertainty, positive-step two-member, zero-step, checkpoint, reader/refit, heldout) plus full software suite in isolated CI; compile, privacy scan and diff check, raw stage exit files and SHA256SUMS. Preserve RED evidence and all negative gates. No native model, Redmi, actual JEPA utility, STEP2, B3, AG6 or age promotion.

Expected negative gates: Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE. Stop if parent/donor source mismatch; never silently overwrite newer owner edits.
