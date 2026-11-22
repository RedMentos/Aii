# QA handoff — JEPA source-lifecycle pin repair (2026-11-22)

## State

INTEGRATION_PENDING. This patch is stacked on JEPA Run 14 base commit aae0330e24279ed2782451e7effe78ee005ac490. It is not a release and has not been installed on Redmi.

## Reproduced blocker

The staged World-JEPA training-resume path stops in source_lifecycle_lock_integration_candidate.py because the lifecycle composer rejects the current memory.py source hash. The existing CI report identifies memory.py as the first failing source. The separate Record-Only controller/source pin failure is not part of this QA-owned repair and must remain visible.

## Patch contents

- Updated the lifecycle composer memory.py SHA-256 declaration (now set to the Python 3.13 CI-observed value 33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701).
- Rebound the downstream generated-builder chain bottom-up: lifecycle -> memory/world -> feedback -> context recall -> World-JEPA training resume -> Termux recovery -> Termux wrapper -> integrated stager.
- Added a Python hashlib regression in test_world_jepa_training_resume_stage_20261111.py. It compares the declared lifecycle pin against the actual checked-out memory.py bytes.

## Verification boundary

- GitHub source readback: the edited candidate and downstream builder files are present on the QA branch.
- Python test and staged integration: NOT YET RUN on the final squashed head; exact-head GitHub Actions is required.
- Local Linux execution: unavailable in this run.
- Termux/Redmi: REDMI_UNVERIFIED; no private owner-read receipt or device execution was available.
- No model, user SQLite, chats, weights, permissions, or installed app were changed.

## Hash discrepancy to resolve in CI

Python 3.13 and 3.14 CI confirmed memory.py SHA-256 33377446f8dca709c0d829764dac6e1d4f1ca92729b955d8a8ad983a16bb1701 and all eight lifecycle source PINS match. The expanded regression then identified two downstream mismatches (feedback builder SHA and Termux wrapper base Git blob SHA1), now corrected from Python's actual outputs. It also checks the C3 base builder pin, which is the remaining unverified edge. Do not merge unless the full chain and staged runtime tests pass.

## Next action

Run the JEPA Python 3.13/3.14 workflow and staged-integrated workflow on the exact PR head. Fix any remaining source/pin mismatch without weakening CI. After merge into the Run 14 branch, re-run PR #2372 on its new exact head.