# Core & Harness — B1/B2 per-organ runtime evidence

**Date:** 2026-11-24  
**Branch:** `core/v14-body-offer-native-evidence-20261124-run1`  
**Code base:** PR #2464 branch `core/v14-native-prefill-receipt-20261124-run1` at `97ffc6db08f9cdeb630bff33341436ded6030f21`  
**Current code checkpoint before handoff-only additions:** `2aa38ca5cc5b489393d37ab02abab4f9d804914d`  
**State:** DRAFT / NOT_RELEASED / REDMI_UNVERIFIED.

## Concrete runtime change

`brain_panel.status` now reads the persisted `body_offer_attempt` and `body_offer_delivered` telemetry for the exact latest assistant event and joins it to the existing C4 selection and C3 native prompt receipts.

For each B1_DETAIL/B2_GIST attempt it exposes only:
- attempt status;
- prompt/generated token counts, TTFT, duration and sampled peak PSS;
- whether a source-verified OfferPacket was durably delivered;
- whether C4 selected its exact packet ID;
- whether that same ID appears in the C3 prompt receipt;
- a bounded consumption state distinguishing missing receipt, non-selection, mismatch, synthetic inclusion and verified C3 native prefill/generation.

No prompt, hypothesis, quote, source text, exception body or arbitrary model string is returned. `semantic_use_proven` remains false. A matching packet ID plus verified C3 prefill proves transport to the model input boundary, not semantic attention or trained latent exchange.

## Test evidence

- **LOCAL_LINUX_ISOLATED:** CPython 3.13.5, pytest 9.0.2; isolated helper `py_compile` and 5 targeted tests PASS. This is not the full Aii checkout or the exact repository test file.
- **Full repository LOCAL_LINUX:** BLOCKED / NOT_RUN; no checkout is mounted and `git ls-remote` fails GitHub DNS in this environment.
- **Exact branch CI:** Python 3.13 and 3.14 jobs plus offline-bridge-security were QUEUED at the last poll on the code/test checkpoint; no PASS/FAIL result yet.
- **CI parent dependency:** PR #2464 exact head `97ffc6db08f9cdeb630bff33341436ded6030f21` had 31/32 check-runs SUCCESS, 1 SKIPPED, 0 failures. The follow-up is intentionally stacked on that native prefill/receipt path.
- **Adjacent fair-scheduler PR:** #2478 head `8e19f6ab49b0d163878196b9a72467c6525c2f6a` had 27 checks registered, 25 QUEUED and 2 SKIPPED at last readback; no completed test result was available then. This branch does not edit its files.

## Product and device boundary

The change makes the next real B1/B2 failure diagnosable from sanitized local status; it does not itself make the bodies faster or more accurate. It also does not change routing, budgets, models, weights, Age, permissions, Android companion state or user data.

No connected Redmi device was available. The latest shared V14 record still marks AI `STOPPED_BY_USER`; no CHAT_SEND, UPDATE_REQUEST, LOG_PAGE, shell, restart or device action was performed. **REDMI_UNVERIFIED.** GitHub push/PR is not deployment. The existing updater was not invoked.

## Next executable action

1. Obtain exact-head Python 3.13/3.14 CI for this PR and fix any observed regression.
2. After PR #2464 is independently reviewed/integrated, rebase this read-only telemetry addition onto the current integration head and run the exact staged/integrated consumer tests.
3. Use the new per-role token/TTFT/PSS and delivery/selection counters to calibrate B1/B2 fair slices against actual runner measurements, not assumed body timings; retain both bodies and C3 reserve.
4. Only after an authorized installed build and a separate owner-verified device receipt, compare real B1/B2 prompt tokens, TTFT, generated tokens, OfferPacket delivery, C4 selection and C3 prefill. No native or Redmi result is claimed here.

**User action required: NONE.** No manual Termux command, model download/swap, weight change or permission change is needed for this repository-only candidate.
