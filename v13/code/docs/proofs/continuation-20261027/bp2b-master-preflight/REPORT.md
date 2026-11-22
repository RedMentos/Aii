# BP2b FP32 metadata and preflight checkpoint · 2026-10-27

Owner: automation11 BP2b master metadata/preflight, review PR #708, parent PR #707 exact `96973e070d91f5dfb456e0ae8166dfedc4ad6f15`. Preregs `c1cad971af9013a9b0cecfcb3c2add0b2cbbe945` and `960b8bf740cd3182b1557449a9ab13a86b04aa3f` before their respective packages.

**Pinned public provenance:** LiquidAI/LFM2.5-1.2B-Instruct, exact revision `8c1348a4aac046a3a5d7698e7fcaaa8a3b7d9cdf`, LFM Open License 1.0. Official FP32 master SHA256 `1ba63d9adb03ae43581db0e136e4416febe0441aff7296397bd455fb6017f73a` matches earlier BP2a master report; **not locally downloaded or verified**. Seven metadata files fetched from exact revision and individually rehashed from original artifact. Locked source `v13/code/specs/bp2b_master_metadata.json` Git blob `e7e8c6f58252f7e7d5919034d2b156a58556e462`.

File | Bytes | SHA256
--- | ---: | ---
config.json | 1224 | `15d6157fb6df3f8272e2fe90e18f57727ccf02a125c94469198b0f3281510185`
generation_config.json | 132 | `5ffd97da1dec4308543894569662d96e923ed01f7a9d8c7ff5aea7f800738cbd`
tokenizer.json | 4733389 | `df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd`
tokenizer_config.json | 92225 | `2a52ec012d3df831ba434b081bef3726a6ee22501f062ad8353c557a0cfa0d01`
special_tokens_map.json | 434 | `742aefe2b7dec496e8caffdba03a75d0c1a9925d53bd3f3e0d388c96b591b6f4`
chat_template.jinja | 1783 | `f05bf4b967dc993bdc7a2fe6e43759ee218eb0eb340d68b063e1c4f8ad148176`
LICENSE | 10596 | `5188f2b355da20647257a3156db5834c794e5fb5e6d8dc4d4cdbb3180e75b85b`

**Closed raw evidence:**
- HF metadata Actions `40502634640`, exact `aeea42a2a6caccd56ddd6522dc0e8b70fad8857e`, seven files downloaded, sha256sum 7/7 match, COLLECT_EXIT=0, PRIVACY_EXIT=0, ZIP SHA256 `b735e8c7718b97a275aec1eb44a74b23c9d71d5edffea65edd7fce2ec0116820`, CRC PASS. Private backup `/V13-Checkpoints/2026-10-27/BP2b-HF-Metadata/` re-materialized byte-exact.
- Local verifier Actions `40502964352`, exact `c8256029d2341ae140475bc2b465e4987682377d`, 7/7 synthetic tests PASS, compile0, privacy CLEAN, ZIP SHA256 `06e8aa25e096c8a89e8b059975bc103e9ad5f793b5f8dd2469159b9a757d323e`, CRC PASS. Private backup `/V13-Checkpoints/2026-10-27/BP2b-Master-Preflight/` re-materialized byte-exact. Script Git blob `6823adc0d5ba367efde009343b241562ebf4b085`.

**What remains:** The verifier supports metadata-only vs streamed full FP32 weight hash, but no full-weight verification, model execution, BP2b native 4-arm comparison, Q4 adapter/Redmi measurements or production integration occurred. Next: implement source-bound per-arm native runner, pin actual master+tokenizer and heavy owner, serialize experiments, preserve failures, then independent review.

Exact next command: `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_master_preflight`; full local preflight once master exists: `PYTHONPATH=v13/code python v13/code/scripts/bp2b_master_preflight.py --master-dir /path/to/pinned/master --out /path/to/receipt.json`.

Negative gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1_NO_SIGNAL, jepa_weight=0, Redmi unmeasured, whole V13 incomplete.
