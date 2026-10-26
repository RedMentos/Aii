# Run563 — original Run561 FUTURE_003 independent offline verification

Date 2026-10-26. Preregistered before implementation at commit `39d6bf8176979dc0d0bf69b3dab0012a8c8b986d` (blob `23ece8f4a7ae11152e678eb7a4275e093c7bfec1`). Review branch PR #561 stacked on dormant Run562; main unchanged.

## Exact evidence and independent result

Original Linux-native Run561 Actions `40357028652`, head `cf40fe3bf601260c6c6590637e50de0a6188a6c8`, completed SUCCESS. Original immutable raw artifact ID `12666688509`, ZIP SHA256 `89b31cc16d9bc569492d6a4c560a2a511b65f0e6bbe2fab0562b4bf6a7e0ac15`; safe artifact ID `12666848624`, ZIP SHA256 `503a1a4c0ad900f71758b42cfda40ff75b440240db7d469f06fe8b976877ed77`. Local ZIP precheck verified 27/27 raw manifest entries, 24/24 safe member digests, all seven original exit receipts zero, exact three stage IDs, 42 consumer rows and zero wrong committed; **local oracle comparison alone is not a frozen-source-origin proof**.

Independent no-model Actions `40360930989` at exact head `545946a6c81adcc33eabebfef82fd27e4bb0990b` **SUCCESS**. Existing pinned `run559_offline_review.py` git blob `4c8ebb3a00ffdf5454f11dbf4f1706ff95f7be92` independently bound all recorded fixture/oracle/history bytes to frozen original Run491 source, rechecked frozen Run500/504 map/schedule, pinned model/runner receipt, full raw and safe SHA manifests, 42/42 source+consumer rows, 12-field oracle scoring, and zero wrong committed. 40/40 source regressions PASS; privacy CLEAN; six exit receipts all 0. Original independent offline artifact ID `12667444246`, ZIP SHA256 `df1738d39cd382e145989eeb00b29a80075d8a1ea6ed9966166f9d0117487a5c`, 16/16 SHA manifest entries independently verified. Raw and safe original ZIPs plus offline artifact privately backed up under `/V13-Checkpoints/2026-10-26/Run563/`.

Descriptive mean 12-field utility (6 observations per arm): `b1_only=0.236111`, `b2_only=0.125`, `both_none=0.222222`, `both_exact=0.222222`, `both_control=0.194444`, `same_policy_dual=0.208333`, `prompt_only_dual=0.25`. Thus `both_exact < b1_only` in this batch; no complementary advantage or STEP2 promotion. These are descriptive values for one frozen batch, not independent seed-level inference or a new model test.

## Scope, gates, continuation

This run executed **no new native inference**, downloaded **no models**, and did not change frozen cohorts, seeds, model/runner hashes, Canon or runtime. The source of native inference is original Run561 only (Linux, not Redmi). `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `Redmi=UNMEASURED`, full V13 INCOMPLETE. No learning, age or approval gates changed.

Next: check active serialized native owners through GitHub Actions API; if none, open the existing dormant Run562 FUTURE_004 branch as a **draft PR against exact Run561 head**, without altering original Run562 source, to trigger its one-shot frozen 42-row Linux-native workflow. Independently verify Run562 raw/safe artifacts in a later separate source-only audit before any FUTURE_005 activation. Preserve RED, never rerun prior batches, no main merge. The future 005–024 batches, B/C/D/E controls, Body-JEPA and Redmi proofs remain open.
