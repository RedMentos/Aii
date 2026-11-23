# Research & Perception handoff — temporal UI lease lifecycle

Date: 2026-11-23  
Branch: `research-perception/v14-ui-temporal-attention-20261123-run1`  
Code checkpoint: `fc9e170399812b81366f8e67ac7563fec8b0f572`  
Final branch/doc head: `846ee8389e42f6700767cdfdbecedcc23a3ebb69`  
Parent: Perception temporal RAW EYE PR #2414 at `1660ce712edbde4a8555bd0b6fedcb428a53ec6f`  
Release-development HEAD observed before work: `aed1d2b826290c95c70356b5d8b864b5ef382be4`  
Status: DRAFT / NOT_RELEASED / EXACT TARGETED + STAGED + INTEGRATED CI GREEN

## Real defect and connected change

The previous temporal registry keyed stream state by `id(consent_lease)` but did not retain the lease object. Once an object was collected, CPython could recycle its numeric id; a later lease with identical source/session/receipt/generation metadata could then collide with stale feature history. The bounded registry now stores the exact lease object in each LRU entry and checks identity before reuse. The LRU remains capped at eight entries; source reset and eviction release the object.

The direct Core path calls `A5UIRuntimeAdapter.revoke(source_id)`, whereas the original temporal reset existed only in the Perception frame-scope helper. The adapter now clears temporal state in `finally`, including the no-Store return and exceptions during Store cleanup. This closes the lifecycle gap without granting capture, action, learning or truth authority.

Added three regressions:
1. lease object remains alive while its bounded stream entry exists and is released by source reset;
2. adapter revoke clears state when no Store exists;
3. adapter revoke clears state even when Store cleanup raises.

The Perception workflow now triggers for the temporal module/test/handoff on both push and pull-request paths; duplicate push path entries were removed.

## Research translated into evaluation requirements

- TRACE arXiv:2609.30670 (2026-09-25 preprint), full accessible method/results/limitations reviewed. Its official `om-ai-lab/trace-bench` repository at `d6a9a1c8dbb80e3a12c39600ce9e25460b763027` is MIT for code. Dataset rights are separate: StreamingBench-derived annotations are CC BY-NC-SA 4.0 under author permission; OVO-Bench annotation rights remain unresolved. No dataset or code was imported.
- TRACE motivates reporting false alarms, misses, response delay, completion and workload separately. Its 1-FPS visual-only single-instruction benchmark does not calibrate V14's 4×4 UI thresholds.
- StreamFlow arXiv:2608.10949 (2026-08-11 preprint) provides a related raw-pixel residual / bounded-memory / on-demand latent retrieval design; its Qwen3.5-9B results are not mobile evidence and no code/weights were reused.
- ActiveForager arXiv:2611.24267 v2 (2026-11-19) was reviewed only at abstract/metadata level; no full-paper claim, official repo or license verification is made.

## Exact tests and evidence

- LOCAL_LINUX CPython 3.13.5: isolated lifecycle smoke **3/3 PASS**:
  - exact lease retention until reset, then release;
  - no-Store A5 revoke clears temporal state;
  - Store cleanup exception still clears temporal state.
- Full local Aii checkout/pytest and exact repo py_compile: **BLOCKED** — no checkout mounted; `git ls-remote` failed because github.com DNS did not resolve.
- Exact final-head GitHub Actions at `26a87cad8351568033f31ae137d2a57355b50530`: all three associated workflows **SUCCESS**.
  - RAW EYE frame ingress run `45126018025`: Python 3.13 and 3.14 each **37 passed**, compile PASS.
  - A5 UI lease run `45126017980`: Python 3.13 and 3.14 each **18 passed + 5 subtests**, compile PASS; public privacy scan CLEAN.
  - Staged context/integrated regression run `45126018127`: staged Runtime **252 passed / 10 skipped / 47 subtests**; integrated regression **424 passed / 3 skipped / 58 subtests**.
  - These are GitHub-hosted CI results, not LOCAL_LINUX full checkout or Android proof.
- TERMUX/REDMI: **REDMI_UNVERIFIED**. Latest shared private owner-read in epic #1984 (06:34 UTC) still identifies installed release `aed1d2b826290c95c70356b5d8b864b5ef382be4`, updater enabled and UP_TO_DATE, but the last stored turn is 57.74 s total / 41.63 s TTFT / 38.95 s prefill / 2 generated tokens; B1/B2 remain TIME_BUDGET. This is not a new turn or a correctness acceptance.

## Important product limitation

Core PR #2408 still provides one frame per MediaProjection capture session. Temporal comparison intentionally resets across a new lease, session, receipt or Runtime generation. Therefore, the current one-shot provider cannot produce a genuine multi-frame `MEASURED` temporal sequence on the phone; current multi-frame evidence is same-lease synthetic only. To activate temporal attention on Android, Core/QA must provide an explicitly consented same-session frame sequence or a separately approved higher-level observation-stream capability. Do not enable continuous capture implicitly.

## Next integration

- Core: compose this A5 revoke cleanup with PR #2408's provider consumer and ensure the same authorized lease is held through all frame observations and downstream C3 use.
- QA: run exact-head Python 3.13/3.14 and staged/integrated workflows; keep emulator/Redmi status distinct.
- Boss: rebase/compose this Perception branch after #2375, preserve JEPA PR #2413's R-107 ledger entry when integrating this R-108 append, and sync `V14_USER_NEXT_ACTION.md` from verified facts.
- No user action is needed. No model, weights, permissions, updater, phone state or user data were changed.


## Android platform note for the next owner

The official Android MediaProjection guide states that capture is a media stream rendered to a VirtualDisplay Surface and that ImageReader can consume frames in real time. Consent is per capture session, defined by one createVirtualDisplay() call. Android 14+ targeting apps must not reuse the consent Intent or call createVirtualDisplay() a second time on the same MediaProjection instance; onStop must release the VirtualDisplay and Surface. The current one-frame behavior is therefore a provider design choice, not a platform requirement to obtain new consent for every frame.

Recommended Core implementation: one explicitly user-started MediaProjection session, one VirtualDisplay, a bounded ImageReader queue, stable session/consent lineage across frames, per-frame nonce/sequence/timestamp, visible OS stop, immediate cleanup on onStop/cancel/expiry/process death, and no raw-frame persistence. This remains a proposal; no continuous capture was enabled or tested. Sources: https://developer.android.com/media/grow/media-projection and https://developer.android.com/about/versions/14/behavior-changes-14.
