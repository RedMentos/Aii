# Run402 — safe source-only restore of Run401 full-cohort native stage archive

2026-10-26. Owner GPT continuation, independent source-only package. Base Run401/PR396 exact head `c0facf60c3286064e15bc06de104c85d9344382a` (stacked review, not main). Own only new `v13/code/scripts/run402_stage_restore.py`, `v13/code/tests/test_run402_stage_restore.py`, `.github/workflows/run402-stage-restore.yml` and this proof directory. Do not mutate Run401 running workflow, frozen Run394/395 source or Run397 runner. Run401 native Actions `40250662450` is a separate serialized owner and is active at planning time; Run402 never downloads models or starts inference.

## Problem

Run397 can resume a 378-row native STEP2 cohort only if the prior completed arm and append-only event journal survive a fresh GitHub Actions runner. The Run401 artifact is not yet completed/observed, so **do not invent its ID or digest**. A staged workflow must verify the observed archive SHA, CRC, every SHA-manifest entry, exact Run401 source head, exit statuses, full frozen cohort identity, one 42-row O_s20 receipt, row/consumer/source/model hashes, and no gate promotion before restoring the work tree. Never treat a synthetic archive as native proof.

## Acceptance

1. Read-only source utility `inspect_archive` rejects wrong digest, traversal/symlink/duplicate/oversize, missing/unhashed/tampered members, wrong source head, failed native/preflight exit, incomplete progress or wrong source/model/row/consumer receipt. It must preserve all original bytes, not silently skip partial attempts.
2. `restore_archive` copies only the verified `run401-full/` tree into a **fresh** destination, no overwrite or symlink traversal, and verifies restored SHA bytes. It never executes native inference or alters canonical gates.
3. Synthetic adversarial tests (including a complete native-shaped archive with 42 synthetic rows) and isolated CI with inherited Run394/396/397/398/400 tests. Record raw RED/GREEN and privacy. A real Run401 artifact can be audited only after observing ID/digest.
4. Preserve STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA/jepa_weight=0, Age0/approval unchanged, no Redmi proof, whole V13 incomplete.

## Next

After Run401 finishes, download its exact observed artifact, run this verifier, review and preserve any RED, and only then launch stage2 native `P_s20` with Run397 `--full --execute --max-new-arms 1` from the restored work tree. Do not start competing native jobs.