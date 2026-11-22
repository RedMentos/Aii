# Core handoff — same-turn C4 → C3 consumption receipt

Date: 2026-11-22

## Ownership and base

- Lane: Core & Harness.
- Stacked base: Boss integration branch `boss/v14-same-turn-budget-pin-chain-20261122`, verified head `9b90d39735c7e49bd9aa47f449bcd18fd924164b`.
- This package does not edit the shared V14 board, workplan, or user-next-action file; those remain Boss/Integrator-owned.
- It does not edit the historical V13 Canon or the V14 active master.

## Concrete runtime change

- `v13/code/v13/cognition.py`: after `Cognition.analyst_context()` has revalidated persisted OfferPacket/QueryPacket bindings and assembled the selected context for C3, it writes a privacy-filtered `c4_offer_context_ready` receipt.
- The receipt contains only C3 role, selected OfferPacket IDs, count and PASS status. It contains no user text, model summary, quote, source bytes, or raw prompt.
- The event means **source-bound C4 selection is ready at the C3 context boundary**. It does not claim semantic use by the native model; the accompanying Runtime test separately inspects the exact C3 prompt received by the test runner.

## E2E regression

- `v13/code/tests/test_v14_same_turn_c4_c3_consumption.py` uses the real Runtime, SQLite Store, Cognition, FocalLoop, packet validation, and C3 prompt assembly.
- It seeds two content-free prior C3 zero-token prefill DEADLINE records, then requires the current nontrivial both-body turn to produce B1 and B2 OfferPackets, include both in the same-turn C4 coalition, and pass their distinct model hypotheses into the C3 system prompt.
- It verifies the exact selected packet IDs in the privacy-filtered receipt.
- Negative control mutates a persisted selected offer and requires the source/binding check to reject it without emitting a second receipt.
- Native runner outputs are deterministic synthetic stubs. This is a connected software/SQLite integration test, not native GGUF execution or Redmi proof.

## Test and deployment status

- LOCAL_LINUX full-repository tests: BLOCKED. The execution container has Python 3.13.5 but no Aii checkout; `git ls-remote` failed because `github.com` DNS did not resolve. No local full-repository suite is claimed.
- Exact-head Core E2E workflow `44965089326`: **PASS** on Python 3.13 and 3.14. Both compiled the exact Runtime consumers and passed the real `Runtime.submit → worker → _turn → Cognition → FocalLoop → C3 prompt` path, two recent C3 zero-token DEADLINE records, both selected body offers, C4 coalition, C3 prompt, receipt IDs and tampered-offer negative control.
- Exact-head staged/integrated workflow `44965089360`: **PASS**. `staged-runtime` PASS; integrated regression **424 passed, 3 skipped, 58 subtests passed**.
- The full source-pin chain was read back after the cognition.py change: cognition blob `e5667431964d216b290564ed96a39ef628a1f1d6` → audio candidate blob `50f2deac4d92a9dfba56758f535dc0b64afb0aec` → recovery wrapper SHA-256 `5501d583985e286775881fbccda31052276d9c8d21f2c7e814329f062cc5008e` → integrated stager SHA-256 `c2369649c5b50fd8ee1df83e1f9fe038073b33ca3a4d4477babe0916768a6136` → runtime deployer pin; all comparisons passed.
- **Open test failure to preserve:** older exact-head staged run `44964349632` failed the separate disposable observer test because it hard-codes 13.5 seconds while the actual effort/resource-scaled per-body deadline was 6.75 seconds. The newer `44965089360` run did not execute that disposable test; its pass does not clear this failure. Boss should change only the invalid exact-time assertion to a bounded positive deadline check and retain the OfferPacket/C4/C3 assertions.
- TERMUX/REDMI: REDMI_UNVERIFIED; no authenticated phone receipt or device access.
- Updater/deployment: unchanged; this branch/PR is not a release and is not installed.
- Models, weights, Age, permissions, device data and installed app state were not changed.
- A separate latent-coupling research note with paper/repository/license and matched/deranged acceptance criteria was posted on whole-system issue #1984; no weights or dependencies were downloaded.

## Next action

1. Boss should fix the still-open disposable observer deadline assertion without weakening the C4/C3 assertions.
2. QA should reconcile the Android companion `android_os_permission_required` mismatch noted on #2273: launch_app is registry/receipt-declared as not requiring an Android OS runtime permission; retain the separate companion per-action consent.
3. QA should rebase its generation-boundary regression (#2277) onto the current Boss stack; avoid duplicate source edits.
4. Boss/Integrator should combine the verified Core fix, the worker-path receipt, and QA's tests on the current integration ancestor, then refresh `V14_WORK_BOARD.json`, `V14_LIVE_WORKPLAN.md`, and `V14_USER_NEXT_ACTION.md`.
5. Only a later signed normal-path deployment plus a fresh private owner-read receipt can change the Redmi status.
