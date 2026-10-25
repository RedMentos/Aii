# Run313 checkpoint — JEF self-outcome label identity (software/SQLite)

2026-10-25 UTC. Branch `assistant/jef-outcome-eviction-run313-20261025`, based on Run312 review checkpoint `f97266161647692af204043661eab09bb1b10dbf` (not production main).
Preregistration `c08981dab89d02a0017458bc0f8064925aa595e7`; RED tests `ade024012aebca5944190f2c761865fdd1218dc2`; CI `42313fac0c5679cb75b4691a8090406807d40bb2`. Source patch `7a9c40c7893ac0dce2bc71a8d2651414701f13af`, remote `jefoutcome.py` blob `7fe503e47eea7a9cf79c3ce1863382dd883a2918` verified.

## Evidence
- RED workflow `40208101313`: **45 tests, 3 FAIL** (evicted event replay after restart, changed-target replay, concurrent source duplication). Privacy CLEAN. Raw artifact `12605031362`, ZIP SHA256 `62ed14ae1064692ffa14e3431f927efd9cfe0006c300fff8a09c5e1fa91d8471`.
- GREEN workflow `40208173446`: **45 tests OK**, privacy CLEAN. Raw artifact `12604122177`, ZIP SHA256 `e0c9695f56e9b610047e584b8941fd1873c6d8b3af948598f044ca9b537232f7`.
- Source change: persistent per-event/component receipts in existing SQLite states table. Retained old labels can lazily receive receipts. Source allocation serialized with Store mutex, receipt and bounded label ledger committed in one SQLite transaction. Replay after MAX eviction cannot allocate another source or overwrite the old self-label; concurrent callbacks no longer duplicate normal source allocations.
- The existing `record` vs `learn` authority, source verification, human veto, route correction and default safety modes remain unchanged.

## Limits and next
The current implementation calls `Store.source` before the label/receipt transaction. A crash in this interval could leave an unreferenced source row, but not a trainable label. Next independent Run313b fault injection should make **source row + label + receipt** one SQLite commit, without editing hash-bound Store or changing source bytes; preserve RED and GREEN. This is a concrete integrity improvement, not a new authority or native model claim.
Software/SQLite with synthetic authored outcomes; no native inference, Redmi, model learning utility or canonical gate promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA unavailable, jepa_weight=0 and whole-system incomplete. Run310 full suite remains 2 FAIL/36 ERROR separately. Raw Actions ZIPs have 30-day retention; IDs/hashes preserved here.
