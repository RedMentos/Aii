# Core & Harness — Run 15 handoff (2026-11-22)

## Verified branch and changes

- Release-development base: `gpt6/v13-private-remote-bridge-20261111` at `c2e7ae7ebe47af6ea96995c7df112872bb404d38`.
- Core PR [#2323](https://github.com/RedMentos/Aii/pull/2323) merged at `c2e7ae7`. It composes the pinned llama.cpp native input-embedding diagnostic receiver and exposes `:callosum native-probe`. Candidate-head CI was 21 SUCCESS / 0 FAILURE / 2 SKIPPED. The receiver remains diagnostic-only; production B3 stays OFF.
- New Core PR [#2325](https://github.com/RedMentos/Aii/pull/2325), branch `core/v14-fair-scheduler-sender-containment-20261122-run15`, code commit `af2a14381df9d9c0a6f67875894ec29df5ed6dba`, is DRAFT and based on c2e7ae7. It changes the budgeted sequential observer precheck to let the per-role minimum-slice gate run while retaining the one-second guard for unbudgeted legacy scheduling. It adds 1.5 s subminimum-peer continuation, exact 2.0 s threshold, and legacy-guard tests.
- The same PR hardens sender model integrity: symlink rejection, strict path resolution, containment under `<home>/models`, regular-file check, then pinned SHA-256 verification. Outside-path and symlink negative tests are added.
- The overlay → recovery wrapper → stage builder → runtime deployer SHA/blob pin chain was recomputed and read back.

## Tests and environments

- **LOCAL_LINUX PASS, isolated only:** CPython 3.13.5 x86_64; subminimum scheduler, exact-threshold scheduler, legacy unbudgeted guard; installed sender path accepted, outside path rejected, symlink rejected.
- **LOCAL_LINUX full repository BLOCKED:** `git ls-remote https://github.com/RedMentos/Aii.git` failed with `Could not resolve host: github.com`. No full local Aii pytest, compile or repository integration run is claimed.
- **CI for #2325:** exact head `af2a14381df9d9c0a6f67875894ec29df5ed6dba` had staged receiver, same-turn, Lab-Age, updater migration and owner-read workflows QUEUED/PENDING at the last poll; safe-additive validation was SKIPPED. No CI PASS is claimed yet.
- **QA #2324:** separate QA-owned branch, exact head `e0cc0c69dfa35cc13566f5b41b206fe00703b269`, two workflows SUCCESS. Its 90 s fairness test covers 20.25 s per body; #2325 adds the missing scheduler-level exact threshold. Do not edit the QA branch.
- **Post-merge CI for c2e7:** ten listed release-branch workflows completed SUCCESS; one additional `offline-bridge-security` check was still IN_PROGRESS at the last poll. Do not treat this as fully green.
- **Redmi:** private owner-authenticated receipt #505 (08:28 UTC) predates c2e7 and reports installed SHA `c03ff0aa9e18b5ffebd1109f3c078105f53c6afe`, auto-update enabled, runtime/dashboard UP_TO_DATE, last_error NONE; latest turn FINAL 63.22 s / TTFT 42.48 s / prefill 34.96 s; B1/B2 TIME_BUDGET 53.2/54.2 s; C3 3.1 s. No post-merge install receipt exists. **REDMI_UNVERIFIED for c2e7/#2325**. No UPDATE_REQUEST or device mutation.

## Canon and product effect

- B1/B2 sequential fairness: fixes the exact 1.0 s admission edge without removing either body or reducing the C3 reserve. The current budget policy retains 16.5 s C3 reserve for a 30 s turn and 49.5 s for a 90 s turn; the 90 s observer window is 40.5 s and the expected two full slices are 20.25 s each.
- B3/Enlightened: pinned native input-embedding path is now buildable/testable as a diagnostic. This is **not** a trained cross-family latent channel, not semantic utility, not learned retention, and not production routing.
- Android action/outcome: no OS executor, installed APK, app launch, screen capture, tap/type or complete ActionOutcome user path was tested in this run.
- Learning: no gradient, weight diff, adapter update, persistent promotion, retention or rollback experiment. No model or weight was changed.
- Voice/audio, World/Self/Memory, Sleep/Replay, sparse MoE and Android UI/background control remain open according to the coverage index.

## Next exact actions

1. Poll the exact PR #2325 checks; if any fail, inspect the failing job and fix the actual source/pin/test, then rerun the relevant workflow.
2. Rebase/coordinate QA #2324 onto the current release base after Core review; keep the 90 s, exact-threshold and deferral negative controls distinct.
3. Continue Core's permissioned Android companion/operator CLI integration on a compatible base, with explicit pairing confirmation and default-OFF action authority.
4. Only after all exact post-merge push checks are green, obtain a separate owner-authenticated PIPELINE_STATUS receipt. Do not issue UPDATE_REQUEST before that.
5. Keep production B3 OFF until real sender/receiver activations, independent labels, zero/shuffle/source-exact controls, task utility, OOD, retention and rollback are demonstrated on authorized hardware.

**User action:** none. No Termux command, model swap, permission change or device operation is needed.
