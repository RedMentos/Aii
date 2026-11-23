# Native sparse firing: opt-in execution observations

The memory hook can now report per-request, per-slot counts of actual floating-point residual changes and entity-guard blocks. Enable it only in diagnostics with `V13_MEMORY_AUDIT=1`, or run `scripts/fast_trace_compare.py ... --audit-firing`. No query, token or fact value is written into these audit records. Exact remains present. Counts do not prove recall, usefulness, retention, leak safety or permission to omit Exact.

Every HTTP prompt starts a fresh request number and counter set. The collector reads only that completed request's stderr window. Missing begin markers, no evaluated rows (including possible cache reuse), wrong dimensions, malformed records, interrupted cumulative sequences and multiple requests remain UNAVAILABLE. Initialization graphs before the first prompt do not touch uninitialized audit vectors. Diagnostic failure does not erase an already obtained model answer.

Rebuild the memory runner with `python3 -m v13.memory_server --home ~/v13 build`. Its manifest now binds the launcher and its adjacent shared libraries. Older manifests with actual shared libraries must be rebuilt; the ordinary runner is used until the binding matches. Healthy warm runners watch library metadata and reload on changes. The benchmark's resume binding includes shared-library hashes, so a matching launcher alone cannot merge observations from different hooks.

The real Linux check in `docs/proofs/continuation-20261011/native-firing-smoke-library-bound/` uses pinned LFM2.5-350M QAD Q4_0 and an explicitly SYNTHETIC three-row artifact: a small nonzero residual, an impossible entity guard, and zero values. Three queries in each arm produce identical answers and prompt-token counts with audit off/on. Only row 0 changes the output; row 1 is guard-blocked; row 2 does not change it. This proves diagnostic execution and request isolation, not learned memory quality or phone performance.

Earlier startup failures and their raw reports/logs remain preserved. The first full-suite rerun had an unrelated process-identity test failure; its log remains preserved, and the isolated process-recovery checks subsequently passed. The final extracted-package result is recorded separately in the webchat checkpoint.

Next: evaluate the unchanged frozen fact/paraphrase/near-miss/retention corpus against real trained memory and all Exact/Trace/Combined/selective arms. Do not promote selective delivery from this synthetic diagnostic fixture. STEP1/STEP2 and the complete Canon remain unfinished.
