# Run362 — conservative German R4 list arithmetic

Parent: Run361/PR356 `f9696d5574119ee87a31f8aa651e6dbd7c358929`. Review: PR357. Owner: `assistant/run362-listarith-german-20261025`. Only `v13/code/v13/agi/listarith.py`, new test and isolated CI workflow changed.

## RED → GREEN with a second negative-control cycle

Initial exact-head [Actions 40230011576](https://github.com/RedMentos/Aii/actions/runs/40230011576): **22 tests, 12 failures, 1 error** — German sum/max-minus-min questions not recognized. Raw artifact 12611684312, ZIP SHA256 `51b18b0fbdbd62b94fc833806c8eea1ad281e4e1e97f2f681c9d13d712b58d84`.

First fix [Actions 40230087945](https://github.com/RedMentos/Aii/actions/runs/40230087945): **22/22 PASS**. A new adversarial German plural-count test and model-free `ToolStep._propose_list` integration exposed a false positive: “Wie viele Preisgruppen arbeiten zusammen?” was misread as a sum and could wake C3 unnecessarily. Exact-head [Actions 40230159163](https://github.com/RedMentos/Aii/actions/runs/40230159163): **23 tests, 3 failed subtests**; raw artifact 12612634186, SHA256 `6ba257c7aebe1b2d5255935c08020213c6af951dac4238a613b51ceb075e40c1`.

Final fix refuses plural-count wording unless the explicit unit is “Euro”. Exact-head [Actions 40230210867](https://github.com/RedMentos/Aii/actions/runs/40230210867) on `19dd6f3a5b38d5639fb59950da6b4833d88fcb81`: **23/23 PASS**, privacy **CLEAN**; raw artifact 12613150032, SHA256 `9f69daf89d8536f188a0883f0283bff6d740996490fb71997dd3e9774ea2439f`.

## Actual behavior and limits

German explicit sums and largest-minus-smallest questions now use the existing fixed `list_arith` operation; counting and ambiguous differences abstain. Original English R3 wording and exact source-number guard still pass. Model-free ToolStep integration verifies no C3 read while the tool is disabled, a typed proposal when enabled, and no C3 read on a plural-count false positive. This does **not** prove native German C3 value extraction or Redmi performance. Tool enabling, Age, prohibitions, approval and learning gates remain unchanged.

Source blobs, all raw receipts, central BUILD_STATE snapshot and next command are in `BUILD_STATE_RUN362.json`. Central `BUILD_STATE.json` is untouched to avoid concurrent-owner conflict. Next: registered native German value-reading evaluation or an independent functional package. Local rerun: `cd v13/code && python -m unittest -v tests.test_listarith_german_run362 tests.test_listarith tests.test_listarith_signed_source tests.test_r4_rule_r3 tests.test_r4_rule_question_only` with isolated `numpy==2.3.5`, `prompt-toolkit==3.0.52`.
