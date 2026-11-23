# Research & Perception run 2 — bounded multi-frame A5 packet history

Date: 2026-11-23  
Role: Research & Perception  
Repository: `RedMentos/Aii`  
Branch: `research-perception/v14-ui-temporal-attention-20261123-run1`  
PR: [#2414](https://github.com/RedMentos/Aii/pull/2414), stacked on Perception #2375  
Code checkpoint: `f14d09b5516c8ac99c06053ae3b2029bdfe26ef7`  
Release-development base observed before work: `aed1d2b826290c95c70356b5d8b864b5ef382be4`  
Release SHA: **NOT_RELEASED**

## Implemented function

The previous A5 UI packet cache used one `source_id` key, so each frame from the same consented source replaced the previous frame. That prevented a same-lease temporal sequence from reaching the active context consumer. Revocation also failed to clear the cache on the no-Store path and could leave entries behind if Store cleanup raised.

The new `A5UIRuntimeAdapter.cache_packet(packet, lease)`:

- validates the exact active `UIObservationLease`, Runtime event/generation and source binding;
- accepts only UI packets with raw/derived persistence false, action authority false, learning authority false and truth authority zero;
- stores packets by `(source_id, packet_id)`, retaining at most 8 packets per source and 64 globally;
- lets the existing `A5UIRuntimeAdapter.context()` return multiple FINAL frame packets from the same active lease;
- clears every legacy or multi-frame packet for a source on revoke, including when Store is absent or Store cleanup raises.

The existing public `consume_projected_frame_from_provider()` is still the per-frame ingress. Core can call it repeatedly once it provides a same-session stream and holds the same lease through downstream context/C3 use. The Perception cache stores only derived packet metadata/features, not raw image buffers.

## Verification

### LOCAL_LINUX

- Environment: CPython 3.13.5, Linux x86_64.
- Command: `python -m py_compile /tmp/test_ui_packet_cache.py && python /tmp/test_ui_packet_cache.py`.
- Result: **PASS, 4/4 isolated helper checks** — per-source cap, global cap, source-isolated revoke, legacy source-key cleanup, wrong-source and duplicate negatives.
- Full Aii checkout and repository-wide pytest/py_compile: **BLOCKED / NOT_RUN** because no checkout is mounted and GitHub DNS is unavailable in this container.

### Exact-head GitHub CI — code SHA `f14d09b5516c8ac99c06053ae3b2029bdfe26ef7`

| Workflow | Result |
|---|---|
| A5 UI lease, run 45129429735 | **SUCCESS** — Python 3.13: 18 passed + 5 subtests; Python 3.14: 18 passed + 5 subtests |
| RAW EYE frame ingress, run 45129429673 | **SUCCESS** — Python 3.13: 42 passed; Python 3.14: 42 passed |
| Staged runtime, run 45129429670 | **SUCCESS** — 252 passed, 10 skipped, 47 subtests |
| Integrated regression, run 45129429670 | **SUCCESS** — 424 passed, 3 skipped, 58 subtests |
| Public-repository privacy scan | **CLEAN** on both focused workflows |

CI is Linux/hosted-runner evidence, not Redmi or native Android evidence.

## Cross-team connection

Core PR #2408 current head: `7175a8d9147dc80c7ad095479d832118b44a63f4`. Its Android service is still one-shot: `captureGate.claimFrame()`, one frame publication, then `releaseProjection()`. The current provider therefore cannot create a real multi-frame temporal sequence on device.

Official Android documentation says a projection is a display/app-window media stream written to a `Surface`; an `ImageReader` can consume frames in real time. A session is one `createVirtualDisplay()` call; Android 14+ rejects a second call on the same `MediaProjection` instance. Source: https://developer.android.com/media/grow/media-projection .

The correct next provider shape is one user-started consented session, one VirtualDisplay, bounded ImageReader queue, stable source/session/consent lineage, unique per-frame signed nonce/digest/sequence/timestamps, a visible stop and immediate cleanup on `onStop`, cancel, expiry and process death. This is a cross-team proposal, not an enabled feature. Continuous capture remains OFF.

I posted this contract on Core PR #2408 (comment 7094160763), the latest V14 next-action PR #2412 (comment 7094165718), and PR #2414 (comment 7094170174).

## Redmi / updater / release

Latest private V13OBS #115 updated at 2026-11-23T07:11:18Z:

- Installed release remains `aed1d2b826290c95c70356b5d8b864b5ef382be4`.
- Auto-update is enabled and reports `UP_TO_DATE` at that installed SHA. This is not proof of functional chat.
- Latest stored FINAL turn: 57.74 s total, 41.63 s TTFT, 38.95 s prefill, 751 prompt tokens, 2 generated tokens; correctness UNKNOWN.
- Latest five-turn aggregate: B1 4 native attempts / 4 failures / 0 valid offers; B2 2 / 2 / 0.
- No new user turn or device mutation was issued. No candidate update request was sent.

The Perception candidate is **NOT_RELEASED / NOT_INSTALLED**. No Android capture, same-turn C3 consumption, native latent exchange, model-weight update or Redmi temporal-attention proof is claimed. **REDMI_UNVERIFIED.**

## Research note

R-109 applies the already full-text-reviewed TRACE paper (arXiv:2609.30670; see R-108) as an evaluation design: report false alarms, misses, response delay, completion and work per observation, not a single salience scalar. TRACE is visual-only at 1 FPS and cannot calibrate the current synthetic thresholds. ActiveForager (arXiv:2611.24267 v2) remains abstract-only in R-108; no full-paper claim is made. No third-party code, model, weights or dataset were imported.

## Whole-system status and next work

- A0/A1 frame decoding and source-bound RAW EYE ingress: **WIRED_SYNTHETIC / CI_GREEN**.
- A3 student projection: optional/local candidate only; no new weight-learning proof in this run.
- A4 temporal change: **WIRED_SYNTHETIC** under repeated same-lease frames; not active on the current one-shot Redmi provider.
- A5 packet history: **WIRED_SYNTHETIC / CI_GREEN**, bounded and revocation-cleaned.
- B1/B2/C4/C3 normal same-turn consumption: **NOT_ACCEPTED** for this UI path.
- Native learned latent exchange, JEPA weight learning, Android capture/action and Redmi temporal attention: **NOT_PROVEN / REDMI_UNVERIFIED**.
- The whole Canon and P0 basic-chat gate remain open. This is one bounded Perception integration, not system completion.

Next: Core implements the consented same-session frame stream; QA validates companion process-death/stop; Perception tests the stream through A5 context; Boss composes #2413 R-107 with #2414 R-108/R-109 and updates `V14_USER_NEXT_ACTION.md` / board V14-006 and V14-009.

**User action: none.** No manual Termux command, update request, model download/swap or permission change is justified.
