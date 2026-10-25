# Run313 checkpoint — JEF self-outcome label identity (software/SQLite)

2026-10-25 UTC. Branch `assistant/jef-outcome-eviction-run313-20261025`, based on Run312 review checkpoint `f97266161647692af204043661eab09bb1b10dbf` (not production main).
Preregistration `c08981dab89d02a0017458bc0f8064925aa595e7`; RED tests `ade024012aebca5944190f2c761865fdd1218dc2`; CI `42313fac0c5679cb75b4691a8090406807d40bb2`. Source patch `7a9c40c7893ac0dce2bc71a8d2651414701f13af`, remote `jefoutcome.py` blob `7fe503e47eea7a9cf79c3ce1863382dd883a2918` verified.

## Evidence
- RED workflow `40208101313`: **45 tests, 3 FAIL** (evicted event replay after restart, changed-target replay, concurrent source duplication). Privacy CLEAN. Raw artifact `12605031362`, ZIP SHA256 `62ed14ae1064692ffa14e3431f927efd9cfe0006c300fff8a09c5e1fa91d8471`.
- GREEN workflow `40208173446`: **45 tests OK**, privacy CLEAN. Raw artifact `12604122177`, ZIP SHA256 `e0c9695f56e9b610047e584b8941fd1873c6d8b3af948598f044ca9b537232f7`.
- Source change: persistent per-event/component receipts in existing SQLite states table. Retained old labels can lazily receive receipts. Source allocation serialized with Store mutex, receipt and bounded label ledger committed in one SQLite transaction. Replay after MAX eviction cannot allocate another source or overwrite the old self-label; concurrent callbacks no longer duplicate normal source allocations.
- The existing `record` vs `learn` authority, source verification, human veto, route correction and default safety modes remain unchanged.

## Run313b atomic source-row checkpoint
Additional preregistration `9e0871a9c24b70b3ccb1f3f1f87b56b72e2741a8`, RED test `9338bca92f13ce527e3c3a784ccb158bd08616f0`: exact-head CI `40208274084` **46 tests, 1 FAIL** as predicted. Failure: receipt serialization exception left an orphan `OUTCOME_SELF_LABEL` source database row, though label/receipt rolled back. Privacy CLEAN, raw artifact `12604622393` SHA256 `601c57b58b572898fb4c56591adff376ba2c244506a8b1976fdff7be5574b7dd`.

Patch `4376f174373c32129a5f4f08295569bc122d877e` (remote jefoutcome blob `9adff2bd0e1b8d74f783e519fb82191d9c47c0a9`) prepares immutable content-addressed bytes using Store's exact source hash/uid/byte/char conventions but defers **source row, label and receipt** to the same SQLite transaction. No Store or schema edit. GREEN exact-head workflow `40208346604`: **46/46 PASS**, privacy CLEAN; raw artifact `12604292148`, ZIP SHA256 `501e3ce41a5bc8ea7bac4e1d2524e4076deb9330ad0b7154ef8e4ecb26404910`. An interrupted blob preparation can leave an unreferenced blob file, but not an authority source row or label.

## Limits and next
Software/SQLite with authored outcomes; no native inference, Redmi, model utility or canonical gate promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, jepa_weight=0 and whole-system incomplete. Run310 full suite remains 2 FAIL/36 ERROR separately. Raw Actions ZIPs have 30-day retention; IDs/hashes preserved here.

Next: independently package the **current** review-chain Termux source ZIP, verify every member against the exact checkout, extract and run Run312/313 plus existing operator/SQLite phone regressions. This is source-only, not a Redmi proof. Then continue unowned functional blueprint work.
