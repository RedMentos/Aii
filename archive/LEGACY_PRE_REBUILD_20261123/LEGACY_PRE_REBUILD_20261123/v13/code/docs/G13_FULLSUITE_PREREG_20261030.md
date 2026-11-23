# G13 cumulative independent unfiltered software review (2026-10-30)

Owner GPT-6; parent review-only G13 #1285 checkpoint 9d14c3cc0ffeacf3ac7fc2c8cffedae9b6ea5bb6. Frozen Canon SHA-1 Git blob 218464b12a2d27d92524c751922fa8e1c3fb0ea7. Both G13 patches are source-only candidate, not production merged.

Before any run, preregister exact command: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest discover -s tests -p 'test_*.py'` with V13_NO_AUTOSTART=1 and NO_MODEL_DOWNLOADS=1; isolated pinned numpy 2.2.6, CPU torch 2.5.1+cpu, transformers 4.44.2, peft 0.13.2, psutil, PyYAML, Pillow and prompt-toolkit 3.0.52. No native model download or runner execution. Collect complete stdout/stderr, exit code, pinned dependency imports, git HEAD, source blob hashes, compileall, privacy scan, diff --check, SHA256SUMS and original raw artifact regardless of outcome. Fail the workflow if any stage fails.

Historical Run34/Run37 source-pin failures from Run13A #1281 are known and MUST remain RED if they recur; do not edit tests, freeze hashes, skips, expected outcomes or acceptance gates to obtain GREEN. Distinguish a preexisting baseline failure from a new G13 regression by comparing #1281 original unfiltered evidence and the focused G13 successes. No synthetic/software evidence promotes STEP2, B3, Body-JEPA, jepa_weight or Redmi. Whole V13 incomplete.

Next exact command: run the new branch-pinned Actions workflow, inspect all stage conclusions and artifact metadata, preserve failures and update scoped BUILD_STATE. After this review continue substantive C2/C3/B2 comparative utility and remaining Canon implementation rather than only further scheduler hardening.
