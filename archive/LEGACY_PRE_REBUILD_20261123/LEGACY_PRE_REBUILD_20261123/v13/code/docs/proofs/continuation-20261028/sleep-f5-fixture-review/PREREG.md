# Independent cross-review preregistration: Sleep A F5 fixture contract

Date: 2026-10-28 UTC. Owner: GPT-6 independent review. Parent PR #796 exact `43b8fede8be8d6db575c16a502be8d8a61a6b304` (review-only, not main). Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` and all newer decisions unchanged.

## Observed RED, before editing

GitHub Actions 40601545744 at exact parent head: 33 focused tests, 3 errors; the 3 errors are from `test_sleep_a_exact_recall_identity_review.py` constructing a `SimpleNamespace` memory stub with only `recall`. New production Sleep A now invokes `memory._verified_rows` to check live F1/F5 authority, so the legacy stub violates the updated collaborator contract. The six exact unchanged Run274 tests and Memory F5 tests passed in this run. No full suite was run (fail-fast). Previous RED 40601124131 remains preserved.

## Hypothesis and change boundary

Do **not** change `sleep.py` or `memory.py` to bypass F5. Update only the older exact-ID regression fixture: retain its deterministic fake `recall` output but delegate `_verified_rows` to a real Memory instance created in setUp. This should preserve all three exact-memory-ID tests, including the negative equal-value cases, without allowing unverified human corrections to pass. Add a separate pinned GitHub Actions workflow to run focused and full Linux software tests and preserve raw exits, privacy and hashes. Original test blob `48a692f5d0d47aece40d5c56d6c2f2ae96ba3c6a` remains in Git history; do not change preregistered Run274 test `a0a62163e48c657df56540b52a6438880b4a5235`.

## Expected evidence and limits

Focused: `test_sleep_a_exact_recall_identity_review`, `test_sleep_memory_authority_run274`, F1/F5 memory and episodic authority, Sleep offline. Full suite only after focused green. Check exact unchanged production blobs `sleep.py=2fa642218712a217a6d55061c9208e2445c0be25`, `memory.py=501c8f43c92f031e034e4b93f4adbd4c67b7edfe`; privacy CLEAN and compile. Negative cases must remain negative; no fake native, Redmi, semantic, learned or whole-system promotion. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age-0 unchanged. Independent review-only branch, no merge, no force-push, no changes to the active PR796 owner branch.

Next after tests: independently inspect CI raw logs, verify remote bytes, report remaining blockers; continue separate blueprint work without claiming acceptance.
