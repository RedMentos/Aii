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

- LOCAL_LINUX full-repository tests: BLOCKED. The execution container has Python 3.13.5 but no Aii checkout; `git ls-remote` failed because `github.com` DNS did not resolve. No local suite is claimed.
- Exact-head GitHub Actions: pending until the stacked PR is opened and workflow runs complete.
- TERMUX/REDMI: REDMI_UNVERIFIED; no authenticated phone receipt or device access.
- Updater/deployment: unchanged; this branch/PR is not a release and is not installed.
- Models, weights, Age, permissions, device data and installed app state were not changed.

## Next action

1. Verify exact-head Python 3.13/3.14 compile and E2E workflow; fix any genuine failures.
2. QA should rebase its separate same-turn generation-boundary regression (#2277) onto the Boss stack and add the downstream C4/C3 receipt assertion, without editing Core-owned source.
3. Boss/Integrator should combine the verified Core fix, this receipt, and QA's downstream test on the current integration ancestor, then refresh `V14_WORK_BOARD.json`, `V14_LIVE_WORKPLAN.md`, and `V14_USER_NEXT_ACTION.md`.
4. Only a later signed normal-path deployment plus a fresh private owner-read receipt can change the Redmi status.
