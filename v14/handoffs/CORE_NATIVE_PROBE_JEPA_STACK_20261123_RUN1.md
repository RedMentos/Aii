# Core handoff — native receiver approval overlay stacked on JEPA runtime

Date: 2026-11-23
Owner: Core & Harness
Dependency: JEPA/Memory PR #2454, branch `jepa-memory/v14-temporal-boss-2443-rebase-20261123-run14`, exact base head `bf2913b150d8decbf6e33c43920d21acc83439b3`
Core branch: `core/v14-native-probe-jepa-stack-20261123-run2`

## Implemented

- Ported the final-stage-only native receiver approval overlay from the standalone Core candidate onto the current JEPA/Memory recovery chain.
- The canonical `v13/operator.py` remains byte-identical. The overlay modifies only the staged operator after the pinned recovery and arithmetic builders.
- Local probe requires an interactive TTY, explicit `--confirm`, a current FINAL authoritative text SourceRef, exact installed model revision/path/manifest/file identity, one-shot approval, exclusive Runtime lease, verified native-process census and MemAvailable, a 120-second deadline, cancellation propagation and managed-body unload.
- Probe is diagnostic-only: production B3 routing OFF, no training authority, no weight/model swap, no Android action, and no remote-chat allowlist entry.
- Updated the exact nested stage pins for the JEPA recovery builder and final stage/deployer.
- Expanded the focused native workflow to execute native receiver, Runtime, 30-case approval, staged-composition and overlay negative-control tests on Python 3.13 and 3.14.

## Exact byte evidence

- JEPA recovery builder SHA-256: `f87b63bbbb89f28718d627897d4e5495838f6e1ea2884ccd68239003e749a6b5`.
- Combined Core stage-builder SHA-256: `2c22cdf1ab97e506a2d1f2f5544d59a60de8556c28f6115d3c81a1b5b53e8b07`.
- Runtime deployer SHA-256: `e5c865c04d74283b72354c3421c6c87195aa67c68a6c1083aeb8bf15f2fa4a0a`.
- Canonical operator Git blob: `8d59efa1bfb7dea7bbb2fd1af2cf7d2e25adebc4`.
- Approval module Git blob: `c52c4d5bf21b34ab691eb6633504b67254bdf098`.
- Staged overlay Git blob: `bc2c39a61d55996278c6fe3adbeff357ba69d455`.
- The prior #2454 head failed its stage/optimizer-resume/Lab-Age/migration consumers because the stage builder expected recovery SHA `6b3a9508...` while the actual recovery builder was `f87b63...`. This branch changes Core-owned stage/deployer pins without weakening the hash gates.

## Tests and boundaries

- Exact-head CI: PENDING at handoff creation; no PASS is claimed for this rebased stacked branch yet. The previous stacked head #2456 surfaced an upstream `integrated_context_recall_candidate_20261111.py` pin failure (expected feedback-builder SHA `b31db610...`, actual SHA `f38943b3...`); this is owned by the JEPA/Memory/Boss source chain and is not changed here.
- Full local Aii checkout/tests: NOT_RUN / BLOCKED (no mounted repository checkout; local GitHub DNS unavailable).
- Standalone #2451 CI is prior-branch evidence only, not a test of this combined branch.
- Redmi: REDMI_UNVERIFIED. No probe, Termux command, update request, APK install, model/weight/permission/data change.
- Release: NOT_RELEASED. This branch is a stacked integration candidate, not a device deployment.
- No trained cross-organ latent transfer or receiver utility is claimed.

## Upstream dependency blocker

The current #2454 base head `bf2913b150d8decbf6e33c43920d21acc83439b3` has a separate failing staged Lab-Age consumer: `integrated_context_recall_candidate_20261111.py` expects `integrated_feedback_bootstrap_candidate_20261111.py` SHA-256 `b31db610f41bd8957991a140f8e3c3faa9a3b9b30c2e58dda87756005eca84eb`, while the current file readback hashes to `f38943b318938f53bd8bce6e279d41627907b87c6a67842b2322a7f7a89320e7`. CI run `45243007960` fails at that upstream check. Core did not edit the JEPA/Memory/Boss-owned context-recall file; its owner must rebind the chain before the full staged suite can pass.

## Next

1. Run exact-head CI for this combined branch and repair any observed stage, migration, operator, native receiver or JEPA regressions.
2. Boss/QA review the dependency chain in order: #2443 -> #2454 -> this Core stack.
3. Only after reviewed release integration and a separate authenticated install receipt should a distinct user decision be requested for any one-shot Redmi native probe. Production B3 stays OFF until held-out utility and all parity/zero/shuffle/OOD controls pass.

User action: none.


## Run 3 — exact operator-to-native-receiver integration (2026-11-24)

- Reproduced the current branch's workflow dispatch defect: the workflow push list included run1 but omitted this exact run2 branch. Exact-head GitHub runs ended at startup_failure with zero jobs; no compile/test/native build had executed.
- Added this branch to the workflow push filter so the Python staged-runtime suite, pinned Linux llama.cpp receiver build/selftest, and Android arm64 cross-compile can execute on this branch.
- Added a staged-runtime operator E2E regression. It keeps the real staged Cognition.native_receive and :callosum arm-probe → :callosum native-probe approval/lease path; only the final C++ process boundary is replaced by a deterministic receipt. It verifies exact source/event/generation, sender tap IDs/vectors, model hashes/revisions, position IDs, receiver dimensions, persisted LatentReceiverPacket, native-input-effect metrics, and zero production/training authority.
- Direct source-tree invocation skips this one test because native_receive is intentionally installed by the verified stage composer; the existing stage integration test reruns it against the composed Runtime. This avoids pretending the uncomposed source tree already contains the method.
- LOCAL_LINUX full Aii checkout: BLOCKED (no checkout mounted; git ls-remote cannot resolve github.com). The exact branch workflow is the executable verification path; results remain pending until GitHub readback.
- Native receiver scope remains diagnostic only: llama_batch.embd consumption is measured; no trained cross-model alignment, semantic usefulness, production B3 routing, weight learning, or Redmi behavior is claimed.
- Next: read back exact-head Python/Linux/Android workflow results, fix any real failures, then coordinate integration with the current JEPA base and Boss source-lifecycle branch. Redmi remains REDMI_UNVERIFIED.
