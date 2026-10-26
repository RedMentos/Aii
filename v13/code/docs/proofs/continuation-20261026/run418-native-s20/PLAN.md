# Run418 — actual P_s20 GREEN, lossless Actions artifact import, then one S_s20

2026-10-26 · owner GPT · review branch `codex/run418-native-s20-safe-import-20261026` stacked on Run416/PR412, not main. Native concurrency group `v13-native-c3-run131-serialized` shared with Run413.

## Newly verified real evidence

Run413 immutable source `f7fe01393801c852aa3797973bda0e81b14069ac`, Actions 40258333913 SUCCESS (2026-10-26 02:35 UTC), actual `STAGE2_NATIVE_PARTIAL_NO_PROMOTION`, **84/84 O_s20+P_s20 rows**, no errors, all original gates negative. Raw artifact 12624511151 SHA256 `3c554e654bc62ba0a4979c5c89b1c9a43d6ce86c4bf16933d5a1b3d709fdf5a5`. Safe no-model artifact 12624057201 SHA256 `bb2bc545ce72b30657f36cc605e4a6b2c3e74b2085aea8c679ccc31062b7089a`. Raw report binds export manifest SHA256 `f082290e6e425e8bbc03be0df1833be54978278327f6221fa5acb83bae0656f5` and progress SHA256 `a415c84345ecedf1e63fc3e429ea337979841cb7a5f04efa977ee5e461501fb1`. Independent local inspection of downloaded exact artifact: 99 regular files, 78,197,324 bytes, no unlisted files, all manifest hashes match.

## Observed transport incompatibility (not a native failure)

The uploaded GitHub Actions artifact ZIP does not preserve empty directory entries. Eight declared empty directories were absent from the downloaded ZIP; calling the unchanged Run413 independent export verifier directly on its extracted files raised `DIRECTORY_INVENTORY_MISMATCH`. Restoring exactly those eight empty directories from the hash-verified Run409 manifest made the unchanged verifier return `RUN413_EXPORT_VERIFIED_NATIVE_PARTIAL`. This is transport loss of empty dirs, **not** permission to weaken the original inventory check.

## Source package and tests

New `run418_import_no_model_artifact.py`: pin the outer Actions ZIP SHA256, reject unsafe/duplicate/oversized/symlink members and extra/missing files, bind the inner manifest hash to the actual Run413 report, reconstruct only manifest-declared directories, stream and verify all file SHA256/CRC, call the unchanged Run413 gate on the reconstructed tree, then publish it atomically to a fresh destination. Synthetic adversarial tests cover missing/extra/traversal/duplicate/symlink/hash/report and omitted empty dirs. Initial source CI RED at 87d3c38 (33 tests, assertion 6 != 1: test incorrectly counted every ZIP-omitted directory entry as empty); fixed reporting distinction at bf8cefd, without weakening verification. Exact-head Actions 40260220484 SUCCESS: **33/33 source-only tests PASS**, privacy CLEAN, raw artifact 12624392222 SHA256 `0d89a506024bf52c2cd10a77f32d27b0404e30c179fbac20bc751fab973fe35a`.

## Native S_s20 workflow

`.github/workflows/run418-native-s20.yml` is separately triggered only by its own file path and serialized with the Run413 owner. It verifies immutable Run413 native/source GREEN and both artifact hashes, installs pinned public models and b10964 runner, imports the exact safe-work ZIP, uses Run416 preflight and unchanged Run397 to execute **at most one S_s20**, then exports no-model work and closes small raw evidence even on RED. Only 126 actual validated rows (O/P/S, 42 each) can satisfy the native success postcondition. Failed attempts are never discarded. Do not reupload the original 1.46GB model-bearing artifact.

## Gates and next steps

Native S_s20 result must be read from actual Actions logs and raw artifact; this document does not assume success. After it completes, independently reverify all exported bytes and 126 per-arm receipts, then continue remaining six arms or record the exact blocker. STEP2 remains `UTILITY_FAIL`; B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi unmeasured, whole V13 incomplete. Do not promote any of these based on 126 rows.
