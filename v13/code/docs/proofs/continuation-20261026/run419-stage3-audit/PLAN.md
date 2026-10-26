# Run419 — independent actual 126-row S_s20 postflight gate, no-model only

2026-10-26 · owner GPT · branch `codex/run419-native-stage4-gate-20261026`, stacked on Run418/PR414 at `7548c3b7a6db9189c1a3a94f447d9414a92bb3b4`. Not main. Run418 native S_s20 Actions 40260347495 is the sole heavy owner while this source-only package is prepared.

## Why

A successful Run418 native wrapper must not be treated as whole STEP2 completion. Before scheduling the next O_s21 arm, an independent verifier must re-open the exported no-model tree and independently check every source/receipt byte, all three O/P/S 42-row reports, the frozen Run394 preregistration and the exact pinned runner/model identity fields, while preserving all canonical negative gates.

## Implementation

`scripts/run419_verify_stage3_native.py` accepts the actual Run415 S_s20 report and the restored hash-closed Run409 no-model export. It checks the Run415 126-row nonpromoting status, all exported files, symlinks/hardlinks, model hashes, directory inventory, manifest SHA, progress SHA and frozen fixture manifest. It then calls unchanged Run397 `validate_completed` separately for O_s20, P_s20 and S_s20, requiring 42 rows each, exact receipt equality and the pinned runner SHA. No models are downloaded or inference launched. Synthetic adversarial tests cover wrong 41-row receipt, false stage/JEPA/Redmi gate, tampered file, extra file, traversal and missing native evidence. Failed/partial native reports stay RED; their original evidence is not deleted.

## Proof limitations and next

Source-only tests are not actual native postflight. Only after Run418 S_s20 finishes and its small raw and safe-work artifacts are independently downloaded, SHA-verified and restored through the Run418 importer may this verifier establish actual 126-row evidence. The next native arm is O_s21, but must be scheduled separately after 126-row GREEN, installed pinned models and exclusive owner. Full STEP2 requires the remaining six arms and original paired utility gate. STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured and V13 incomplete remain unchanged.

## Lossless transport to the independent gate

`run419_import_stage3_artifact.py` accepts a pinned outer Actions ZIP SHA256 and actual Run415 S_s20 report, rejects extra/missing/duplicate/traversal/symlink/oversized members, reconstructs only directories listed in the hash-bound Run409 manifest (Actions may omit empty entries), streams all file SHA256 and CRC, calls the full independent 126-row verifier on the staged tree, then atomically publishes a fresh work tree. New source-only tests exercise transport failures and the three receipt calls. This is not a second native S_s20 execution.
