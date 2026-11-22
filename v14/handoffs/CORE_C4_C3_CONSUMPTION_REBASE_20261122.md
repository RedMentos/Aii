# Core handoff — same-turn C4 → C3 consumption on current Boss base

Date: 2026-11-22

## Ownership and exact base

- Lane: Core & Harness.
- Branch: `core/v14-c4-c3-consumption-rebase-20261122`.
- Base: Boss integration PR #2288 branch `boss/v14-recall-store-pin-rebind-20261122`, exact starting SHA `f0d3c848dfb1d65e282f065233adbe3c9205e439`.
- The branch is stacked on #2288 and is not a release branch.
- Shared V14 board, active master and historical Canon were not edited; Boss/Integrator owns those shared files.

## Runtime change

- `v13/code/v13/cognition.py`: after persisted OfferPacket/QueryPacket bindings, source spans and the selected C4 context are revalidated and assembled for C3, emit `c4_offer_context_ready`.
- Receipt fields are limited to `role=C3_LANGUAGE`, selected OfferPacket IDs, count and PASS. It contains no prompt, source bytes, quotes, summaries or user text.
- The event means source-bound C4 selection is ready at the C3 context boundary. It does not claim that the native model semantically used the context.
- The audio candidate, recovery wrapper, integrated stager and runtime deployer pins were rebound in order. Exact blob/SHA-256 values are recorded in the commit/PR and must be re-read after CI.

## E2E regression

- `v13/code/tests/test_v14_same_turn_c4_c3_consumption.py` exercises the real Python Runtime submit/worker path, SQLite Store, Cognition, FocalLoop, persisted packet validation and C3 prompt assembly.
- It requires both B1_DETAIL and B2_GIST same-turn OfferPackets to enter the C4 coalition and their distinct hypotheses to appear in the C3 system prompt after two content-free prior C3 zero-token prefill failures.
- It checks the exact selected packet IDs in the receipt and tampers with a selected OfferPacket as a negative control; the tampered binding must be rejected without another receipt.
- Native model output is a deterministic synthetic runner. This is connected software/SQLite evidence, not native GGUF or Redmi proof.

## Test and deployment boundary

- LOCAL_LINUX full-repository tests: BLOCKED. The execution container has no Aii checkout and `git ls-remote https://github.com/RedMentos/Aii.git HEAD` failed because github.com DNS did not resolve. No local full-suite PASS is claimed.
- Exact-head GitHub Actions on this new branch: pending at branch creation; the dedicated workflow runs Python 3.13 and 3.14 compile plus the same-turn E2E and negative binding control.
- Full staged/integrated, Lab-Age, migration and owner-read workflows remain subject to the upstream #2288 pin-chain status. A pass on the focused workflow does not clear unrelated upstream failures.
- TERMUX/REDMI: REDMI_UNVERIFIED. Latest private PIPELINE_STATUS request #453 had no authenticated reply; installed SHA and updater consent remain UNKNOWN.
- Release: NOT_RELEASED. No deployment, model/weight, Age, permission, updater or user-data change occurred.

## Next action

1. Read exact-head focused CI and fix any regression.
2. Run staged/integrated and source-pin verification on the exact PR merge commit; distinguish any inherited #2288 failure from this Core delta.
3. If Boss advances #2288, create a new current-base rebase branch rather than force-pushing.
4. Boss/Integrator should merge this Core slice into #2288 and refresh the shared board/workplan/user handoff.
5. After that, continue the separate Core V14-003 native input-embedding receiver experiment; keep production B3 OFF until native receiver utility and negative controls are proven.
