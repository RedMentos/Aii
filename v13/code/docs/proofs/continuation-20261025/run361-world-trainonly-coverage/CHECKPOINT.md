# Run361 — WorldModel counterfactual support is training-only

Parent: Run360/PR355 `fb908db88c9608fccf9e4cdc493b3a577d9dbd0b`. Review: PR356. Owner: `assistant/run361-world-trainonly-coverage-20261025`. Canon: §7.2.2 Action-Coverage and Counterfactual Confidence. World predictions remain **HYPOTHESIS**, never causal facts.

## RED: observed support leakage

Exact-head [Actions 40229629016](https://github.com/RedMentos/Aii/actions/runs/40229629016) on `5f777262fb5a03de2864785876df21734e2323f1`: **12 tests; 2 failures and 1 error**. The old World fit included held-out evaluation states in its counterfactual coverage map and counted repeated actions as independent support. Raw artifact ID 12612736546; ZIP SHA256 `4a7d67ff4ced049961634e9dd027c9edbe444424f51ddec4482d748843a92a36`.

## Corrected behavior and compatibility

World fit now stores only training states in `states`, with aligned training source-group IDs in `state_groups`. Counterfactual confidence uses **distinct training source groups** rather than raw action-row frequency. Old persisted World states without this metadata abstain until re-fit; no implicit evidence promotion. Existing Run64 hand-built `store=None` numerical fixtures have a narrowly scoped compatibility path explicitly marked `SYNTHETIC_TEST_ONLY`. This path is never used for a real Store or a persisted fitted artifact.

Intermediate [Actions 40229687274](https://github.com/RedMentos/Aii/actions/runs/40229687274) passed 12 focused tests but revealed two legacy synthetic-fixture regressions in broader CI. Those failures were retained, not hidden. After the narrow compatibility correction, exact-head [Actions 40229814620](https://github.com/RedMentos/Aii/actions/runs/40229814620) on `713b24275ce6abb9a96d4bc465f63653de10dc43`: **13/13 PASS**, privacy **CLEAN**. Raw artifact ID 12612568587; ZIP SHA256 `a727538fc4ed42d0f323f52bf3134b883ea6811b2d8888ba4ed27c5d8662792e`. Run301, Run306, source lineage, observed count, terminal outcomes, runtime observation and source-bound World workflows were also successful on this source at checkpoint inspection. Broader complete-suite failures remain separately tracked.

## Limits and next command

Source-only Linux NumPy/SQLite proof, **not** native World JEPA, Body-JEPA, Redmi, causal validity or whole-system completion. Original cohort and seed hashes were not reinterpreted. Central `BUILD_STATE.json` remains unchanged; the scoped state, source blob SHAs, raw receipts and original negative gates are in `BUILD_STATE_RUN361.json`. Next: `cd v13/code && python -m unittest -v tests.test_world_trainonly_coverage_run361 tests.test_world_source_disjoint_run306 tests.test_world_model` with isolated `numpy==2.3.5` and `prompt-toolkit==3.0.52`; independently re-fit older World state only from currently valid sources.
