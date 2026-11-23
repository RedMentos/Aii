# AG6 manual adapter approval: second-transaction source recheck — preregistration

UTC 2026-10-29. Review-only child of #1131 at `636ec7fb9f5608b93b5465ae8e56231158475669`. No production merge, no model/seed/cohort registration change, no activation outside isolated authored test fixtures.

## Concrete gap

`WeightConsolidation._approve_locked` checks staged source/explicit rating/FINAL dependencies in transaction 1, commits `ACTIVATING`, then opens transaction 2 and can publish the adapter mirror/registry without checking those dependencies again. An out-of-band SQLite revocation committed between the two transactions (outside the normal single coordinator) can therefore authorize a candidate whose supporting source was deleted. The existing in-process mutex prevents normal same-Store interleaving but does not prove cross-process/external SQLite immutability.

## Registered negative control

Use an isolated real SQLite Runtime fixture with nine human memories and one explicit rated FINAL with declared supporting SourceRef, plus authored FakeLora. Stage, train, gate to PENDING_USER. Wrap `Store.tx` only during manual `approve` and, **after transaction 1 commits and before transaction 2 begins**, commit `sources.deleted=1` for the rated dependency through a separate SQLite connection. Preserve the exact original RED. Expected after correction: approval refuses, request remains PENDING, batch returns to PENDING_USER through existing recovery, no consolidated memory, no adapter registry activation/mirror. A valid unchanged source still approves in existing tests.

## Minimal candidate

Inside the second SQLite transaction, after validating ACTIVATING attempt ID/input hash and **before any mirror/registry side effect**, recheck all staged item source refs and rated answer dependencies with the existing `_check_item_sources`. If invalid, raise a source-specific veto and let the existing recovery journal restore PENDING_USER. No new learning permission, no changed training data, no silent artifact deletion. The first transaction check remains; no bypass of original gates.

## Evidence and limits

Run exact-source pinned focused tests on Linux NumPy with real SQLite/FakeLora, compile, privacy and diff; preserve original RED and GREEN raw ZIPs, CRC, SHA256SUMS and private backup. This is a software transactional guard, not native adapter quality, device execution or approval to activate weights. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight0, V13 INCOMPLETE remain.

Owned paths: `v13/code/v13/agi/weights.py` (minimal second-tx guard), `v13/code/tests/test_ag6_second_tx_source_recheck_20261029.py`, `.github/workflows/v13-ag6-second-tx-source-recheck-20261029.yml`, and dedicated BUILD_STATE. Existing PR1128 tests and all frozen hashes retained.