# Run84 — JEF/B1/B2 dual-source C3 post-generation integrity boundary (2026-10-31)

Owner: automation/GPT-6, isolated review branch `assistant/v13-run84-dual-source-c3-postgen-20261031-auto11`, exact parent Run83 #1443 `5ca8b4cc24f03238bca9846c284cb9efd53e9979`. This is a NEW software-only default-OFF adapter, not a modification to frozen Run83 native cohort, Run75/77/70, model/runner pins or Canon.

## Question and predicted acceptance

Run82 `jef_b1b2_c3_dual_source_shadow.build` produces an authenticated JEF typed decision and B1/B2 source-bound prompt but has no generator callback / post-generation integrity check. Can a separate default-OFF C3 callback boundary reject an incorrect or malformed formatter result, mutated prompt, newer USER, revoked human source, changed B1/B2 offer, and SQLite writes during the callback, while retaining zero output/tool/learning authority?

Acceptance: focused real SQLite FakeRuntime tests demonstrate a correct schema-shaped answer, OFF before any callback, wrong action, duplicate JSON keys, prompt mutation, stale USER, revoked F1/F5 memory, mutated offer, and same-connection/external SQLite writes all fail closed; no message/action output is committed. Source + model state checked again after generation. Any callback side effects are DETECTED, NOT rolled back or sandboxed. No native model is run by this package.

## Implementation and proof plan

New isolated `v13/code/v13/jef_b1b2_c3_postgen_shadow.py`; new `v13/code/tests/test_run84_dual_source_c3_postgen.py`; separate CI workflow. Reuse Run82 source composer and existing strict `jef_c3_schema_draft_candidate.decode_action` parser and schema, no duplicated scoring logic. Snapshot Store table counts + SQLite total_changes/data_version/transaction state before callback and recheck after, including after source revalidation. Use deepcopy of prompt and schema. Return source-bound SHADOW verdict only; never stage C5, dispatch, write Store, call a model itself or accept TTY approval.

## Fixed negative gates and limitations

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight 0; Redmi UNMEASURED; whole V13 incomplete. No learned B1/B2 semantic utility, native C3 success, C5/C6 delivery, TTY or output approval. A trusted callback is required; detection is not isolation. Original Run83 synthetic-native 6/6 per arm is unrelated and must not be promoted.

## Workflow and next command

After this prereg is remotely verified, implement adapter/test/workflow on unique paths; run `cd v13/code && PYTHONPATH=.:tests python -m unittest -v tests.test_run84_dual_source_c3_postgen`, `python -m compileall -q v13 tests`, privacy/diff scans; trigger CI, retain original raw logs and SHA256SUMS, verify remote and private backup if permitted. Continue next independent package. Remaining platform budget UNKNOWN.
