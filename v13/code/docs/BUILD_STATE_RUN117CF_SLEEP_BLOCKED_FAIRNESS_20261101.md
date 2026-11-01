# Run117CF BUILD_STATE — Sleep blocked-session fairness (review-only)

2026-11-01 UTC. Owner: Run117CF branch. Parent Run117CD PR #1558 at exact head `29da84e58339a4a83b2ce245117ac874832d3f85`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No production merge, no model/seed/registered-cohort changes.

## Problem and fix

Run117CB made session scheduling oldest-cursor-first, but a session whose **first unconsumed assistant is DRAFT** and whose later assistant is FINAL is permanently blocked at its cursor. Eight such sessions fill all eight work slots on every cycle; a ninth ready session never gets digested. This is a real progress/liveness bug, not a source-authentication relaxation.

Run117CF checks the first unconsumed assistant status per pending session and defers those blocked by unfinished status. Ready sessions retain oldest-first ordering and the existing eight-session work cap. New `blocked_sessions` and existing `deferred_sessions` are workload diagnostics only. All digest content still comes through `native_history` source verification. A blocked session becomes eligible after its DRAFT is finalized; no cursor is advanced through an unfinished answer.

## Original regression RED (closed)

- New real SQLite/Store tests reproduce eight blocked + one ready and one all-blocked session.
- Original source-pinned Actions [41257169340](https://github.com/RedMentos/Aii/actions/runs/41257169340) **FAILURE** at `f97defcff3a330e4b01aafec93880496f58a25f4`, before source fix.
- Original artifact `13063661902`, ZIP SHA256 `21774f1fb663d208b972df413d62ae8a42b13a9c0ee851bbf03b66c0b311df5f` (5,095 bytes); independently downloaded, CRC clean, 16/16 inner SHA256SUMS, PINS/VENV/DEPS/COMPILE/PRIVACY/DIFF all zero. TEST_EXIT=1: 51 tests, one expected assertion failure (ready ninth received zero turns) and one expected missing blocked_sessions error. All other tests pass. Original raw retained without rewriting.

## Source and pending verification

- Test blob `1c9a7c1302fd53980e1a3146a609adfa6802f26b`; fixed `sleep_offline.py` blob `dfea2f22a36b53ad01051efd1f547ad632d6f26f`.
- Corrected CI workflow pins both and includes existing Sleep/ContextOS source/revocation/fairness tests. CI exact-source result: **PENDING** at initial checkpoint; do not promote until terminal original raw is independently checked.
- Exact local reproduction: `cd v13/code && python -m unittest -v tests.test_run117cf_sleep_blocked_fairness tests.test_run117cb_sleep_session_fairness tests.test_run117bz_sleep_digest_backlog tests.test_run117ca_sleep_context_consumer tests.test_sleep_digest_view_authority_run278 tests.test_sleep_offline tests.test_sleep_digest_live_lineage_run208 tests.test_context_os`.

## Negative gates and next step

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; `jepa_weight=0`; no native model, Redmi, weight training, tool/output authority, or whole-system completion. This is software-only source-safe scheduling. Original failed attempts preserved.

Next: inspect terminal corrected CI run, download and CRC/hash-verify original artifact, independently review scheduling fairness and no-cursor-skip counterexamples; then consider bounded large-session performance without weakening source/age/learning gates. Current remaining platform budget UNKNOWN.
