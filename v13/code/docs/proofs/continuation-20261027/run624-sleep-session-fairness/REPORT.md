# Run624 — bounded fair Sleep A digest across more than eight chats

2026-10-27 UTC. Review-only child of Run623 PR618 head `608d7be0b214e66771ae70cba2d61c8b3a95a6a5`, PR619. Preregistered **before** test and implementation in commit `97fff0b07e3a4c1f2155cf1df1a69e86a34dcbb6`. Original source `sleep_offline.py` blob `4ad4e4382b73f7ee2189e1d2e6d05a5d09b6ac9c` selected the latest eight FINAL-bearing sessions forever. A session older than that window could never enter the extractive Sleep A digest even when it had valid unprocessed turns.

## Implementation

Source commit `752d5769150fdc5e67ae831dbcf2bbae7243b5e8`, exact code blob `0525bffc887efd91a26a67f94a38f7eab2cdfd0f`. The new `_session_batch` retains a fast lane of the **four newest** FINAL-bearing sessions and adds a **four-session persisted keyset round-robin** across the rest. Every cycle is bounded by `SESSIONS_MAX=8`; each session still drains at most `TURNS_MAX=64` source-validated pairs. The cursor is stored in the existing `S7_DAY_DIGEST` state and invalid type/oversize fails closed before writing. Existing digest entries, source revocation, history validators, Age and learning rights are unchanged.

## Actual exact-head Linux SQLite evidence

- **Frozen prereg** `97fff0b0`; original new test committed `57b47ee5` before source patch. First CI attempt at `ab409859` exposed a **test expectation error**: `sessions` counts actually processed sessions, not already-completed hot sessions. The original failed GREEN log and all raw files remain preserved. Corrected test in `5265c190`, blob `bea79648409efc7d6f23fa02a110a74fa09ea5a7`, explicitly after implementation. This is disclosed, not silently presented as a pristine prereg.
- Exact-current Actions **run `40418239872` SUCCESS**, checkout HEAD `0e59091f5f09fa39adbe100031f470c6fc3f12d4`. Original Run623 source with the same corrected four-test counterexample: **RED, exit 1** (5 failures and 1 error; includes starvation, absent cursor, invalid cursor acceptance). Patched exact source: **18/18 Linux SQLite Runtime/software tests PASS**, including 12- and 17-session liveness/restart, hot-session continuity, cursor rejection, source-bound deferred/revoked history, digest live context, predictor and staging. The historical 70-turn soak was not rerun in this final focused job; it passed in the earlier failed CI at `ab409859` (22 tests, 21 passed, one incorrect new test expectation), and remains distinct evidence.
- Privacy scan `608d7be0b..HEAD: CLEAN`, exit 0. Canon SHA256 remains `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`. No model download, inference or Redmi device was used.
- Success raw artifact `12696475583` from Actions, ZIP SHA256 `1b0a10116bde87b37bacf5937775f43e4d0b0a23b6e4533479162925fcf5b7a4`; all ten internal manifest entries independently SHA-verified. Failed first GREEN artifact `12696285507`, ZIP SHA256 `6922f4f56bc8c4d0be74277109bd83c3e35b1e40e7b9a9ed5cb522b728c67129`, also SHA-verified.
- Both ZIPs are durably stored in **private Library** `/V13-Checkpoints/2026-10-27/Run624/`; both were materialized back and byte-compared against the originals (PASS). This is not the rejected anyone-writable Drive destination.

**Scope:** functional source-bound Sleep A multi-chat liveness, not proof of semantic learning. STEP2 remains `UTILITY_FAIL`; B3 L1 `FAIL`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; Redmi `UNMEASURED`; V13 `INCOMPLETE`. No main merge or Age/learning/tool authority promotion.

## Next independent package

Build and independently verify an **exact-current source-only Termux phone ZIP** including this new Sleep A scheduler, with extracted SQLite Runtime regression and full-member SHA parity (using existing pinned Run622 packaging/verifier, without altering model/cohort pins). Continue toward native body learning/semantic utility in a separate package; do not confuse source packaging with device or native acceptance.
