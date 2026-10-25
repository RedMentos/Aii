# Run124 cross-review — recovered queue vs pending phone STOP

Base Run123 PR #154, which had 25/25 Linux software tests but a reproduced startup ordering gap. New deterministic test-first CI (Actions 40148004332) **3/3 FAIL** before fix: pending NOTAUS/STILLSTAND did not bind before Runtime returned. Full raw RED log retained.

Minimal Runtime change (source blob a691d27 → b80fe3e4): apply existing `phone_halt.apply_once(self)` after components/SleepRuntime are initialized and **before** coordinator thread starts; no new safety policy. If a stop-file preflight raises, close Store and never start worker. When standstill creates a special wake event before the worker exists, bind its worker field to the actual coordinator thread before start. Explicit user stop ownership preserved.

Post-fix Actions 40148069028: **28/28 PASS** (3 new, 6 Claude Widget/guide, 2 Run121 CLI, 3 Run86, 14 standstill); official privacy CLEAN; Python compileall PASS. Recovered exact-copy turn stays queued under preexisting STILLSTAND and finishes only after explicit release. Preexisting human stops are not cleared.

**Scope:** Linux software/SQLite/worker tests, not Redmi/Termux widget latency, native inference or full V13 acceptance. Startup notice currently captured as `_startup_phone_halt` but not displayed by UI; next package. Canon SHA remains 218464b12a2d27d92524c751922fa8e1c3fb0ea7. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, DS2 H2 FAIL, V13 INCOMPLETE unchanged.
