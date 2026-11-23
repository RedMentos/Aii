# Core & Harness handoff — ActionSelection source lineage — 2026-11-24

## Ownership and base
- Owner: Core & Harness.
- Work branch: `core/v14-actionselection-source-lineage-20261124`.
- Base release-development SHA: `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Current branch HEAD at this handoff: `69b9a28175799b6ce70fd7ff483f12552d9889ae`.
- Code commit: `024e2facf315904ef8aba22adeb74e582c6669b5`.
- Test commit: `3f378f27e6bb7f822a152765cc2005af50e96cf9`.
- Dedicated workflow commit/fix: `461106a59342290f39e35622fec0b53926a569c3` / `69b9a28175799b6ce70fd7ff483f12552d9889ae`.
- PR: NOT_CREATED. GitHub create-pull-request returned HTTP 403: at least one email address must be verified. No workaround attempted.

## Concrete gap
The production C5 ActionGate wrote only `[e.source_ref]` into ActionSelection provenance. The source-bound T8/JEPA consumer already reads ActionSelection provenance and merges C4 FocalCycle lineage, but the producer did not directly carry admitted Memory, observer, Context OS, Enlightened Space, or QueryPacket/BodyView source refs. This was the explicit V14-012 next step.

## Implemented
- `v13/code/v13/focal.py`: ActionGate now constructs a bounded (64), deduplicated, digest-checked, readable SourceRef set from the current event, admitted coalition items, persisted OfferPacket evidence/context/enlightened refs, and bound QueryPacket source/context/enlightened provenance. It also includes fixed-rule OutputPolicyDecision refs.
- Offer and Query packet identity, event/generation/role/state-version bindings are checked before their refs are consumed.
- Missing, malformed, unreadable, conflicting, or over-bound lineage fails closed before ActionSelection commit and before C5 learning side effects.
- Only SourceRef metadata is persisted; source text is read for validation but is not copied into ActionSelection.
- `v13/code/tests/test_focal.py`: producer/consumer readback, memory + observer + Context OS + Enlightened + QueryPacket/BodyView refs, SQLite restart, privacy non-copy, unreadable-digest negative test; the existing strong-body fixture now stores a real OfferPacket.
- `.github/workflows/v14-actionselection-lineage-20261124.yml`: exact source compile and focal regression matrix for Python 3.11/3.13/3.14.

## Evidence
- LOCAL_LINUX synthetic MiniStore: PASS — source union, QueryPacket binding, invalid-digest rejection, SQLite restart/readback.
- Full repository checkout and pytest: BLOCKED — `git ls-remote` failed with `Could not resolve host: github.com`; no local Aii checkout is mounted.
- Exact-head GitHub Actions: NOT_RUN / no workflow run was visible for the branch at last readback. Do not call CI green.
- Redmi/Termux: REDMI_UNVERIFIED. No private device receipt, APK, native model, or phone action was used.
- Deployment/updater: NOT_VERIFIED; GitHub branch push is not deployment. No UPDATE_REQUEST or device command was sent.
- Models, weights, permissions, user data, and installed device state: unchanged.

## Consumer and integration
The production consumer is `v13/code/v13/world_jepa_store_authority.py::_selection_source_refs`. The new test invokes that consumer and confirms the expanded producer refs survive SQLite restart. Its existing C4 FocalCycle merge remains in place for prior-cycle lineage. Coordinate with JEPA & Memory to run the full temporal/source-forget gates after Boss rebinds the active nested Runtime/JEPA pins. Do not edit those owner files from this branch.

## Next executable steps
1. Resolve the GitHub email-verification restriction through the account owner or have the authorized Boss create the PR from this branch; do not create a substitute/duplicate PR.
2. Run the exact-head 3.11/3.13/3.14 workflow and fix any observed failures.
3. Rebase/review on the then-current integration head without overwriting #2458 or JEPA-owned work; run source-forget, T8 transition, staged and integrated regression.
4. Keep whole V14-012 open: this does not implement Memorilla overflow consumption, query-sensitive episodic recall, real numeric JEPA weight learning, trained B3 latent exchange, or Android proof.

User action: none for the device. GitHub PR creation is blocked by the connected GitHub account's unverified email; no installed update or manual Termux command is needed.
