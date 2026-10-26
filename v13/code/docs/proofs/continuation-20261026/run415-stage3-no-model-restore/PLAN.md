# Run415 — no-model stage3 restore and one S_s20 native arm (source-only preparation)

2026-10-26. Owner GPT; branch stacked on Run413 review head 0aa6125. Not main. Run413 original native owner Actions 40258333913 at f7fe013 is still in progress; no P_s20 result is assumed.

## Prerequisites
Exact Run413 84-row native O_s20+P_s20 GREEN and independently verified no-model work artifact; raw Run411 report, export manifest, original ZIP and model hashes bound. Do not execute S_s20 until those prerequisites exist. The Run413 original 1.46GB ZIP remains at its original artifact, never reuploaded. Native owner must be exclusive; use the same GitHub concurrency group. No new model revisions.

## Implementation package
Build a read-only verifier and atomic fresh work restore from Run409 no-model export (Run413 independent gate), omitting only the export manifest. Stream every regular-file SHA; reject symlinks, hardlinks, traversal, extra/missing files, changed size or model-weight paths. Preserve all O/P native receipts, original failed attempts and frozen Run394 cohort. A separately opt-in `--execute` may use unchanged Run397 runner to run exactly one S_s20 arm and export a new safe no-model checkpoint even on RED. No native run or gate promotion in source-only tests.

## Acceptance
Synthetic adversarial restore tests + actual Run413 artifact verification when available, then one real pinned Linux-native S_s20 (42 additional rows, 126 cumulative if valid), no model bytes uploaded. Preserve failed attempts and all negative gates. STEP2, B3, Body-JEPA, jepa_weight, Age and Redmi remain RED/OFF until their original acceptance proofs.
