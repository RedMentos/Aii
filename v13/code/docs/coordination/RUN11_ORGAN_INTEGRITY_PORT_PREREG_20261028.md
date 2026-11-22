# V13 Run11 — organ snapshot/restore integrity integration preregistration (2026-10-28)

## Immutable source and owner
- Owner: this isolated automation review branch only. Parent is PR #919 at exact `6d1cb49488fa5f5876a8142296dc119e3a7c6f0e`, **not production main**. No parent or foreign branch will be modified.
- Donor: independently reviewed PR #440 / Run441 at `9db3f09abd76f3c156e43b68528b3dea1fe8705c`, with preceding PR #42 immutable artifact repair and PR #360 path validation. Source file `v13/code/v13/organ.py` donor Git blob `aa925d5d4128974c3e1aaf64e58d0e4310e5dfa1`, base blob `8ba800f94f17d1df2347d093279d799aa612417c`. Donor RED/GREEN evidence described in PR #440; independently recheck CI in this combined tree.
- Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` and all newer user decisions remain binding. This is an organ checkpoint safety repair, not a new learning/age grant.

## Reproduced source-level gap before edit
The parent `organ.py` still copies snapshots into a flat basename directory; two components with different paths but identical basenames can collide. Its `check` can label damaged backup bytes restorable; `restore` copies into existing artifact paths before checking the full generation plan and commit, potentially modifying another organ's live bytes on a later failure. Snapshot role/id traversal and symlinked bridge root/files are not refused. These are source-code findings; no new RED runtime claim until source-pinned tests execute.

## Implementation and tests
Port the **exact donor** `organ.py` blob from PR #440 and its three isolated test suites `test_organ_artifact_integrity.py`, `test_organ_path_safety_run365.py`, `test_run441_organ_bridge_symlinks.py` into this child, retaining existing `test_organ.py`. Do not touch frozen runtime.py, source/model registries, seeds, cohorts, or operator authorization. Check donor file/test blobs byte-for-byte on remote.
- Expected source-only tests: original organ behavior; corrupted active/missing backup, cross-organ path collision, basename collision, rejected commit without changing existing files, role/id traversal, symlinked root/bridge file/backup. Restart test proves active artifact consistency.
- Source-pinned isolated Linux software CI: focused organ suites then full `unittest discover`, `compileall`, privacy scan and diff checks. Retain original logs, exit statuses, source SHA256 in Actions artifacts. Avoid native/model jobs and do not enter TP27 native shared concurrency group.
- Independent review after CI: compare donor and new blobs, check negative gates and that any source-only PASS is **not** native/Redmi proof. Preserve any RED.

## Non-promotion and next work
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 incomplete. This package cannot satisfy STEP2 12-arm, B3, learning utility, or whole-system acceptance. After a verified checkpoint, continue the next authorized independent Canon package or audit pending original TP27 raw; do not stop because this patch passed.

## Recovery command
`git fetch origin assistant/v13-run11-organ-rollback-integrity-integration-20261028; git checkout assistant/v13-run11-organ-rollback-integrity-integration-20261028; cd v13/code; PYTHONPATH=.:tests python3 -m unittest -v tests.test_organ tests.test_organ_artifact_integrity tests.test_organ_path_safety_run365 tests.test_run441_organ_bridge_symlinks; PYTHONPATH=.:tests python3 -m unittest discover -s tests -p 'test_*.py' -q`

Remaining execution budget UNKNOWN.
