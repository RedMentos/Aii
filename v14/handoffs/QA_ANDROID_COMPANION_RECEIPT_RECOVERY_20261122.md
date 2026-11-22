# QA Android companion claimed-action receipt recovery

Date: 2026-11-22  
Owner: QA & Android  
Candidate branch: qa/v14-companion-receipt-only-recovery-20261122-run12  
Base: core/v14-android-companion-native-20261121 at 24e059d1f54e54d2285c9a542df207372fb27f4a

## Defect

A one-shot Android action is first durably claimed as EXECUTING or DENYING. The prior Activity finalizer removed the approval notification in finally, even if Android Keystore signing or the SQLite finish update failed. The action could then remain claimed without a receipt: outcome() returned NOT_READY, pending() could not show it, and the user could not retry finalization. Re-dispatch is unsafe because the launch may already have happened.

## Change

- Added an atomic finishClaimed update guarded by the original claimed state and receipt_json IS NULL; added a read-only query for claimed rows needing recovery.
- Added a shared receipt factory that revalidates action ID, package, canonical digest, capability and consent boundary before signing.
- Recovery is receipt-only and idempotent. EXECUTING becomes signed OUTCOME_UNKNOWN (approved locally, dispatch result not asserted); DENYING becomes signed USER_DENIED. It never invokes the launch intent.
- Provider startup, outcome(), pending() and reopening the consent Activity retry recovery. The notification is cancelled only after a durable receipt exists. Finalization and recovery share the action gate to prevent the normal result and conservative recovery racing each other.
- Python's pinned ECDSA verifier and source-bound ActionOutcome consumer accept COMPANION_OUTCOME_UNKNOWN as a non-observed, non-authoritative outcome. No T8/World learning authority is granted.

## Verification plan and boundaries

- Android Gradle/Robolectric tests cover execution and denial recovery, retry after injected Keystore failure, notification retention, process/database reopen, concurrency, request-scope rejection and exact receipt fields.
- Python 3.13/3.14 companion-outcome workflow covers signature verification and persistence of COMPANION_OUTCOME_UNKNOWN.
- No local Android SDK/Gradle or full Aii checkout is present in this run; exact GitHub CI is required. No APK install, Android permission, companion launch, Redmi action, Termux mutation, model/weight change or device deployment is claimed.
- The change does not enable UI observation, Accessibility, tap/type, shell, network or AudioRecord. Companion remains default-OFF; a signed receipt is not proof that the app reached foreground and never authorizes learning.

Status at authoring: candidate / CI not yet observed / NOT_RELEASED / REDMI_UNVERIFIED.


## QA follow-up — uncertain Android framework dispatch result (2026-11-22)

**Defect:** after an action is durably claimed, the old claimAndDispatch() mapped every RuntimeException from the dispatch callback to FAILED_TO_DISPATCH. An exception from startActivity() is not proof that Android did not cross the ActivityManager/framework boundary. Reporting definite failure could therefore misstate an action that may already have launched.

**Code at exact branch head 9cccde3896760ff7e03797484e43693384d52f07:**
- CompanionProvider.DispatchNotAttemptedException is reserved for the provably pre-dispatch case (the package has no launch intent).
- That explicit case remains FAILED_TO_DISPATCH.
- Any other runtime exception after the dispatch callback begins becomes OUTCOME_UNKNOWN; the action is never retried.
- receiptStatusForDispatchResult() centralizes the signed receipt mapping; unknown/unexpected results remain OUTCOME_UNKNOWN.
- ConsentActivity signs the mapped status against the already-claimed row.
- Added regressions for an exception after dispatch was attempted, missing launch intent without external dispatch, and all receipt-status mappings.

**Exact-head CI — all four workflows SUCCESS:**
- V14 Android companion run [45032673479](https://github.com/RedMentos/Aii/actions/runs/45032673479): :app:assembleDebug and :app:testDebugUnitTest PASS.
- V14 core companion outcome run [45032673542](https://github.com/RedMentos/Aii/actions/runs/45032673542): Python 3.13 and 3.14 each **51 passed**.
- Android outcome contract run [45032673558](https://github.com/RedMentos/Aii/actions/runs/45032673558): **3 passed**.
- Staged/integrated run [45032673482](https://github.com/RedMentos/Aii/actions/runs/45032673482): staged-runtime **240 passed / 10 skipped / 47 subtests**, ContextOS recall **15 passed**, migration suite **42 passed / 37 subtests**, integrated regression **415 passed / 3 skipped / 58 subtests**.
- Migration boundary: both simulated checkouts fast-forwarded to the candidate, but the legacy plain-UI recovery profile intentionally fails closed with “Pinned plain UI recovery builder changed”; the migration suite's PASS confirms refusal, **not** successful legacy runtime activation.

**Current real-phone boundary (private owner-read, no mutation):**
- PIPELINE_STATUS #567: auto-update enabled; runtime/dashboard UP_TO_DATE; last_error NONE; installed commit c4eb82deec915f65894c20d6ebbaf0ebf58fa335.
- DIAGNOSTICS #568: last turn **57.74 s**, TTFT **41.63 s**, prefill **38.95 s**, 751 prompt tokens, 2 generated tokens; B1_DETAIL and B2_GIST both TIME_BUDGET (53.2 s / 54.2 s). The instantaneous process map reports 4 small process entries but only 0.3 MiB total PSS, so it does not establish that the GGUF weights were resident.
- The companion PR is not installed on the phone. No APK installation, launch, UI action, permission request, model/weight change, user-data change or new CHAT_SEND occurred.

**Integration status:** PR #2347 remains stacked on draft Core PR #2271 at base 24e059d1f54e54d2285c9a542df207372fb27f4a. Exact candidate CI is green and this QA slice is ready for Core/Boss review on the companion stack, but it is **NOT_RELEASED** and **REDMI_UNVERIFIED**. Do not merge it directly to the release branch or infer Android behavior from Robolectric/CI.
