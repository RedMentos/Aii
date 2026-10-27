# Current-chain full software suite: optional native path portability — prereg 2026-10-27

Base diagnostic commit `27ada5026bb16f3d11c0b3c7689917029594d408` (world review chain PR #656; not AG5/Claude integration or main). Exact Linux Actions `40451020251`: `python -m unittest discover -s tests -p test_*.py -v` executed **1820 tests, 1 ERROR, 15 skipped**, compile 0, privacy CLEAN; original ZIP SHA256 `0b52dc79f13f3b2ddee125cf2ce69dafa3a37bd4eaef31eda902d109ebac4522` privately backed up and verified.

The single error is **test-only**: `tests/test_toolforecast.py::CheckpointTests.test_competence_check_scores_states_not_calls` probes `Path('/root/native/restore/round8-note-tool-raw').exists()` and raises `PermissionError` on the non-root Actions runner. The native path is optional; this is not a production regression, not a failed model or a missing fixture to fabricate.

## Acceptance before source
- Allow optional native restore root from explicit `V13_NATIVE_RESTORE_ROOT`, default historical path unchanged.
- When the optional native directory is missing/inaccessible, skip ONLY that extra native plan cross-check, retaining all mandatory synthetic competence assertions. Catch OSError only around the optional existence probe; do not hide `cc.plan` errors when the path is accessible.
- Tests prove PermissionError is skipped and an accessible explicitly supplied root actually calls `cc.plan`. First commit RED tests before helper source, then focused GREEN and a new full software suite (same pinned environment) with original raw ZIP/source hashes/compile/privacy. No model download/native run, no acceptance gate promotion, no AG5/Claude branch merge.
