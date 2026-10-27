# BP1 QAD native-smoke software review — prospective repair note (2026-10-27)

Owner: GPT-6 automation11 independent reviewer; review-only child of PR #682 at `a71121d30fa1b83fa4c9b86b8f5fa3bc5fe710aa`. Scope is only `v13/code/tests/test_bp1_qad_native_smoke.py`, `v13/code/scripts/bp1_qad_native_smoke.py`, a separate **software-only** CI workflow and this scoped proof folder. No model downloads/training, no heavy native runs, no active owner's branch changes.

Observed original RED: Actions 40473645747, software job 122086516186, source a71121d: 10 tests, 1 ERROR (`test_batch_encoding_is_normalized_to_tensor` NameError at nested `class Torch: Tensor = Tensor`); native job skipped. This is a Python test-scoping error, not evidence of a model failure. Preserve the original run unchanged.

Package 1: fix only the test-scoping bug without weakening assertions; rerun all ten software tests, compile and public-repo privacy scan on an isolated review branch.

Package 2: source-bound comparison integrity. Before implementation add negative tests: stale/wrong seed, revision, token budget, registered prompts, schema, gates and falsely claimed training must be rejected by `compare`, not silently summarized. The legitimate `common(...)` reports remain accepted; nonmatching generated response text remains a diagnostic difference, not a model failure. No change to frozen registered cohort/model hashes, four prompts, 24 tokens or seed 13.

Use new software-only CI on this branch (no heavy native job), retain raw tests/compile/privacy output and their exit codes as a GitHub artifact. A software PASS cannot promote any native/utility/Redmi/STEP2/B3/Body-JEPA gate. Negative gates: STEP2 UTILITY_FAIL; B3 L1_FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi unmeasured; full V13 incomplete.

After green CI: independently read original logs, audit the exact remote bytes, then create a review-only PR against PR #682 head branch; no production merge. Next owner should separately resolve the original native smoke and run true pinned source serially.