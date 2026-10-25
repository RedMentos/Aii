# Run304 — source-closed, restorable V13 backup snapshots (preregistered 2026-10-25)

Owner: GPT-6 automation, independent of active Run302 Operator, Run303 Budget, Run297 Context OS native owners. Base exact commit `5c4a655e521ff939ee4b00fc03d0be54c3db62da` (PR301 Run302 head). Owned: `v13/code/v13/backup.py`, new `tests/test_backup_source_closure_run304.py`, dedicated CPU workflow, this scoped proof folder. No changes to Runtime, Store, learning, Canon, registered model/seed/cohort, thresholds, or user authority.

## Observed defect and test contract (RED first)

Existing `backup()` copies SQLite then blob tree without checking that every **live source row** in the snapshotted DB has a matching plain or archived blob. `unpack_verified()` checks the archive's *self-reported* file hashes but not the logical SQLite→source-blob closure. A partial snapshot or repacked archive with a consistently rewritten manifest can therefore pass archive verification yet fail later source retrieval. Tests must reproduce this using actual Runtime/Store SQLite and synthetic nonprivate text.

1. Valid plain and archived source snapshots remain accepted, with exact SHA256 and restorable SourceRefs.
2. Deliberately omit a live source blob during snapshot copy: `backup()` must fail closed, publish no final tar or partial tar, preserve live Store.
3. Corrupt a live plain or compressed source blob: backup must fail closed.
4. Repack a valid tar **without** its live blob, update the manifest hashes consistently: `unpack_verified()` must refuse before a restore swap.
5. Deleted/revoked sources need not retain blobs; no resurrection, and original source records/gates stay unchanged.

Implementation candidate: read-only closure validation against the snapshotted SQLite, checking only distinct nondeleted `sources.hash` entries. Prefer plain blob when both variants exist, otherwise verify zlib archive with bounded decompression. Hold `store.mutex` while snapshot and file copies are staged, then verify stage before publishing. Revalidate on unpack after the archive's own hashes, before restore swap. Preserve existing backup manifest format, recovery journal, models-included=false, and all original negative gates.

Claim limit: **software/SQLite integrity only**. No live phone measurement, no native model execution, no STEP2/B3/Body-JEPA/JEPA utility promotion. RED and GREEN workflow outputs must be retained, including failures. Exact next command after RED: implement closure guard in backup.py and run dedicated workflow + existing backup/restore tests, then independent review and durable BUILD_STATE checkpoint.