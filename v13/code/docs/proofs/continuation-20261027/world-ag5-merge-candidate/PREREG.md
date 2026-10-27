# Two-parent World-JEPA + AG5 integration candidate — prereg 2026-10-27

World parent PR #658 exact `df3d690a34aca83e4da96e40c08f8bfb81e5d229`, AG5 parent PR #648 exact `c615497384dc5519be59232451895ca443ce9e45`. Both are review-only. Previous exact read-only merge audit found only `scripts/handy_pflicht.py` and `v13/operator.py` as content conflicts; original 8 stage/marker blobs and SHA hashes are backed up privately.

## Candidate resolution, no owner overwrite
- Take AG5 `handy_pflicht.py` V2 as strict superset of World V1: preserves six stages and adds atomic resume, evidence integrity, process cleanup.
- Take AG5 `operator.py` as baseline to preserve bounded chats/search/export, language selection, idle locks, self/Context OS/AG5 commands. Graft World `:world shadow` exact read-only SHA-bound guarded handler, `:ersetze` human route supersession, `:effort detail|gist` one-body modes, HELP entries and `atomic_write` import. Keep origin, READ_LOCAL/notaus/announce and age gates unchanged.
- Verify exact SHA256 of both stage-2 and stage-3 blobs before applying. No heuristic conflict resolution or silent drop of either source.
- Disposable GitHub Actions checkout performs a two-parent merge, applies only the two audited resolutions, validates JSON, source syntax, privacy, AG5+World focused suites and a broad software suite. Preserve raw failures and SHA before any push.
- If focused tests/compile/privacy fail, **do not push**. If they pass, create a merge commit and push ONLY to a **new** branch `codex/world-ag5-merged-review-20261027`, failing closed if that branch already exists; never force-push, merge to main, overwrite active owners or enable authority. Independently review candidate before any owner integration.
- Broad suite is diagnostic and may remain historically RED; do not relabel STEP2/B3/Body-JEPA or V13 completion. No native/Redmi proof, no model downloads/paid provisioning.

Exact next command on the candidate if it exists: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_console_shadow tests.test_world_probe_bounded_io tests.test_world_file_timing_receipts tests.test_handy_pflicht tests.test_handy_pflicht_resume tests.test_operator_config_atomic_run623 tests.test_language_operator_run620 tests.test_effort`.
