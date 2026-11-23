# Core handoff — native receiver approval overlay stacked on JEPA runtime

Date: 2026-11-23
Owner: Core & Harness
Dependency: JEPA/Memory PR #2454, branch `jepa-memory/v14-temporal-boss-2443-rebase-20261123-run14`, exact base head `c56e1fab31cfd00346e82599ca2779ff4e8cce40`
Core branch: `core/v14-native-probe-jepa-stack-20261123-run1`

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

- Exact-head CI: PENDING at handoff creation; no PASS is claimed for this stacked branch yet.
- Full local Aii checkout/tests: NOT_RUN / BLOCKED (no mounted repository checkout; local GitHub DNS unavailable).
- Standalone #2451 CI is prior-branch evidence only, not a test of this combined branch.
- Redmi: REDMI_UNVERIFIED. No probe, Termux command, update request, APK install, model/weight/permission/data change.
- Release: NOT_RELEASED. This branch is a stacked integration candidate, not a device deployment.
- No trained cross-organ latent transfer or receiver utility is claimed.

## Next

1. Run exact-head CI for this combined branch and repair any observed stage, migration, operator, native receiver or JEPA regressions.
2. Boss/QA review the dependency chain in order: #2443 -> #2454 -> this Core stack.
3. Only after reviewed release integration and a separate authenticated install receipt should a distinct user decision be requested for any one-shot Redmi native probe. Production B3 stays OFF until held-out utility and all parity/zero/shuffle/OOD controls pass.

User action: none.
