# Research & Perception — Run 59 handoff (2026-11-27)

## Product bug found and fixed in the A5 visual frame branch

Branch: research-perception/v14-a5-visual-frame-bridge-20261127-run58
Parent chain: child of Core PR #2549; #2549 is based on Perception #2548.
Current code path: v13/code/v13/a5_visual_frame_bridge.py -> a4_visual_salience.py -> existing A4 Attention.perceive().

### Reproduction

When an already-installed hashed_bow student projector had captions, A5 emitted the base visual segment plus one or more student-hypothesis segments. Every segment correctly retained the same source_ref because they came from the same frame. A4 returned one row per segment, but apply_raw_eye_structure() searched by source_ref alone and required exactly one match. Therefore any non-empty student hypothesis set caused the entire visual ingest to raise ValueError: RAW-EYE source does not map to exactly one A4 row. The existing tests exercised projector ranking separately, not the combined ingest path.

### Code change

- a4_visual_salience.apply_raw_eye_structure(..., segment_index=0) now binds the RAW-EYE cue to the exact A4 row index and the matching source_ref, instead of assuming one row per source.
- After adding the structural contribution, it recomputes A4 normalized weights, suppression and high-resolution re-look ranking using the existing A4 constants. Previously these fields remained calculated from the pre-RAW-EYE scores.
- A5VisualFrameAdapter explicitly targets segment index 0, the base frame observation. Student captions remain separate STUDENT_ESTIMATE / REFERENCE_NOT_FACT rows and do not inherit the RAW-EYE structural cue.
- Added an integration regression that supplies one synthetic student candidate, verifies both A4 rows share the same source_ref, only the base row receives RAW-EYE, normalized weights sum to 1, and re-look ranking is consistent with the updated scores.

## Verification

- LOCAL_LINUX, CPython 3.13.5: isolated exact-helper reproduction of the old ambiguity — FAIL as expected; patched helper compile + duplicate-source selection + normalized-weight + re-look checks — PASS.
- Full local Aii checkout/pytest: BLOCKED / NOT_RUN. No repository checkout is mounted; git ls-remote fails because this environment cannot resolve github.com. The isolated helper check is not the full repository suite.
- GitHub Actions before this patch: PR #2550 head cb52515ffba625abf048bd66a7e3789a13ca1415 A5 workflow and staged/integrated regression both SUCCESS. Those results do not transfer to the new head.
- GitHub Actions after this patch: exact code/test head fca70db. A5 workflow 45943031921 PASS on Python 3.13 and 3.14: py_compile PASS and 11 passed / 3 subtests each. Shared staged/integrated workflow 45943031927 PASS: staged runtime 268 passed / 10 skipped / 48 subtests; integrated regression 424 passed / 3 skipped / 6 warnings / 58 subtests. These are hosted Linux CI results, not local hardware or Android proof.
- TERMUX/REDMI: REDMI_UNVERIFIED. No live MediaProjection provider, screen frame, Android service, microphone, model, weight, permission, updater or user-data operation was used.

## Real user effect and limits

This fixes the optional-student-projector branch of the synthetic Runtime-side A5 adapter: an available caption projector no longer makes an otherwise valid visual frame fail because several derived segments share one source. It does not make screen capture user-visible yet. The normal-turn Core callsite is still missing: current Core PR #2549 does not modify runtime.py or reference A5VisualFrameAdapter. Core must add that consumer; the provider still has to obtain explicit Android OS consent, hold the revocable lease, and map MediaProjection onStop() to cancellation and cleanup. No real Redmi screenshot or visual answer is claimed.

## Research / model boundary

R-179 records only an abstract-level review of Llama-Mobile (arXiv:2608.21134, 2026-08-21) plus the official repository and license readback. The reported 3.7-GB 11B vision checkpoint is not a fit for the Redmi 6-GB-class budget without a real memory profile; source is MIT, but weights are under the separate Llama 3.2 Community License. Nothing was downloaded or imported. Android's official MediaProjection reference (updated 2026-08-03) confirms explicit consent, foreground-service requirements and mandatory cleanup on onStop(); Android 14's additional ordering rule must not be misapplied to the Android 13 target.

## Next owner/action

1. Core: create or extend the normal-turn Runtime consumer for A5VisualFrameAdapter under the live UIObservationLease. Current Core #2549 changed-file list does not contain runtime.py or an A5 visual callsite; it is the current integration parent, not proof that the visual adapter is wired.
2. QA: test provider revocation during frame decode, context read, A4 admission and Runtime teardown; confirm cache cleanup and no stale consumer access.
3. Boss: reconcile the #2548 -> #2549 -> #2550 stack onto the current integration/release head after exact-head CI; do not equate merge with phone install.

Status: DRAFT / NOT_RELEASED / REDMI_UNVERIFIED. No user action required.


## Next Perception finding — A4 omission session-scope audit

A static code audit found a conditional cross-session false-positive risk in the existing A4 event expectation path:

- audio_event_expectation.py keys process-local expectation state by (source_id, generation_id) and resets it only when consent_scope_id (SHA-256 of the consent receipt) changes.
- audio_voice_cues.py passes source_id, generation_id and consent_scope_id but no session_id.
- The Store events table already contains session_id, and consume_pcm16_voice_window has event_id; Store.one can resolve the session without reading message text.
- Therefore, if the same source, generation and consent receipt are reused across two chat sessions in one Runtime process, expected intervals / expected_next_ms could carry over. This is a conditional risk, not a measured live false positive; the provider may already issue a new receipt per session.
- Existing event-expectation tests cover uncertain, low-confidence and late windows but not same-source/same-receipt session rotation.

Next test: seed a valid periodic pattern in session A, then use the same source/generation/receipt in session B; B must be WARMUP and produce no omission until it independently accumulates MIN_INTERVALS. Verify source revocation resets all session keys. Implementation must add session_id to the event registry key and consumer call, and Core must refresh the exact audio_event_expectation.py pin in integrated_audio_context_candidate_20261121.py before staged/integrated tests. Ledger R-180 records this as CODE_AUDIT_ONLY / OPEN, not a proven runtime bug.
