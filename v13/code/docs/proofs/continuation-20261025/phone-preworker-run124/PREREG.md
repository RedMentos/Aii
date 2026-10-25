# Run124 — deterministic pre-worker Widget stop gate

2026-10-25 UTC. Base Run123 PR #154 exact head `d3aa8dde0f521ecd3f4920820743a3d3bbad12bc`. Owner: **narrow pre-worker stop-file handling in `v13/code/v13/runtime.py`**, new `tests/test_phone_halt_preworker_run124.py`, new workflow/proofs. Run123 UI/operator/Claude files read-only; no other organ/model/Canon changes. No active native jobs.

**Observed Linux counterexample on Run122 source:** persisted exact-copy turn + preexisting `control/STILLSTAND` file; Runtime created an assistant FINAL about 43ms after construction while STOP request remained pending (watcher starts only after Runtime). Run123's UI hooks still start after Runtime worker. This is a real ordering gap, not a device measurement.

**Test-first RED** on Run123 source: require pending STOP to bind in `Runtime.__init__` before coordinator thread starts; recovered turn must remain pending, confirmed_still eventually true, explicit human release resumes and yields exact copy. Also pending NOTAUS before Runtime returns and preexisting user stop parts survive widget release. Preserve raw RED.

**Narrow fix plan:** after full Runtime components and SleepRuntime are initialized, but **before** constructing/starting `self.worker`, call existing `phone_halt.apply_once(self)` (it uses same typed stop functions). If it creates standstill `_SeenEvent`, bind `wake.worker` to the newly created thread before `start()`, so parked/confirmed_still is not spuriously false. If preflight fails, do not start worker (fail closed). No change to queue TTL, age/learning, model, registered cohorts, or safety gates. Re-run all 3 new + 25 inherited Linux tests and privacy. Do not claim Android/Redmi latency.

Original gates: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE.
