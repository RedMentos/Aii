# QA & Android — whole-Canon checkpoint, run 13 (2026-11-22)

## Scope and base

- Repository: RedMentos/Aii.
- Release-development branch: gpt6/v13-private-remote-bridge-20261111.
- Exact installed/release-development base: c4eb82deec915f65894c20d6ebbaf0ebf58fa335.
- This checkpoint preserves the full V14 master and 1,255-heading historical Canon inventory. It does not change master bytes or the Boss-owned Work Board.

## Verified device facts

- Private PIPELINE_STATUS #574: c4eb82 installed, auto-update enabled, runtime/dashboard UP_TO_DATE, last_error NONE.
- Private DIAGNOSTICS #575: last stored turn FINAL, 57.739 s total, 41.627 s TTFT, 38.945 s prefill, 751 admitted prompt tokens, 2 generated tokens. No new turn was sent; answer correctness remains UNKNOWN.
- B1/B2 probes TIME_BUDGET 53.2/54.2 s; C3 probe 3.1 s; native probe SMOKE_PARTIAL.
- Instant native process sample: 4 mapped processes, 0.3 MiB PSS / 2.9 MiB RSS. Not sustained weight residency or free RAM.
- HEALTH #576: 1,352 MiB MemAvailable / 5,569 MiB total, 1,567 MiB disk free, but runtime UNAVAILABLE in this snapshot while DIAGNOSTICS says RUNNING. Keep discrepancy explicit.
- Official Age 0, lab request 10/effective 5, physical feature execution false, learning commit authority requires SHADOW.
- Exact c4eb82 commit check-runs: 49/49 SUCCESS. This is not a post-merge push-CI receipt.

## QA code change

PR #2347 head 955cb4b3c37f2c054bd0fc4d6e26177e2d41a365 adds startup/pending-path reconciliation for stale approval notifications after a durable terminal receipt. It serializes against submit/dispatch, preserves valid pending approvals, ignores unrelated channels/malformed tags, fails closed on Store/notification query errors, and never redispatches. Regression simulates durable OUTCOME_UNKNOWN + still-active notification, preserves a second live approval, and proves idempotence.

Exact-head CI at the last read: 4/5 SUCCESS (Android Gradle/Robolectric, companion outcome 3.13/3.14, Android outcome contract, offline bridge security); staged/integrated regression still running. This is a stacked draft-companion PR, not installed or released. Local Android SDK/Gradle unavailable.

## Other current QA evidence

- PR #2342 pairing persistence: exact head 24b8f9760939eccea6e877536027101204fe04f8, 2/2 exact CI SUCCESS; separate stacked companion leaf, no APK/device proof.
- PR #2343 fair-budget integration: exact head 55b76c4c79b24b5ac674366d6bcb32aa15ab1f9d, still blocked by staged builder/source pin and consumer failures. No device update.
- JEPA PR #2345 receiver code is in the Boss candidate; prompt-level numeric SHADOW only, B2 default false, not trained latent transfer or live weight learning.
- B3 PR #2346 remains draft with a reported symlink output-path escape; no production B3 acceptance.

## P1 source-forget / weight-promotion race

Code inspection of exact #2343 head shows:

1. Memory._forget_source reads updates and active generation before acquiring source_forget_guard.
2. Store.switch_generation pre-reads the pending update and validates its artifact before its final transaction.
3. The final transaction checks the active generation but does not re-read update status/path/hash/manifest or confirm all manifest source_ids remain live.

A concurrent forget can therefore tombstone a source, quarantine the update and remove its artifact after promotion preflight but before promotion commits. This is a code-derived interleaving, not a locally executed reproduction.

Required order: WorldJEPA file lock → Store RLock/SQLite transaction. Move forget's update/generation checks inside the guard and Store lock; serialize promotion's full preflight/commit under the same Store lock; re-read update state and source liveness inside the final transaction; add barrier tests for both interleavings and a no-deadlock test. Adjacent: replace symlink-check-then-open in WorldJEPA _locked with O_NOFOLLOW + fstat regular-file validation.

Details: https://github.com/RedMentos/Aii/pull/2343#issuecomment-7081633818

## Environment / limits

- No local Aii checkout, Android SDK or Gradle in the execution container; full local Linux/Android suite BLOCKED / NOT_RUN.
- No APK install, companion pairing, Android UI action, microphone capture, UPDATE_REQUEST, CHAT_SEND, LOG_PAGE, model/weight swap, permission change or device mutation occurred.
- No transcript or raw console excerpt was copied into public evidence.

## Next actions

1. Finish #2347 exact-head staged/integrated CI; hand to Core/Boss only if green.
2. Boss clears #2343 source-pin failures and P1 source-forget/promotion race before any learning or unlearning acceptance.
3. Continue whole-Canon acceptance: correct native chat, B1/B2 OfferPacket delivery/consumption, B3 latent utility, persistent weight/retention/rollback, voice, Android UI/background control, restart/update recovery and semantic coverage.
4. User action: none. Existing updater is already at c4eb82; candidate branches are not releasable.
