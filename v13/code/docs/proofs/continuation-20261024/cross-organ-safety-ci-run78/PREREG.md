# Run78 prereg — cross-organ safety/age/memory/sleep CI expansion

2026-10-24. Base Run77 PR110 `7cc74d0d1751343ec21d1c7172f884c0ba45f25e`.
Owner only `.github/workflows/v13-focused-proof.yml` test module list and new `v13/code/docs/proofs/continuation-20261024/cross-organ-safety-ci-run78/**`. No production runtime/model/native edits.

Goal: add 20 actual Linux software suites to Run77's 142-test JEF/Callosum/World/Context baseline. Safety and permissions, Age rights, stop controls, per-organ snapshots, SQLite migrations, native-history source lineage, episodic/neuromod/attention, Self Model, deterministic output policy, transactions, Sleep scheduler and homeostasis must not regress. Registered modules (no retuning after results):

- `tests.test_age`
- `tests.test_age_rights`
- `tests.test_prohibitions`
- `tests.test_standstill`
- `tests.test_organ`
- `tests.test_migrations`
- `tests.test_runtime_queue`
- `tests.test_history_lineage`
- `tests.test_episodes`
- `tests.test_neuromod`
- `tests.test_attention`
- `tests.test_ledger_hygiene`
- `tests.test_selfmodel`
- `tests.test_output_policy`
- `tests.test_output_policy_runtime`
- `tests.test_toolstep`
- `tests.test_transaction`
- `tests.test_sleep_scheduler`
- `tests.test_sleep_validation`
- `tests.test_homeostasis_regulation`

All use Python stdlib/SQLite plus existing isolated numpy and prompt-toolkit, no model downloads, no native inference/training, no paid provisioning. Existing 10-minute GitHub Actions timeout, read-only permissions and privacy scan unchanged. Record all RED failures and fix only reproducible code/fixture defects without loosening guards. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE remain unchanged. A 20-module expansion is not the complete repository suite.
