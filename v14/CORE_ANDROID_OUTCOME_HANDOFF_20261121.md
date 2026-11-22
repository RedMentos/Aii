# Core & Harness — Android action/outcome handoff (2026-11-21)

## Checkpoint

- Work branch: `gpt6/v14-core-companion-outcome-20261121`
- Current branch HEAD at this checkpoint: `10d88d74ebd353c342a7a8e5f58c8a437a1495e1` (latest code test update); earlier handoff commits: `67f1fd07a9d2377a2bc06d992325db94c80064ac`, `a95b7bfb9f7ba74bd34cbbc15e64fead0c0edb7d`
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
- The first staged/integrated regression run failed because the initial patch changed pinned `v13/code/v13/contracts.py`; 17 tests hit the expected arithmetic source-pin guard, plus two migration assertions returned `PARTIAL` instead of `UPDATED`. The global contracts file was restored exactly to the dependency branch blob `7b21d9c5076015716851b5d432a5730e4e17da92`. A later staged-runtime job passed after restoration; the integrated-regression job was still running at the previous checkpoint. Latest exact-head rerun is queued; the two earlier migration assertions remain separately unclassified.
- GitHub checkout in the local container: BLOCKED; `git ls-remote` failed with DNS resolution for `github.com`. Do not report the exact branch as locally tested.
- CI for the stacked dependency PR #2119: V14 receipt workflow passed; its separate additive-only scope gate failed because that PR adds a workflow file outside the gate's allowed inert-module/test/handoff paths. On PR #2134's first merge commit, the V13 Android broker, V13 sandbox replay, V14 receipt verifier and V13 Android outcome-contract workflows passed; the V14 Core outcome adapter workflow failed only on the invalid hex test fixtures described above. The V13 staged/integrated regression workflow failed on the temporary pin mismatch described above.
- Android companion app/service, Android Keystore key custody, OS permission prompts, live transport, real Android execution and Redmi receipt: NOT IMPLEMENTED / REDMI_UNVERIFIED.
- HMAC test secret is supplied to the Python verifier; `key_storage_status=UNVERIFIED`. The `confirmed_by_local_ui=True` flag is a caller assertion, not authenticated consent. The stored receipt labels `android_os_permission_status=REQUIRED_NOT_VERIFIED` and `observed=false`. This is not an independent OS security boundary and cannot authorize T8 learning.
- No production model, weights, Age, user permissions, Termux installation, database or device state was changed.

## Next executable step

1. PR #2134 is open as a stacked draft against #2119. Recheck exact-head Actions after the hex-fixture correction and exact restoration of `contracts.py`; the existing V13 broker workflow now also includes a real-Store receipt test.
2. Fix remaining exact-head failures and request independent Core/QA review. Do not merge or call this native Android functionality.
3. Next native package: a separately installed Android companion with a user-visible per-action consent UI, OS API permission checks and Android Keystore-backed asymmetric signing; the Python runtime should hold only a pinned public key. Verify the actual API/security behavior for Android 13 before implementation. Keep the executor OFF until the user explicitly authorizes installation and device testing.
4. Only after native receipts are independently verified should a separate reviewed consumer map observed outcomes into trusted T8 transitions.

## Android 13 native-design research (primary documentation; not device proof)

- Android Keystore documents EC key-pair generation in `AndroidKeyStore` and SHA-256 signing. The private key can remain non-exportable; hardware-backed/StrongBox availability is device-dependent. Initial candidate for the companion receipt is ECDSA P-256 + SHA-256, with runtime verification using only the pinned public key. Confirm key security level and user-authentication requirements on the actual Redmi before treating it as a boundary.
  - https://developer.android.com/privacy-and-security/keystore
  - https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec
- Android 12+ restricts starting foreground services from the background. Android 13's restricted battery state can prevent foreground services, alarms and jobs, and users can stop foreground-service apps from the Task Manager. Therefore the first executor should be user-initiated from a visible companion UI; do not assume an always-on invisible service.
  - https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
  - https://developer.android.com/about/versions/13/behavior-changes-all
- AccessibilityService is a separate, user-enabled fallback and requires an explicit service configuration; it is not a silent substitute for official APIs.
  - https://developer.android.com/guide/topics/ui/accessibility/views/service

## Shared coordination

- QA's draft PR #2132 owns the shared `V14_WORK_BOARD.json` and `V14_USER_NEXT_ACTION.md` edits. Core did not write those same files in parallel. A coordination comment was added to #2132 pointing to this handoff and asking the integrator to fold the verified Core status into the common board/next-action after review.
- PR #2134 is a draft stacked dependency on #2119; it is not merged or released.

## User action

None for repository continuation. No Termux command, model download, permission change or phone update is requested.


## 2026-11-21 follow-up — cross-event nonce replay closure

- Verified code SHA: `96edceec0836ad791b92dd385bdbaa2a8897b9f2`. Subsequent commits on this branch are handoff-only; `android_outcomes.py` and its regression test retain identical blob SHAs. Read PR #2134 for the current branch HEAD before resuming. The draft remains stacked on the companion-receipt branch and is **NOT RELEASED**.
- Fixed the test-file indentation defect that had prevented collection.
- Tightened `persist_companion_outcome`: replay detection now scans every persisted `C5_ANDROID_COMPANION/ANDROID_COMPANION_RECEIPT` ActionOutcome, not only rows for the same event. The same nonce is idempotent only for the same action ID, event ID and digest; otherwise it fails with `receipt nonce replay`. The uniqueness check and packet insert remain inside the same Store transaction.
- Added `test_nonce_replay_rejected_across_distinct_source_events`, covering reuse of one nonce on a different event/action.
- Exact-head CI on `96edceec`: PASS — V14 Core Android companion outcome adapter (run 44842779504), V13 Android outcome contract (44842779484), V14 companion receipt verifier (44842779554), V13 staged-context/integrated regression (44842779560), Android control broker isolated tests (44842779435), Android local sandbox replay integration (44842779590), and private-bridge tests (44842773164).
- Local Linux: PASS — isolated SQLite reproduction verified same-event idempotency and cross-event nonce rejection with one committed ActionOutcome. This was an isolated algorithm test, **not** the exact repository suite. Exact local checkout was unavailable in this session (no repository checkout; GitHub DNS resolution failed).
- Redmi/Termux: **REDMI_UNVERIFIED**. No owner-verified device receipt was returned for this run. No Android Keystore-backed signature, native companion transport, real device action, or C5→T8 Runtime execution is demonstrated. The current HMAC verifier and caller-asserted local-approval field are not OS permission proof.
- Next: independent review of the nonce transaction and migration behavior; integrate the prerequisite companion-receipt branch in order; then connect verified ActionOutcome to the actual Runtime/C5→T8 consumer without enabling any Android capability or action by default.
