# Independent PR #654 review: bounded World-JEPA SHADOW local reads — 2026-10-27

Base PR #654 head `d466aa121810041ad5bcee3034eee17f1d676cf4`, review-only child `codex/review-world-probe-bounded-io-20261027`; not main. Canon and newer user decisions unchanged.

## Confirmed defect / change
The explicit `:world shadow` console bridge checks hard READ_LOCAL/notaus/announce prohibitions before file access, but its shared `_json_file` loader and `SlotWorldJEPA.load` checkpoint loader used `Path.read_bytes()` before checking their existing maximum sizes. A huge caller-controlled file therefore allocated its entire content on the 6 GB-class Redmi before being rejected. Both paths now open files and read at most `max_bytes+1` (JSON 2 MiB / provenance 8 KiB; checkpoint 32 MiB). The existing exact SHA256, provenance, archive checks, schema, inference, and authority remain unchanged. This is a bounded resource integrity fix, not World-JEPA utility.

## Preregistered raw RED / intermediate / GREEN
Prereg commit `5d087dcebf9ec761a3dd07d7157c9df51e76665e`; test commit `0cb4aa7927d11b33bca8e71ded33eedc246f1c0e`; CI commit `a88958b34c2df28510e028e75ab061586b96b9fe`, before any source fix.
- RED Actions https://github.com/RedMentos/Aii/actions/runs/40450200045, HEAD `a88958b34c2df28510e028e75ab061586b96b9fe`: **22 tests, 3 FAIL** (oversized JSON, provenance, checkpoint); compile 0, privacy CLEAN. Original artifact 12709891792 SHA256 `025964f5c614c8714a3f5f4103596142681cba0275a4de86703cbd653e256562`.
- Intermediate Actions https://github.com/RedMentos/Aii/actions/runs/40450254464, HEAD `419bbc895373faaa51ae6836655eba334c94000f`: **22 tests, 1 FAIL** (checkpoint loader still unbounded); compile 0, privacy CLEAN. Original artifact 12710440706 SHA256 `a4c1102f4a6d0ee364909f1dc8b755473c06709771f3b926c514d7a18833bd4c`.
- GREEN Actions https://github.com/RedMentos/Aii/actions/runs/40450270947, HEAD `c568201bce21ab32f624e8322826058c92358928`: **22/22 PASS**, compile 0, privacy CLEAN. Original artifact 12710605429 SHA256 `4ed585f4498ef6f07760c1a0b9888be762a5290c0454651d095e78758cccd020`.

All three original ZIPs checked for CRC, HEAD, exit files and SHA256; private Library backups at `/V13-Checkpoints/2026-10-27/World-Probe-Bounded-IO/` uploaded and byte-verified by rematerialization. No rejected anyone-writable Drive location used.

Exact GREEN source SHA256:
- `v13/code/v13/world_jepa_shadow_probe.py`: `f5ba6916fc7a0beb7ad35abaf10d45077579e14000ecf2c0e7f6770e946722e9`
- `v13/code/v13/world_jepa_slots.py`: `5325089689641bdd27817ccc7f78dfadf98c42225dd22397e6238b255a14602e`
- `v13/code/tests/test_world_probe_bounded_io.py`: `bc51455f182f2af4bc413df5ffd99a79a5970f0c1baea85b485af23de4b7a8fc`

## Claim limits / next work
Software/synthetic Linux CI only. No Redmi measurement, no new native LLM run, no registered Z12c rerun, no proof of World-JEPA causal/semantic utility. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age/approval unchanged; `canonical_architecture_complete=false` and `user_full_scope_complete=false`. Main and active owners untouched.

Owner: independent reviewer / next implementer. Next substantive package: verify whether preserved World-JEPA Linux file-world row overlap labels are independently recomputable from the raw world log; if not, add source-bound timing sidecar with prospective RED/GREEN without changing historical cohort hashes. Also pursue full-budget fresh-seed v2 utility evidence separately. No automatic live observer until action/slot mapping is validated.

Exact command with isolated NumPy 2.3.5 and prompt-toolkit 3.0.52:
```sh
cd v13/code
PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_probe_bounded_io tests.test_world_console_shadow tests.test_world_jepa_shadow_probe tests.test_world_jepa_slots_checkpoint
```
