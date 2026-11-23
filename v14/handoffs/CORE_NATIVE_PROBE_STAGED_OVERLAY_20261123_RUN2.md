# Core & Harness — native-probe staged overlay checkpoint (2026-11-23)

## Source state

- Repository: `RedMentos/Aii`.
- Base: `gpt6/v13-private-remote-bridge-20261111` at `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- Work branch: `core/v14-native-probe-staged-overlay-20261123-run2`.
- Initial branch read-back before the code/handoff/board sync: `81e08489ac3710c84f8228b8c095a80a14030597`.
- Code checkpoint commit: `8d4c0678cfad1f0fce995c9b7df22d1f21d8da77`; the handoff and board synchronization commits follow it on the same PR branch. PR #2451 is the authoritative current head.
- Supersedes the direct-`operator.py` edit attempted by draft PR #2449. #2449 remains blocked because that edit violates the integrated receiver source pin; do not merge it.

## New connected runtime slice

- Added `v13/native_probe_approval.py`: one-shot local-TTY approval bound to the current FINAL text SourceRef, active session/generation, sender/receiver roles, exact installed model revision, model manifest SHA-256, selected model path and inode identity.
- The helper requires a fresh approval, rechecks the binding at consume, atomically consumes it before native work, holds an exclusive idle Runtime lease, enforces a 120-second deadline, forwards Ctrl+C to the receiver, and unloads the managed body pool after the probe.
- The resource preflight checks only the known managed census (B1/B2/C3 pool, C2/Needle, semantic-key encoder) plus MemAvailable. It explicitly reports that this is not a global native-process census or OOM guarantee.
- Added `integrated_native_probe_approval_overlay_20261123.py`. It checks exact Git-blob pins for the canonical operator and approval module, then patches **only the staged** `v13/operator.py` dispatch/help after the pinned recovery, native receiver and arithmetic overlays. Canonical source `operator.py` remains byte-identical.
- `stage_integrated_candidate.py` now records the overlay in `INTEGRATION_STAGE.json`; `runtime_deploy.py` pins the exact updated stage-builder SHA-256 `584a2dc02f4e2d96ffe5bc91ab001e48d39c60baf5f138d2c3809b862a93da47`.
- Added an exact staged-runtime regression suite (approval/consume/revoke, model tamper and route drift, source/session binding, resource refusal, cancellation/lease, remote allowlist) plus overlay negative controls. The nested stage test imports the patched Operator from the final staged tree.

## Verification

- **LOCAL_LINUX_ISOLATED — PASS:** overlay helper with controlled fixture files; staged-only replacement, Python compile, unchanged source bytes, tampered staged-operator rejection, and duplicate insertion-anchor rejection.
- **LOCAL_LINUX_FULL_REPOSITORY — BLOCKED / NOT_RUN:** no mounted Aii checkout; `git ls-remote` failed DNS. No full local pytest, full stage build or native llama.cpp execution is claimed.
- **CI — PENDING:** exact Python 3.13/3.14 staged receiver workflow will run after this PR is opened. Do not call it green until the exact PR head reports success.
- **REDMI — REDMI_UNVERIFIED:** no connected device test, no native probe, no Termux command, no update request, no APK, model, weight, permission or user-data change.

## Scope and safety boundary

This is a diagnostic operator path only. It does **not** activate production B3, train an alignment projector, prove receiver utility, change model routing, edit weights, grant tool authority, download/swap models or operate Android apps. The remote chat allowlist remains excluded. The approval requires a real interactive local TTY even if a caller claims an operator origin.

## Next executable step

1. Open the draft PR against the current release-development branch and wait for exact-head Python 3.13/3.14 staged CI, privacy scan and existing native receiver/Android ARM64 build checks.
2. Fix any real failures without editing the pinned canonical `operator.py` or weakening source checks; independently review the overlay and local approval boundary.
3. After Boss integration and a separate authenticated installation receipt, ask for a distinct one-shot probe decision only if a fresh Redmi diagnostic is still justified. Keep production B3 OFF until latent-vs-SOURCE_EXACT-vs-NO_MESSAGE, shuffled/zero/OOD controls and held-out receiver utility are actually measured.

**User action: none at this checkpoint.**


## Run 3 — exact-head fixture repair and CI verification (2026-11-23T18:23:01.047Z)

### Change

The first exact staged Runtime run on the previous code head exposed three failures in `StageTest`: the temporary source fixture lacked the required native-probe overlay, pinned canonical operator and approval module. The stage builder correctly failed closed. The test fixture now copies the exact repository operator, approval module and real overlay into the temporary source tree. It also verifies that only the staged operator is changed, that the manifest records `SHADOW_REVIEW_ONLY`, and that the inventory contains the added pinned files. Production missing-overlay/source-pin checks were not weakened.

- **Code-tested commit:** `ea7535e8ad83f16cdbf7f5df626b96123ad309f6`.
- **PR:** [#2451](https://github.com/RedMentos/Aii/pull/2451), still DRAFT / NOT_RELEASED.

### Exact test evidence

- Native receiver workflow #45236111168: Python 3.13 and 3.14 each **12 passed**; Linux pinned API PASS; Android ARM64 cross-compile PASS. The first Python 3.13 attempt failed only during a transient pip package download (connection reset); the targeted rerun passed.
- Staged/integrated workflow #45236111273: staged Runtime **255 passed, 10 skipped, 47 subtests**; integrated regression **424 passed, 3 skipped, 58 subtests**.
- Audio/arithmetic workflow #45236111290: Python 3.13 and 3.14 each **52 passed, 26 subtests**.
- Same-turn B1/B2→C4→C3 consumer workflow #45236111088: Python 3.13 and 3.14 PASS.
- Runtime deploy integrity #45236110955, Lab-Age #45236111027, private owner-read bootstrap #45236111099, two-checkout migration #45236111102 and release-event integration queue #45236111121: SUCCESS. Safe-additive candidate check was SKIPPED by policy.

### Honest limits and next work

- Full local Aii checkout/tests: **BLOCKED / NOT_RUN**; no checkout is mounted and GitHub DNS fails from the local container.
- Redmi: **REDMI_UNVERIFIED**. No device probe, install, update request, Termux command, model/weight/permission/data mutation.
- The native probe is diagnostic-only. It does not prove a trained cross-organ projector, receiver utility or production B3. Normal B1/B2 same-turn offer quality and correct C3 output remain unverified on Redmi.
- Independent Boss/QA review is pending. Next: review/integrate #2451, then recompose the stale fair B1/B2 pre-answer scheduler on current release HEAD while preserving both bodies, C3 reserve and source-bound C4/C3 consumption.

**User action: none.**
