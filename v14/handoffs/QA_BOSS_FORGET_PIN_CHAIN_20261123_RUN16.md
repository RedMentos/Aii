# QA — Boss Memory/forget source-pin chain repair

Date: 2026-11-23
Role: QA & Android
Branch: `qa/v14-boss-forget-pin-chain-20261123-run16`
Stacked base: Boss PR #2443 branch `boss/v14-memory-forget-lifecycle-composition-20261123-run11-clean`
Base commit: `395bba21c39dfb0d92882babc85de306f12e4438`
Code checkpoint before this handoff file: `e2c58ecce248507f91c4520f8fb221233e8793dc`

## Reproduced blocker

On exact Boss head `395bba21c39dfb0d92882babc85de306f12e4438`, three independent CI paths failed at the same immutable source-composition check:

- Lab Age E2E: run `45248409528`
- staged + integrated regression: run `45248409132`
- JEPA optimizer-resume Python 3.13/3.14: run `45248409153`

The first failing consumer was `record_only_controller_guard_20261116.py:198`: it expected SHA-256 `9f4a665d92af9ae4bedd559d036887c356f87615e4d0f49cce30c79f03838875` for the generated `v13/local_error_route_shadow_candidate.py`, but the actual source bytes were `34944ff94efb2bfc962d0150b04d411fb256d5e62e86e1fc70ae396a36fd488c`. No test gate was relaxed.

## Repair

Copied the exact already-reviewed, source-derived pin values from QA PR #2455 onto the current Boss parent. Only five pin-bearing files changed:

1. `v13/code/scripts/record_only_controller_guard_20261116.py`
2. `v13/code/scripts/termux_runtime_recovery_candidate_20261112.py`
3. `v13/code/scripts/termux_runtime_recovery_candidate_20261121.py`
4. `v13/code/scripts/stage_integrated_candidate.py`
5. `v13/code/v13/runtime_deploy.py`

The corrected bottom-up chain is:

- generated local-error source SHA-256: `34944ff94efb2bfc962d0150b04d411fb256d5e62e86e1fc70ae396a36fd488c`
- controller-guard SHA-256 consumed by recovery-12: `20c79bc99f3733ddc12ce186bb93ad31956d81847cfd5b06a9ec24675df36639`
- recovery-12 Git blob SHA-1 consumed by recovery-21: `9a0927cf4475bfb3a49f14a6ec57a646d4c4db2a`
- recovery-21 SHA-256 consumed by integrated stage: `16fc4a35ad94b6f7ee0cb4ed06b622e4c19a3887081225ed69e516236b10a41f`
- integrated-stage SHA-256 consumed by RuntimeDeploy: `37efcc130d755019151da170098c81fb8a6e9680b2676180370393e70c8eb9b0`

The upstream source-builder files compared identical between the current Boss head and #2455's tested candidate; only the five dependent pin values needed to be transplanted.

## Verification boundary

- Exact branch CI: pending at handoff creation; must be inspected on the final PR head.
- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN; no checkout is mounted and GitHub DNS lookup from the local container fails.
- Existing parent vision source-lineage run `45248409266`: Python 3.13 and 3.14 PASS, but the QA-owned stronger canonical-unlink interleaving regression remains in PR #2455 and is deliberately not mixed into this pin-only blocker PR.
- Runtime deployment integrity on the parent before this patch: run `45248409285` PASS.
- Redmi: `REDMI_UNVERIFIED` for these changes. The latest authenticated private receipt says installed base `8d93236c753f0194224c19edc7411d8d7082b1d6`, updater/runtime/dashboard UP_TO_DATE, but AI is `STOPPED_BY_USER` with autostart false. No restart, CHAT_SEND, UPDATE_REQUEST, model operation, or device mutation was attempted.

## Next action

Run exact-head Lab Age, staged/integrated, optimizer-resume Python 3.13/3.14, runtime deployment integrity, and all source-builder consumers. After this pin-only PR is integrated and Boss #2443 is green, rebase the QA-owned vision cleanup race test from #2455 onto the exact new parent and test the actual canonical `os.unlink(..., dir_fd=...)` seam while Store.tx is held.
