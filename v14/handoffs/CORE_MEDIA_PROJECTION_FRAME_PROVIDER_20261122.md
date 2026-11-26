# Core handoff — one-shot Android MediaProjection frame provider

Date: 2026-11-22  
Owner: Core & Harness  
Package: V14-009 / Android screen-observation provider  
PR: [#2379](https://github.com/RedMentos/Aii/pull/2379) — DRAFT, stacked on QA PR #2356  
Branch: `core/v14-media-projection-frame-provider-20261122`  
Latest code SHA: `ff271b1def8ee1469c4e838abad66a1e43f9375e`

## Product behavior and current code

- The companion exposes a user-visible one-shot Capture screen frame action.
- Each capture requires Android MediaProjection system consent; the service captures the default display once and stops projection.
- JPEG is bounded to 4 MP / 8 MiB and held in process memory for at most 20 seconds. The signed P-256 receipt binds exact bytes/hash/dimensions, source/session IDs, capture scope/method, API level, monotonic interval and expiry; action, learning and raw-persistence authority remain false.
- Termux can read only the fixed paired ContentProvider URI, once, with a bounded byte read and signature/hash verification.
- The consumed frame now moves into a registered `FrameReadLease`, rather than an untracked raw byte array. Stop/discard/expiry/provider restart clear active leases, close both pipe ends, zeroize the same byte buffer and remove the lease.
- Pipe consumption, registration and the companion stop switch share `ACTION_GATE_LOCK`; the stop-vs-openFile race now has a 16-iteration concurrent regression.
- The writer thread is terminal on reader disconnect or revocation. It is daemonized, closes its output and zeroizes the buffer on completion; the lease remains registered until stop/expiry so already-buffered kernel-pipe bytes can still be discarded.
- The Core Runtime adapter now calls Perception's three-argument provider-verifier factory with the exact `UIObservationLease`, observation and verifier callback. It marks the grant consumed at entry and zeroizes the mutable frame buffer on every exit, including stale/foreign lease and verifier-factory rejection.
- The source branch still lacks the newer A5 lease/RAW EYE modules because this PR is based on QA companion branch #2356, while Perception PR #2375 is based on the newer release base. The current test proves the Core verifier-call contract with an exact lease object; the real A5 lease + Perception consumer integration remains blocked until Boss provides a combined accepted base.

## QA findings addressed

1. The earlier receipt assertion mismatch was already corrected in the current branch.
2. QA's P1 consumed-buffer gap is addressed with `FrameReadLease`, active lease tracking, stop/discard/expiry revocation, pipe-end closure and zeroization.
3. QA's stop-vs-openFile race is addressed by rechecking the enabled state and registering the pipe under the same `ACTION_GATE_LOCK` used by stop/enable.
4. QA's Perception factory signature mismatch is corrected to `_issue_provider_frame_verifier(self.lease, self.observation, self.bundle["verify_frame"])`.
5. Python regressions verify exact lease forwarding, stale/foreign lease rejection, one-shot consumption and zeroization on all exits.

## Exact validation

| Environment | Test | Result |
|---|---|---|
| LOCAL_LINUX / JDK 21 with `javac --release 17` | Isolated `FrameReadLease` compile + blocked-writer close/zeroization smoke | PASS |
| LOCAL_LINUX | Full Aii Gradle/Robolectric suite | BLOCKED — no Gradle command or Android SDK in this worker |
| LOCAL_LINUX | Full repository Python/staged tests | BLOCKED — no full checkout; `git ls-remote` previously failed DNS |
| GitHub Actions | Exact head Android MediaProjection workflow | QUEUED — [45076824779](https://github.com/RedMentos/Aii/actions/runs/45076824779) |
| GitHub Actions | Exact head staged/integrated regression | QUEUED — [45076824754](https://github.com/RedMentos/Aii/actions/runs/45076824754) |
| GitHub Actions | Exact head private-bridge regression | QUEUED — [45076819948](https://github.com/RedMentos/Aii/actions/runs/45076819948) |
| GitHub readback | Core code files | PASS — exact current branch blobs read back |
| TERMUX/REDMI | APK install, MediaProjection dialog, real frame delivery, lifecycle and memory | REDMI_UNVERIFIED; no device session or capture was performed |

Queued CI is not PASS. The local JDK smoke is only the pure-Java lease helper with a stub Store; it is not Android PFD or Robolectric proof.

## Dependencies, risks and next actions

1. Poll exact-head Android and staged CI; fix only observed failures.
2. QA should independently review the new pipe lease, close semantics, stop-race test and negative gates.
3. Boss must combine the accepted QA companion base with the newer release/A5 lease base and Perception #2375 before claiming a real A5 frame-to-RAW-EYE integration. The current Core branch still fails closed when Perception is absent.
4. After the combined base is available, add a real `A5UIRuntimeAdapter.lease` + `ProviderFrameVerifier` integration test and verify the same lease/generation reaches C3.
5. Only after exact CI, Boss integration and explicit Android OS consent may QA run on Redmi. No update request or native capture was sent.

## Safety and non-claims

- This is a one-shot screen-frame provider, not continuous recording or arbitrary app control.
- No Android permission prompt was bypassed; no MediaProjection capture was performed.
- No raw screenshot, action, learning or truth authority is granted.
- No end-to-end visual reasoning or C3 consumption is yet proven.
- No model/weight change, remote shell, installed runtime update or device mutation occurred.
- PR #2379 is DRAFT / NOT_RELEASED; GitHub push is not deployment.
