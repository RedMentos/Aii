# Core & Harness — Android action/outcome handoff (2026-11-21)

## Checkpoint

- Work branch: `gpt6/v14-core-companion-outcome-20261121`
- Latest verified branch HEAD at handoff creation: `11e88d224523b0f84550fa2ee0439afcaf58ceff`
- Stacked dependency: draft PR #2119, branch `gpt6/v14-core-companion-receipt-20261120`, head `6622218640c6859a628d96d7b63e3625ac46ba28`
- Integration base observed: `gpt6/v13-private-remote-bridge-20261111` at `14d7386484dfce6728aa404d89eae98403b4dba0`
- This is a review candidate, not a release or a device deployment.

## Implemented in this candidate

1. Adds a typed `AndroidActionOutcome` packet schema with strict fixed status, source-independent non-authority, action/capability, digest and nonce validation. A packet cannot claim `observed=true`, T8 authority, or World-learning eligibility.
2. The receipt verifier can defer nonce consumption for the C5 path. The C5 consumer verifies the receipt, then commits the nonce and typed outcome packet in one `Store.tx()` transaction.
3. Persistence is idempotent for the same action/nonce/digest across retry or Store restart. A reused nonce for another action, or a different receipt for an existing action, is rejected.
4. Adds a combined authenticate → persist → notify consumer function. It does not call Android APIs and does not create a WorldAction/T8 transition.
5. Adds real `Store`-backed tests for packet persistence, replay across two actions, restart idempotency and authority-negative controls; protocol tests retain the default durable replay behavior.

## Evidence and limits

- LOCAL_LINUX: isolated SQLite transaction/concurrency reproduction PASS — one packet committed, one cross-action nonce replay rejected. This was a small algorithm reproduction, not execution of the exact repository checkout.
- Exact repository compile/pytest: PENDING the PR-specific GitHub Actions run.
- GitHub checkout in the local container: BLOCKED; `git ls-remote` failed with DNS resolution for `github.com`. Do not report the exact branch as locally tested.
- CI for the stacked dependency PR #2119: its V14 receipt workflow passed; its separate additive-only scope gate failed because that PR adds a workflow file outside the gate's allowed inert-module/test/handoff paths. That failure is a scope-policy result, not proof of receipt-runtime integration.
- Android companion app/service, Android Keystore key custody, OS permission prompts, live transport, real Android execution and Redmi receipt: NOT IMPLEMENTED / REDMI_UNVERIFIED.
- HMAC test secret is supplied to the Python verifier; `key_storage_status=UNVERIFIED`. This is not an independent OS security boundary and cannot authorize T8 learning.
- No production model, weights, Age, user permissions, Termux installation, database or device state was changed.

## Next executable step

1. Open a stacked draft PR against #2119's branch and run the exact workflow `.github/workflows/v14-core-companion-outcome.yml` (compile + existing Android-control/outcome tests + new real-Store tests).
2. Fix any exact-head failure and request independent Core/QA review. Do not merge or call this native Android functionality.
3. Next native package: a separately installed Android companion with a user-visible per-action consent UI, OS API permission checks and Android Keystore-backed asymmetric signing; the Python runtime should hold only a pinned public key. Verify the actual API/security behavior for Android 13 before implementation. Keep the executor OFF until the user explicitly authorizes installation and device testing.
4. Only after native receipts are independently verified should a separate reviewed consumer map observed outcomes into trusted T8 transitions.

## User action

None for repository continuation. No Termux command, model download, permission change or phone update is requested.
