# Run128 — source-bound-safe preworker Widget stop

2026-10-25 UTC. Base Run123 PR #154 `d3aa8dde0f521ecd3f4920820743a3d3bbad12bc`, not Run124/125. Run126 full-suite audit PR #157 found a critical correct SourceHandoff failure: modifying frozen `v13/runtime.py` caused 63 errors. Run127 owns Widget installer quoting separately. This package owns ONLY `v13/phone_halt.py`, `v13/__main__.py`, new test/workflow/proofs. Runtime, UI, canonical blueprint, cohorts, model bytes, operator and installer are read-only.

Problem: recovered accepted turns can execute before a pending STILLSTAND file is consumed by UI watcher. Proposed proof: CLI preflight consumes request and durably engages existing stop gates **before Runtime constructor starts worker**, without changing frozen runtime.py. Need preserve preexisting human stop ownership, avoid partial writes on failure, and not drop pending file before durable commit. A direct Runtime(home) constructor is not covered by CLI preflight and must not be claimed as such.

Test-first RED: CLI pending recovered turn, explicit preflight STILLSTAND/NOTAUS/both, already-held user flags, unreadable state refusal, idempotent retry. Source-bound hash of runtime.py must remain Git blob `a691d27bd0772a4fa1f03d57ec90663237bf6825`. Run inherited stop tests and SourceHandoff/NativeFiring focused checks, then bounded full-suite. Preserve all raw failed attempts. No native/Redmi/model utility claim.

Original gates unchanged: STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE.
