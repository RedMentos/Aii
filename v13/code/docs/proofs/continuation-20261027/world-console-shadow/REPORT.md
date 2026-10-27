# V13 explicit `:world shadow` console bridge — verified 2026-10-27

Review-only child of PR #653 exact `3d39a7e0663ffbf72b804e5926822f2c9ab2ec7f`, not main. Adds a narrow explicit **OPERATOR_TTY-only** subcommand:
```
:world shadow <checkpoint.npz> <sha256> <provenance.json> <observation.json>
```
It reuses the calibrated v2, digest/provenance-bound read-only World-JEPA probe and returns its JSON result with `SHADOW_ONLY`, `authority=0`, `action_executed=false`, `learning_performed=false`, and `after_verified=false` for caller-supplied after-state. No output file, model update, automatic action, fact write, Age change, tool proposal or download. Existing `:world` world-state report is unchanged. Unknown/partial subcommands fail rather than silently being ignored.

## Fixed-rule safety
Independent review after the initial GREEN found a genuine policy gap: the new local file read was outside the transaction tool registry and could otherwise bypass `:notaus`, fixed `:verbot` (READ_LOCAL, all, or named `world_shadow_probe`) or `:verbot ansage an`. The final source checks existing model-independent `prohibitions.blocked(store,'world_shadow_probe','READ_LOCAL',True)` and `announce_all(store)` **before reading any file**; all blocks and unreadable prohibition state fail closed. The console does not silently create an approval route. The existing non-TTY origin gate remains binding. `:stillstand` explicitly allows user-typed operator commands but notaus/forbidden local reads are still enforced.

## Prospective RED/GREEN
Prereg `d474ae4a00420971565030134d5a27ec7cb1646c`; RED tests `45480066bbfcef3ce6fdd5fdcfaa344d6a46814c`, workflow `9154520e5326b9e98ed167b3c4cd47880001bcd5` before source.
- RED Actions [40449343966](https://github.com/RedMentos/Aii/actions/runs/40449343966): **39 tests, 4 FAIL** (no console bridge/unknown args/help); compile 0, privacy CLEAN. Original ZIP artifact `12709785830`, SHA256 `7d6aa273495ae23efe45a5debbccfbcfa77325d67241d9458d100db63f6d7ebe`.
- Initial GREEN Actions [40449369769](https://github.com/RedMentos/Aii/actions/runs/40449369769) at source `fb1d2de37641a555f5c08dffb94cfaa5600efaaa`: **39/39 PASS**, compile 0, privacy CLEAN. Original ZIP artifact `12710010617`, SHA256 `3c7af679bfccc0a1392e31d7e6e8b687644eec24ef5f1393d81fffbc950bacdf`. This success predates the hard-rule review and is not retroactively treated as satisfying it.
- Prospective safety amendment `0d221a5015b1a036c73ad78257a92d7f8c7416a5`; RED tests `bd072bbfb1ead2a1eeb9f663654bc85a33f02b1e`. RED Actions [40449506387](https://github.com/RedMentos/Aii/actions/runs/40449506387): **40 tests, 6 FAIL**, proving file JSON loader was reached under notaus/READ_LOCAL/all/named/announce/invalid-table blocks; compile 0, privacy CLEAN. Original ZIP artifact `12710215425`, SHA256 `16a3072259f38def19ecdf35140b45b918f8ff3d5e475c38691b8178483f6aa9`.
- Safety fix `3eb0297155b31f78d69f557e204970b29f398a34`. Final GREEN Actions [40449532588](https://github.com/RedMentos/Aii/actions/runs/40449532588): **40/40 PASS**, compile 0, privacy CLEAN. Original ZIP artifact `12709523659`, SHA256 `5efbea879c6c59edac245a72729573dc72d69cce4c308a65da514395c964d5e8`.

All four original ZIPs checked for SHA256/CRC/HEAD/exit and privately uploaded to `/V13-Checkpoints/2026-10-27/Automation11-World-Console/`, then re-materialized and byte-verified. Rejected anyone-writable Drive not used.

## Limits and next owner
This is **software/synthetic Linux operator evidence** using a real small NumPy checkpoint, not a native Body/Redmi run, not automatic Context OS observer, not proof of semantic/causal utility. The original registered Z12c PASS (201/202/203) remains historical; the new tiny seed211 smoke FAIL remains separately preserved. No changes to JEF/C2/C3/B1/B2/Callosum/Sleep/Dream, age/approval, STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0` or V13 incomplete. Full suite historically RED.

Owner: independent next reviewer. Next: inspect the ongoing fresh-seed full-budget Z12c v2 replication (214/215/216), preserve all results, then investigate a **source-bound automatic SHADOW event observer** only with a validated runtime feature/action mapping and explicit operator opt-in; do not infer file-slot semantics for unrelated runtime actions.

Exact focused command (isolated NumPy 2.3.5 and prompt-toolkit 3.0.52):
```sh
cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_console_shadow tests.test_world_jepa_shadow_probe tests.test_world_jepa_shadow_lifecycle tests.test_z12c_control_calibration tests.test_world_jepa_slots_calibration_guard tests.test_world_jepa_slots_checkpoint tests.test_world_state
```
