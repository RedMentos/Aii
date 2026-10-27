# PR667 + PR669 combined security review (2026-10-27)

## Source and ownership
- Exact parent: PR669 head `2671f054ed025625abe94be42d12667329c4366f` (Claude PR666 BP11b export review); no overwrite of Claude, PR667 or main.
- Separate source review PR667 at `551d6212d7b71f8e78e1fdb163e45ab41a11310d`, originally based on Claude `ed5010708`. The source fix was applied narrowly to the newer BP11b source; PR667's seven mid-fetch negative/positive tests were copied byte-exact.
- Branch `codex/automation11-module-review-merge-20261027`, test commit `809733d56cb376649c7578ed7a298c2d02b08424`, workflow commit `7719a01f4191192855ad15faf609d9a6c4cc6609`. Current owner: independent GPT-6 security integration review.
- Changed runtime path: `v13/code/v13/modules_gate.py` only; BP11b `module_learn.py` and its typed export ban from PR669 remain byte-unchanged. No runtime age, model, cohort, seed or authority promotion.

## Verified focused evidence
- GitHub Actions `40462349557`, exact `HEAD=7719a01f4191192855ad15faf609d9a6c4cc6609`, **55/55 PASS**, compile exit 0, public privacy scan CLEAN.
- Tests: `tests.test_review666_module_halt_race`, `tests.test_review666_bp11b_export_gate`, `tests.test_modules_gate`, `tests.test_guard2`. Both Notaus/revoke-during-fetch and typed module_export prohibition remain tested on one combined source tree.
- Original ZIP artifact `12715092601`, SHA256 `864b82afc9931a648fb052a60e7392b2e5c6a20c153f8d58a3bb8076f3dc7e57`; ZIP CRC clean, all exit receipts checked, exact head checked. Private Library backup `/V13-Checkpoints/2026-10-27/Review666-Combined-Gates/v13-review666-combined-40462349557.zip` byte-identical and SHA256 reverified.
- No actual network fetch, Qwen inference, model training or Redmi measurement. A final check/filesystem TOCTOU remains open; no security-complete claim. The parent PR667 and PR669 original RED attempts remain preserved.

## Blockers, gates and exact continuation
- PR666 remains stacked on a source harness, not a committed AG5+World integrated runtime. This focused success does not prove full V13 integration. Independent five-way integration and broad-suite baseline comparison are in progress on separate review branches.
- STEP2=`UTILITY_FAIL`, B3=`L1_FAIL`, Body-JEPA=`UNAVAILABLE`, `jepa_weight=0`, `canonical_architecture_complete=false`, `user_full_scope_complete=false`; Redmi not measured.
- Exact focused replay from this branch: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_review666_module_halt_race tests.test_review666_bp11b_export_gate tests.test_modules_gate tests.test_guard2`.
- Next: integrate this review branch with the verified five-way disposable AG5+World+Claude candidate; run cross-feature, broad, source-binding, privacy and phone tests before proposing any production merge. No main merge authorized by this report.
