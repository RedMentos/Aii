# Sleep B queued Dream validation F5 authority — dependent preregistration

UTC 2026-10-28, GPT-6 review owner. Parent exact PR797 `c9de3de39a6b11c650e32dc2ffbb7fb7ee0a66ee`, CI 40602893223 pending at preregistration; do not edit production before parent passes. PR797 descends from Sleep A/B F5 PR796, which is review-only and not main.

Prior verified historical Run275 / PR275 (`codex/dream-validation-authority-run275-20261025`) already proved a related RED and narrow GREEN on the older Run274 chain. Its exact source `sleep.py` blob `a144cd40ba46450af3329f598b1bc6ea7464ea94` is **not** to be wholesale copied, because the newer PR796 Sleep A exact-ID and Dream B F5 seed guards must remain. Original six-case test blob `152933e4afaf0e7d1defd991ab3e5c3267315a00` may be reused unchanged. Prior Run275 focused 80/80 PASS, full suite NOT_RUN_IN_RUN275. Historical RED retained.

## Narrow proposed integration

First import unchanged Run275 tests and run RED on the current source; capture raw failures. Then transplant only `SleepCycle._memory`, `_neighbors` and `check_hypothesis` F5 read guards, retaining current `_probe`, `sleep_b`, queue policy, Dream fact-write zero, and all other production code byte-for-byte. Verify a revoked queued Dream anchor becomes STALE, revoked neighbor no longer marks SUPPORTED, independent valid hypotheses survive, and no factual write or native/Redmi claim. Use pinned Actions for focused/full software and privacy. No tests on mocked whole runtime.

Separate follow-up question (do not silently fix without a test): `validate_hypotheses` currently caches any verdict other than UNVERIFIED forever; even an F5-aware `check_hypothesis` will not be called after later revocation. Add a separately registered cache-revalidation test/package if confirmed. Do not conflate with Run275's direct `check_hypothesis` contract.

Preserve all Canon and user decisions, original failed attempts and unchanged registered model/source/seed hashes. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age-0 approval unchanged, V13 incomplete. This is review-only; no merge or force-push. Next: wait for parent exact CI, add unchanged test RED, narrow fix, focused/full tests and remote proof.
