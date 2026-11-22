# Core & Harness — Android action intent/outcome journal

**Date:** 2026-11-22  
**Owner:** Core & Harness  
**Branch:** `core/v14-android-action-journal-20261122`  
**Parent stack:** Core companion PR [#2271](https://github.com/RedMentos/Aii/pull/2271) → QA durability PR [#2342](https://github.com/RedMentos/Aii/pull/2342) → this PR  
**Base SHA:** `ab99ad94f25db2e5ce363045de4d175595bd2619`  
**Release base observed separately:** `gpt6/v13-private-remote-bridge-20261111` at `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`

## Connected code

- `:android launch <package> --confirm` now persists a typed, source-bound `ActionIntent` packet from `C5_ANDROID_COMPANION` with the action ID, capability and explicit operator-plus-companion approval contract.
- `:android history [1..50]` reads the current chat session's intent/outcome packets and the durable broker state. It does not contact Android, expose package names or source text, or combine unrelated sessions.
- A signed companion receipt appears as `COMPANION_ATTESTED_NOT_DEVICE_VERIFIED`; history preserves `observed=false`, `t8_authoritative=false` and `world_learning_eligible=false`. The journal is an audit/continuity path, not a learning promotion or a claim that the app reached foreground.
- The Python regression workflow now runs on this stacked branch and base for CPython 3.13/3.14.

## Tests and evidence

- **LOCAL_LINUX_ISOLATED / CPython 3.13.5:** PASS — independent SQLite reproduction of session scoping, intent/outcome join, privacy projection, bounded limits and negative T8 authority.
- **Full local Aii checkout:** BLOCKED — no repository checkout is mounted and `git ls-remote` fails DNS resolution for github.com. No full local pytest or exact-source compile is claimed.
- **Exact GitHub CI:** pending for this branch; workflow runs the existing companion, broker, ECDSA, transport, outcome and new runtime tests on Python 3.13 and 3.14.
- **Android / Termux / Redmi:** REDMI_UNVERIFIED. No APK install, pairing, capability enablement, app launch, screen observation, tap/type or device receipt was performed.
- No model, weights, Age, permissions, updater settings or user data were changed.

## Acceptance boundary and next step

This adds a real source-scoped C5 action journal on top of the existing permission-gated companion candidate. It does not implement an Android UI observer, a verified foreground transition, T8 learning eligibility, B3 latent coupling or a release. Keep this PR stacked until QA #2342 and Core #2271 are reviewed and Boss rebases the companion stack onto the current release-development head. Any Redmi exercise requires the already separate explicit device-side approval and a fresh authenticated receipt; do not send a manual Termux command or update request from this PR.
