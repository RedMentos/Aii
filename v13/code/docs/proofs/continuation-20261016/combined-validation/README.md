# Combined working-source validation — 2026-10-16

Final complete discovery:1421 tests,1416 passed,5 skipped,0 failures/errors/expected failures.108.353s wall time. Four skips are absent PyTorch; fifth is optional native Tap/GGUF unittest environment not supplied. The separate preregistered native cohort is run after this suite and reported separately.

First run preserved in unittest.log and initial-summary.json:1420 tests,14 failing/error outcomes caused by two absent sparse-checkout fixture/header paths plus an existing test injection race. Exact M blobs restored for both missing fixtures; all14 related checks then passed. Thread O c9b7eddf supplied exact test-only ResourceGuard pins; deterministic failure/fix and20/20 focused checks in tests-race/. No bodies.py change or weakened assertion.

Parent summary helper initially failed serializing TestCase skip objects after the test runner; corrected helper records IDs/reasons in summary.json. recheck-unittest.log contains the successful full run. No old negative evidence was deleted. The final run includes the parent single-attempt/preregistration guards and combined K/M source drift fix.
