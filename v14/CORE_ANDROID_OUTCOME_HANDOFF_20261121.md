# Core & Harness — Android action/outcome handoff (2026-11-21)

## Checkpoint

- Work branch: `gpt6/v14-core-companion-outcome-20261121`
- Current branch HEAD at this checkpoint: `25c7f35ad3d88f13d50f32bb0dc2e6c2e7893b00` (latest code test update); earlier handoff commits: `67f1fd07a9d2377a2bc06d992325db94c80064ac`, `a95b7bfb9f7ba74bd34cbbc15e64fead0c0edb7d`
- Stacked dependency: draft PR #2119, branch `gpt6/v14-core-companion-receipt-20261120`, head `6622218640c6859a628d96d7b63e3625ac46ba28`
- Integration base observed: `gpt6/v13-private-remote-bridge-20261111` at `14d7386484dfce6728aa404d89eae98403b4dba0`
- This is a review candidate, not a release or a device deployment.

## Implemented in this candidate

1. Uses the existing canonical `ActionOutcome` packet schema with a strict C5 companion subtype payload. The adapter rejects `observed=true`, T8 authority, World-learning eligibility, unsupported capabilities/status, and malformed action/digest/nonce values. The pinned global `contracts.py` source is restored byte-for-byte; no new global schema or migration was introduced.
2. The receipt verifier can defer nonce consumption for the C5 path. The C5 consumer verifies the receipt, then commits the nonce and typed outcome packet in one `Store.tx()` transaction.
3. Persistence is idempotent for the same action/nonce/digest across retry or Store restart. A reused nonce for another action, or a different receipt for an existing action, is rejected.
4. Adds a combined authenticate → persist → notify consumer function. It does not call Android APIs and does not create a WorldAction/T8 transition.
5. Adds real `Store`-backed tests for packet persistence, replay across two actions, restart idempotency and authority-negative controls; protocol tests retain the default durable replay behavior.

## Evidence and limits

- LOCAL_LINUX: isolated SQLite transaction/concurrency reproduction PASS — one packet committed, one cross-action nonce replay rejected. This was a small algorithm reproduction, not execution of the exact repository checkout.
- Exact PR workflow on the first PR merge commit: compile PASS; adapter pytest 20 passed / 3 failed because test fixtures used non-hex nonce characters (`g`–`j`). Those fixtures were corrected to valid hex on the newer head `29133ebb`; exact-head rerun is PENDING.
- The first staged/integrated regression run failed because the initial patch changed pinned `v13/code/v13/contracts.py`; 17 tests hit the expected arithmetic source-pin guard, plus two migration assertions returned `PARTIAL` instead of `UPDATED`. The global contracts file was restored exactly to the dependency branch blob `7b21d9c5076015716851b5d432a5730e4e17da92`. Re-run required; the two migration assertions remain separately unclassified until the rerun.
- GitHub checkout in the local container: BLOCKED; `git ls-remote` failed with DNS resolution for `github.com`. Do not report the exact branch as locally tested.
- CI for the stacked dependency PR #2119: V14 receipt workflow passed; its separate additive-only scope gate failed because that PR adds a workflow file outside the gate's allowed inert-module/test/handoff paths. On PR #2134's first merge commit, the V13 Android broker, V13 sandbox replay, V14 receipt verifier and V13 Android outcome-contract workflows passed; the V14 Core outcome adapter workflow failed only on the invalid hex test fixtures described above. The V13 staged/integrated regression workflow failed on the temporary pin mismatch described above.
- Android companion app/service, Android Keystore key custody, OS permission prompts, live transport, real Android execution and Redmi receipt: NOT IMPLEMENTED / REDMI_UNVERIFIED.
- HMAC test secret is supplied to the Python verifier; `key_storage_status=UNVERIFIED`. This is not an independent OS security boundary and cannot authorize T8 learning.
- No production model, weights, Age, user permissions, Termux installation, database or device state was changed.

## Next executable step

1. PR #2134 is open as a stacked draft against #2119. Recheck exact-head Actions after the hex-fixture correction and exact restoration of `contracts.py`; the existing V13 broker workflow now also includes a real-Store receipt test.
2. Fix remaining exact-head failures and request independent Core/QA review. Do not merge or call this native Android functionality.
3. Next native package: a separately installed Android companion with a user-visible per-action consent UI, OS API permission checks and Android Keystore-backed asymmetric signing; the Python runtime should hold only a pinned public key. Verify the actual API/security behavior for Android 13 before implementation. Keep the executor OFF until the user explicitly authorizes installation and device testing.
4. Only after native receipts are independently verified should a separate reviewed consumer map observed outcomes into trusted T8 transitions.

## User action

None for repository continuation. No Termux command, model download, permission change or phone update is requested.
