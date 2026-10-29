# Sleep S7 bounded digest backlog handoff — 2026-10-29

## Exact ownership
- Parent PR #1104 head `15732a6237187743c9cc6fe8539fdddfed94c6dc`; draft child PR #1110. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Prereg `ed63151629530b75c0437e2513ee7539901eb105` before test-only `ae0de670e293f21d3de2242b1cc644e30b3e5ff6`, original RED `e1c8a11532241e245ed920b748dba01eefdad665`, then `history.py` `9aa181f880bc1fa122eea96f9bd838b3943700c3`, `sleep_offline.py` `ab6ccce817e6434ad616813721e440d3d0071305`.
- Own only these two source files, new `tests/test_sleep_digest_backlog_20261029.py`, prereg/handoff and two dedicated workflows. No donor changes or force-push.

## Functional change and evidence
- Former digest chose latest64 and advanced until to global last, skipping oldest backlog permanently. New paged native_history selects earliest source-valid complete pairs after `after_id` (legacy latest-window callers unchanged). S7 digest scans bounded chronological settled pairs, halts at incomplete streaming answers, validates through existing native_history source/rule lineage, and advances only through scanned assistant high-water. Intended 150-turn catch-up: 64+64+22, no silent skip; final 96 entries retained.
- Original RED Actions `40901056782`: 4 tests, 1 pass, 2 expected failures, 1 error; artifact `12908942340` ZIP SHA256 `2510fcf9c24c173d62842fabd09ce26d64086c4ba015d91da47cdefc16513356`, CRC clean, privacy exit0. Private backup `/V13-Checkpoints/2026-10-29/SLEEP_DIGEST_BACKLOG_ORIGINAL_RED_40901056782_SHA2510fcf9.zip`.
- Source-only focused/full CI `40901202344` at `783b02f792adcd55a355e327cddab98160c7427e` launched, outcome pending. Full workflow pins CPU torch 2.14.1, transformers 5.20.2, peft 0.21.2 to avoid observed missing-import failures. Never claim GREEN until raw verified.

## Next exact commands
1. Inspect Actions `40901202344` and original raw. `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_sleep_digest_backlog_20261029 tests.test_sleep_offline tests.test_history_lineage`; full `python -m unittest discover -s tests`; privacy `python v13/code/scripts/public_repo_privacy_scan.py --base 15732a6237187743c9cc6fe8539fdddfed94c6dc --head HEAD --no-worktree`.
2. If RED, preserve exact raw and repair; watch for native_history after_id boundary and assistant-final status handling. If GREEN, independent review and private raw backup with SHA256 byte recheck.
3. Continue another canonical utility package; no production merge without review.

## Negative gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 incomplete.
