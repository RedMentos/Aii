# Run365 GREEN — exact-head source/SQLite closure

## Verified implementation
- Parent `assistant/run364-plain-ui-cursor-20261025` @ `4616bb0618b7ff64969df6f1af369da723f5da3e`, review PR #360 (stacked, **not merged to main**).
- Production `v13/code/v13/organ.py` now checks the role against the existing `models.ROLES | models.OPTIONAL_ROLES`, refuses unsafe organ-root/role symlinks and paths, requires generated `organ_<32 lowercase hex>` IDs, and binds manifest ID/role to its actual directory. No model/age/approval/learning changes.
- Source commit `e5c0ced78487563fd343f50ac72267bec1af684b`, additional independent ID-swap and role-symlink tests commit `5bcae3b9ca2acbc85f78d40d0a55486bd40cc34f`.
- SHA256 source `v13/code/v13/organ.py`: `908ec645748b1870e54067b3bf5da8285ed163085173e7083e237c6848e86ddc`; new test: `38ba1d009df28783b76bb85bb81f4a0f51000502001458f3c20857823156bb24`.

## Actual evidence
- Original RED exact head `b3dc77da2a3d87de7d20d2ddaf19e0f7c0ce6a41`, Actions `40231388826`: 13 tests, 4 expected assertion failures, 9 inherited organ tests passed, privacy CLEAN. Raw artifact `12613721197` SHA256 `b090f3a75a81dd5bdf6f95088740ec0e47fe4d48be645f5c7d3893bcbf442bd4`, CRC and 4/4 raw-member SHA manifest PASS. Independently downloaded and stored in private Library `/V13/checkpoints/2026-10-25/V13_Run365_OrganPath_RED_raw_shab090f3a7.zip`; re-materialized bytes matched.
- Initial GREEN `e5c0ced...`, Actions `40231498419`: 13/13 PASS, privacy CLEAN, raw artifact `12613336145` SHA256 `9dc400cdc25990203355ecae3470e476ca98fc74b710c888fc334f7e4133f800`, CRC and 4/4 manifest PASS; private Library copy verified.
- Final GREEN exact head `5bcae3b9ca2acbc85f78d40d0a55486bd40cc34f`, Actions `40231660532`, job `121284495084`: **15/15 PASS in 0.916 s** (six new path/identity negatives + nine inherited), compileall PASS, privacy CLEAN. Independent focused source-bound workflow `40231660542` completed **SUCCESS** at the same exact source/test head; its scope is not a full V13 acceptance suite.
- Final raw artifact `12613721657` SHA256 `73206668c8b6d49b837a6fcec67c38d26fa90df018fabef859720b70c56ae7cd`, CRC and 4/4 internal SHA manifest PASS. Private Library `/V13/checkpoints/2026-10-25/V13_Run365_OrganPath_GREEN_FINAL_raw_sha73206668.zip`, re-materialized and byte-compared equal to downloaded raw ZIP.

## Negative gates and handoff
- Evidence = GitHub-hosted Python/SQLite tests only; **not** Linux-native model quality, Redmi, B3 L1, STEP2 EXIT, Body-JEPA, `jepa_weight`, Age promotion, complete V13 or a general security proof.
- `canonical_architecture_complete=false`, `user_full_scope_complete=false`.
- Remaining organ concern (not part of this package): bridge files are copied after the generation commit, so an interrupted bridge restore may leave a mixed state; needs a separately registered recoverable protocol rather than an untested atomicity claim.
- Next independent functional package: bound nonfinite AG12 solver confidence before weighted coalition/learning telemetry, with RED-first tests and original `test_agi_solver` regression. Avoid altering any frozen native cohort or user approvals.
