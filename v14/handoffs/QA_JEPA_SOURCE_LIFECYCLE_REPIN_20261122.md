# QA handoff — JEPA source-lifecycle pin repair (2026-11-22)

## State

INTEGRATION_PENDING. This patch is stacked on JEPA Run 14 base commit aae0330e24279ed2782451e7effe78ee005ac490. It is not a release and has not been installed on Redmi.

## Reproduced blocker

The staged World-JEPA training-resume path stops in source_lifecycle_lock_integration_candidate.py because the lifecycle composer rejects the current memory.py source hash. The existing CI report identifies memory.py as the first failing source. The separate Record-Only controller/source pin failure is not part of this QA-owned repair and must remain visible.

## Patch contents

- Updated the lifecycle composer memory.py SHA-256 declaration (currently set to def5d6c1fa7118a16c88b893e1a4b8b1a1a01285d2afa2924ca72ebb65e07e30).
- Rebound the downstream generated-builder chain bottom-up: lifecycle -> memory/world -> feedback -> context recall -> World-JEPA training resume -> Termux recovery -> Termux wrapper -> integrated stager.
- Added a Python hashlib regression in test_world_jepa_training_resume_stage_20261111.py. It compares the declared lifecycle pin against the actual checked-out memory.py bytes.

## Verification boundary

- GitHub source readback: the edited candidate and downstream builder files are present on the QA branch.
- Python test and staged integration: NOT YET RUN on the final squashed head; exact-head GitHub Actions is required.
- Local Linux execution: unavailable in this run.
- Termux/Redmi: REDMI_UNVERIFIED; no private owner-read receipt or device execution was available.
- No model, user SQLite, chats, weights, permissions, or installed app were changed.

## Hash discrepancy to resolve in CI

An earlier team note stated memory.py SHA-256 33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701. This branch currently declares def5d6c1fa7118a16c88b893e1a4b8b1a1a01285d2afa2924ca72ebb65e07e30. The added Python hashlib test is the authority: do not merge if it fails; use the exact hash printed by that test and recompute every downstream builder pin bottom-up.

## Next action

Run the JEPA Python 3.13/3.14 workflow and staged-integrated workflow on the exact PR head. Fix any remaining source/pin mismatch without weakening CI. After merge into the Run 14 branch, re-run PR #2372 on its new exact head.