# QA & Android handoff — Android 13 bind-mount identity (2026-11-21)

## Scope and ownership

This is a QA-owned correction under V14-009 (permissioned Android device-control prerequisites) and the whole-Canon epic #1984. It does **not** close the P0 real-chat gate #1904 or implement Android API/UI execution.

## Verified source facts

AOSP Android 13 init.rc:
- sets /data to system:system mode 0771 (lines 673–677);
- creates /data/data as system:system mode 0771 (line 843);
- creates /data/user/0, then bind-mounts /data/data onto /data/user/0 (lines 915–923).

The bind-mounted path is a directory, not a symlink. The compatibility exception therefore must require exact UID/GID/mode **and** matching st_dev/st_ino with /data/data; a pathname-only or owner/mode-only allowlist is too broad.

Primary source: https://android.googlesource.com/platform/system/core/+/refs/heads/android13-release/rootdir/init.rc

## Code checkpoint

- Release-development base readback: gpt6/v13-private-remote-bridge-20261111 at 4a471ae40dd9b768c8130fafdba51900b5417800.
- QA branch: qa/android13-bindmount-identity-rebase-20261121.
- Current QA head: 3fb5f96b6205bc51ff206afe40c643fd9a907049.
- PR: https://github.com/RedMentos/Aii/pull/2197
- Source blob: 069f7c42bc793ee42f72496ca23164dc56918d10.
- Test blob: e75b0a98604bf3735af28de5e29a4f9b20a3e538.
- The guard permits /data/user/0 only for exact system:system 0771 metadata with the same device/inode as /data/data. Negative tests cover mismatched inode, bind UID/GID/mode, target UID/GID/mode, world-write and writable descendants.
- The stale, diverged PR #2191 (6 ahead / 6 behind current release) was closed as superseded; no changes were lost.

## Exact evidence at this checkpoint

- V13 Android local sandbox replay integration run 44898539122: PASS (simulation job).
- V13 integrate reviewed agent PRs on release events run 44898539104: PASS.
- V13 Android control broker isolated tests run 44898539132: PASS (broker job).
- V13 staged context and integrated regression run 44898539112: IN_PROGRESS at readback; staged-runtime and integrated-regression jobs were still running.
- V13 safe additive candidate tests run 44898539106: FAIL by the existing-module scope rule, with exact message 'not a strictly additive PR'. This PR changes the existing android_control.py; no policy gate was bypassed. Manual Boss review remains required.
- Exact local full-checkout tests: BLOCKED because this execution environment cannot resolve GitHub DNS. No local PASS is claimed.
- The tests synthesize filesystem metadata; they do not create a real bind mount or prove Redmi behavior.

## Device / release boundary

- Private read-only owner-relay requests HEALTH #396, PIPELINE_STATUS #397 and DIAGNOSTICS #398 were created with 10-minute expiry. At the latest readback all three had zero comments.
- Installed Redmi SHA: UNKNOWN. Auto-update consent/state: UNVERIFIED. Device: REDMI_UNVERIFIED.
- No UPDATE_REQUEST, shell action, installer, model swap, permission change or phone-data mutation was performed.
- The merged #2190 path broker remains DRY_RUN_ONLY; no Android OS executor, authenticated companion, AccessibilityService, MediaProjection or UI action is implemented by this patch.

## Next action

Read back all exact-head CI jobs for #2197. If the focused broker, staged and integrated checks pass, request Boss's manual review of the existing-module security exception. Do not deploy or claim Android verification without a fresh owner-authenticated phone receipt. Continue the shared P0 #1904 work separately: correct answer quality, native B1/B2 offers actually consumed by C4/C3, latency and 20-turn Redmi evidence remain open.
