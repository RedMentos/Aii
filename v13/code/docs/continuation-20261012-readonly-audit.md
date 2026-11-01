# V13 read-only evidence audit — isolated continuation checkpoint

Date: 2026-10-12. Review branch: `assistant/evidence-streaming-20261012`.
Based on verified authority source: `c1663f87f5e38aef6b456825410662164617e79c`.

## Newly implemented
- `v13/code/scripts/sealed_storage_integrity_audit.py` reads the existing `v13-sealed-storage-parts-v1` manifest/parts, streams at most 1 MiB of part data per read, checks every declared size/hash and full SHA-256, rejects malformed descriptors, symlinked parts, missing files and changed metadata, and can reject unlisted parts with `--strict-directory`. It does not reconstruct/modify evidence unless separately instructed to write a diagnostic receipt.
- `v13/code/tests/test_sealed_storage_integrity_audit.py` covers corruption, exact/full hashes, multiple sizes, symlinks, unlisted parts, immutable receipts, malformed integer types.
- With the previous isolated candidate tests, **16/16 PASS** in a staged source-tree layout using `PYTHONPATH=. python -m unittest -v tests.test_sealed_storage_streaming_candidate tests.test_sealed_storage_integrity_audit`. Python 3.13 on Linux; neither Redmi nor active training.
- CLI proof on 1,048,607 synthetic closed bytes: the intact archive returns `INTEGRITY_PASS_NOT_UTILITY_PASS` with matching whole hash and part count 2. After overwriting the last part with `BROKEN`, the command exits 1, emits `INTEGRITY_FAIL` and does not publish any successful receipt for the corrupt archive.
- Only **new standalone files**, no edits to production V13 runtime, source-handoff candidate, frozen 121 Python sources, historic evidence, gates or roadmap.
- Verified read-back GitHub blob identities match local Git object hashes:
  - `sealed_storage_integrity_audit.py`: `0655710a363b062d26a704a7fdc96017403ad4df`
  - `test_sealed_storage_integrity_audit.py`: `fb7807cae92f06ef174877c1ebb18f414df4989e`
- Local independently re-hashed ZIP snapshot: `V13_Storage_Checkpoint_20261012_v3.zip`, SHA256 `b2ab4a962c214a7279ea03bd34b7d9eae7ad022cac62edc7f9b9264b4ba05103`, also copied into Library `/V13/`.

## Intended continuation for Work/Codex
1. Re-read `AGENTS.md` and `v13/code/docs/HANDOFF_CURRENT.md` and check remote authority HEAD before work. Review this isolated branch against authority, cherry-pick only when active preregistered SourceHandoff tests permit. Candidate storage tools are opt-in; they have not replaced the production saver.
2. Run audit against the **real 12 published part files**, at `v13/code/docs/proofs/continuation-20261011/action-native1875-recovered-20261012/parts/manifest.json`. The legacy recovery report declares 1875 native rows, 118 batches and NPZ hash `09fde379793ea8c4a63268df729a33b4b98a3f4f90f3eeee2dec4a83a10b5843`, but this new independent audit was **not** run against those actual part bytes here.
3. Resume the **original** source-handoff 16-case preregistered ablation with actual weights and invariant bindings; original NumPy seeds 13/21/34, Dream2 B40 2/15, then isolate and integrate the existing approval-reader/firing fixes. Original STEP2 UTILITY_FAIL and B3 L1 FAIL unchanged.
4. Preserve locally and remotely each proof and restart point; avoid concurrent mutation of shared frozen status, force-pushes and claiming hardware/utility results without evidence.

`canonical_architecture_complete=false`, `user_full_scope_complete=false`.
