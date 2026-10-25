# Run363 — strict local list-row fast arm before C3

Parent: Run362/PR357 `90d142ea3ca8e0cfcbe4ba8a3bb82584057bb1a4`. Review: PR358. Owner: `assistant/run363-listarith-fast-rows-20261025`. A JEF/ToolStep performance-path candidate, **not** a native C3 latency measurement.

## RED and preserved failures

Initial exact-head [Actions 40230383476](https://github.com/RedMentos/Aii/actions/runs/40230383476): **25 tests, 1 failure, 8 errors**. The new strict row parser was absent and ToolStep woke C3 for simple source rows. Raw artifact 12612479951, ZIP SHA256 `6b3ce01dbcc6190e977c8c33177f91dbc74e568371da238e249635f3ac3ee9d3`.

A source-writing mistake was caught, **not concealed**: JavaScript `String.replace` interpreted the Python regex's `$'` as replacement syntax and truncated the inserted source. [Actions 40230466453](https://github.com/RedMentos/Aii/actions/runs/40230466453) failed at Python compile; raw artifact 12612044022, SHA256 `fc7c8f6c7cfaf966417bc5704e7f914424775cc8bc1745711ebaca874beeaf8a`. Restored exact parent bytes and reapplied the change with a callback-based replacement; diff verified.

The next [Actions 40230529723](https://github.com/RedMentos/Aii/actions/runs/40230529723) had **25 tests, 1 failure** because Run362's former C3-call observation was now obsolete for exact rows. The Run362 historical branch remains unchanged; only the stacked Run363 test expectation was updated to require **zero** C3 calls on the exact-row case. Its counting veto remains, and Run363 separately asserts **one** C3 call on ambiguous rows. Raw artifact 12612153937, SHA256 `684493c8288d657316a299cd2f8e617d94e5171a61b4defe45e310956a4e83db`.

## GREEN

Final exact-head [Actions 40230605773](https://github.com/RedMentos/Aii/actions/runs/40230605773) on `e049d9a4b2855028aeb1b21065cea67f67f0030a`: **25/25 PASS**, privacy **CLEAN**. Raw artifact 12611964509, ZIP SHA256 `4bcb7457da2545a5a332c620e28536397fdb0cd40215ac7bf838499c4466df8a`. Run101 ToolStep and Run362 German wording workflows also passed at this exact source.

`listarith.parse_explicit_rows` accepts only unambiguous named integer rows (max 8), rejects decimal/leading-zero/duplicate/incomplete/stray-number inputs, and ignores clearly marked summary lines. `ToolStep._propose_list` tries this deterministic path **only after** the existing human tool-enable and prohibition checks; all uncertain formats retain the typed C3 fallback. The original source-number guard still runs before a proposal. Age, approvals and tool execution policy are unchanged.

## Limits and continuation

No actual model wake or latency was measured, no Redmi proof, no native German extraction or STEP2/B3/Body-JEPA promotion. Old registered cohorts are historical; this source is a prospective candidate. The scoped `BUILD_STATE_RUN363.json` records source blobs, failed attempts, raw hashes and next command. Central `BUILD_STATE.json` remains untouched to respect other owners. Next: test additional adversarial source layouts and independently continue the binding blueprint. Rerun: `cd v13/code && python -m unittest -v tests.test_listarith_fast_rows_run363 tests.test_listarith_german_run362 tests.test_listarith tests.test_listarith_signed_source tests.test_r4_listarith_live` with isolated NumPy/prompt-toolkit.
