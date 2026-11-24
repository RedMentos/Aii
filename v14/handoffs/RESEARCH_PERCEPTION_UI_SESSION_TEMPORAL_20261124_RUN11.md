# Research & Perception handoff — session-scoped RAW EYE temporal lineage

**Date:** 2026-11-24  
**Owner:** Research & Perception  
**Branch:** `research-perception/v14-ui-session-temporal-20261124-run11`  
**Base:** Perception PR #2463 branch `research-perception/v14-vision-current-20261124-run33`, base head `18b27e1d639c14f1007d26ecf5c8ebd0b3f71997`  
**Current branch head at handoff:** `b587c68dd71b2c40657c076aecde115146b5758a`  
**Epic:** #1984. This is a follow-up to #2463, not a release or a claim that the Android provider already emits multi-frame receipts.

## Functional change

The previous A5 temporal registry keyed history by `(capture_session_id, generation_id, consent_receipt_ref)`. That was correct for the existing one-shot provider, but it discarded temporal history whenever a provider rotated its per-frame receipt inside one still-authorized screen-capture session.

This branch adds optional `session_consent_receipt_ref` as a distinct stable authority lineage:

- Each frame retains its own `consent_receipt_ref`, source ID, digest and one-shot `UIObservationLease`.
- A stable `session_consent_receipt_ref` can span multiple frame receipts within the same capture session and brain generation.
- `TemporalVisualEvidenceRegistry` keys history by the stable session receipt when present. A changed session receipt, generation or capture session resets the history.
- Legacy observations without the new field continue to key by their per-frame receipt; existing one-shot behavior is preserved.
- The session receipt is bound into the observation lease, one-shot provider verifier, temporal evidence packet and A5 `PerceptPacket`.
- `temporal_visual_revocation_callback` is now explicitly documented as a **session-end** callback. It must not be attached to every per-frame lease when the capture session continues; final-frame `end_of_stream=True` remains another cleanup path.

No frame bytes or raw UI content are persisted. The feature changes only bounded process-local numeric temporal history and source-bound diagnostic metadata. It grants no truth, action or learning authority.

## Tests added

- Provider verifier rejects a forged/changed session receipt and malformed session receipt.
- Two different frame source IDs and per-frame receipts, each with its own lease, preserve A5 temporal history only when the session receipt remains stable.
- Changing the session-level receipt forces a fresh WARMUP.
- Existing legacy test still proves that a changed per-frame receipt without a session receipt resets history.

## Evidence boundary

- **LOCAL_LINUX isolated registry contract test:** PASS. It exercised stable-session receipt continuity, session-receipt reset, legacy receipt reset and explicit cleanup using a minimal state stub. This is not the full project test suite.
- **Full repository pytest / integration:** NOT_RUN locally. No local Aii checkout is mounted; GitHub raw-host DNS resolution failed. Exact project CI is still required.
- **CI:** pending PR creation / exact-head workflow results.
- **Android/Redmi:** REDMI_UNVERIFIED. No live MediaProjection provider, phone, or device receipt was available in this run.
- **Native model/weights:** no native inference or weight update was attempted or claimed.
- **Deployment:** NOT_RELEASED. No updater or installed model/data/permission was touched.

## Required integration from Core / QA

The Android companion provider must add the stable session receipt to the signed observation and have its provider verifier authenticate that field for every frame. It should continue issuing a distinct one-shot frame receipt and digest per frame. A bounded two-frame queue can then use separate frame leases while preserving the stable session lineage. QA must test cancellation, session stop, frame receipt rotation, changed session receipt, and restart/cleanup on the actual Android API/device.

Until that provider change is merged and verified, the current provider remains one-shot and will use the backward-compatible per-frame receipt fallback. This branch is a Perception-side interface capability, not proof of Android multi-frame capture.

## Next action

Core owns the Android provider and runtime composer. Rebind the provider's signed-observation verifier to the optional session receipt, connect the bounded frame queue, and run the exact staged/integrated A5 tests. Then obtain an authenticated Redmi session receipt before changing the device status from REDMI_UNVERIFIED. PR #2463 and Core PR #2465 still have their own staged-composer integration work; this follow-up must be composed with those changes rather than treated as an independent release.

## Run 12 — provider-side session receipt authentication contract (2026-11-24)

A contract audit found that the prior Run 11 change bound the optional stable session receipt into the Python lease, verifier object, temporal registry key and packet, but the provider's **current-grant check, linearizable guard and revocation subscription did not receive that receipt**. The field could therefore be syntactically valid and echoed into temporal history without the provider lifecycle callbacks being required to authenticate/revoke that exact session lineage.

The follow-up changes `a5_ui_admission_bridge.py` so:
- legacy one-shot observations without the optional field retain the original seven-argument consent callbacks and five-argument revocation subscription;
- when the stable session field is present, its exact value is appended to `consent_check` and `consent_guard` arguments and passed as `session_consent_receipt_ref=` to `revocation_subscribe`;
- unsupported providers fail closed before the lease is yielded.

Regression coverage verifies the session receipt reaches all three provider callbacks, a provider that lacks the new session-aware subscription is rejected, and legacy one-shot callback arity is unchanged.

**Scope boundary:** this strengthens the Perception-side provider contract. It does not implement the Android companion's signed session receipt, nor does it prove that the current Core provider has been updated to issue or authenticate it. Core/QA must implement the matching callback signature and signed-receipt validation before multi-frame MediaProjection is enabled.

**Local test status:** exact repository checkout unavailable in this environment; the focused project pytest is not claimed as locally run. Exact-source CI is required after this push. Redmi remains REDMI_UNVERIFIED; NOT_RELEASED; no updater/device/model/weight/permission/data action.
