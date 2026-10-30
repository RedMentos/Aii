# C2 prior native evidence scope alignment — 2026-10-30

The new isolated `Runtime._route` provenance probe must **not** be described as the first V13 native Needle/C2 execution.

- Earlier PR #1191, Actions `40986013453`, already verified a genuine pinned Linux native **Needle3 CLI** `select_processing` call: route `both`, 0.417 s, model SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`, CLI SHA256 `5eb163c5ed33bd914c103ef8eba2134c7bb2d97bafafdd69f410a4a3100e8c37`, confidence 0.9932 **uncalibrated**, original ZIP SHA256 `363cac72b92ea781614cf294514c85362d9cfbef555ea8d53cf9dbffa15740a6`. This is C2 native CLI, not the full Runtime route.
- PR #1192, Actions `40987192595`, already verified a connected Age0 Linux **serial** JEF/C2/C3 and B1/B2 vertical, 31/31 software tests and native original ZIP SHA256 `ad961abb8eea8d567f58cbc4f1fed67f7a79920e36564bb5527b7ea08fa4f3f7`. It did **not** prove one all-organs semantic final answer, STEP2 complementarity or Redmi.
- The new C2 pilot's distinct, narrower missing proof is `Runtime._route(route_override=auto)` invoking the native `needle-worker` **inside** a stored current-session `ExecutiveControlContext`, recording whether native advice actually selects a route and whether its worker is reaped. The software preflight alone does not establish this; native launch waits for STEP2 v3's heavy job.

Do not double-count these independent cohorts or treat C2 invocation, C2 advisory route selection, and integrated semantic utility as interchangeable. All original pins and negative gates remain.
