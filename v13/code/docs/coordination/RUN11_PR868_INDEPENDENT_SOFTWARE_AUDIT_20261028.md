# Independent PR #868 exact-source software audit — 2026-10-28

Owner: GPT-6, review branch `assistant/v13-run11-jef-after-ag0-native-20261028-0805`, no source modifications. This is a **software-only** verification of the exact #868 workflow, not native/Redmi evidence.

- GitHub Actions run: 40647087335, exact tested source commit `ac24a0b0c75bbb132db0557bd81b9c263927e284`, conclusion SUCCESS. Branch PR #868 later doc-only head `5ff280db555658d912b36f2a3189ecdb4efcff1e`; do not confuse those commits.
- Original Actions artifact ID `12797519483`; downloaded ZIP size **8030 bytes**, SHA256 `3862bdeb52625d5fe44f269eed36fa65a33f600c900550a67c7bfe13842c9ddf`. ZIP CRC clean; all **16/16** internal SHA256SUMS independently recomputed and matched. Raw `HEAD.txt` equals exact tested source.
- Raw `BLOBS_RAW.log`: **13/13** expected Git blob hashes equal actual for World, C2 benchmark, C3 prompts, AG0 slots, test sources and frozen catalog. `BLOBS/INSTALL/FOCUSED/FULL/COMPILE/PRIVACY/DIFF` exits all **0**.
- Focused `unittest`: **46 PASS** in 1.556s. Full software suite: **2244 tests OK, 1 skipped** in 233.429s. `PRIVACY` exit0 and diff check exit0. The full raw log includes expected argparse rejection examples; final suite status is OK.
- Private Library backup: `/V13-Checkpoints/2026-10-28/Run11-JEF-AG0-Integrated/PR868_SOFTWARE_GREEN_40647087335_sha3862bdeb.zip`. Uploaded and re-materialized; SHA256 and binary `cmp` matched original **byte for byte**.
- New PR #869 pinned native workflow started independently at source `14e85071c95a8f66192cacbd86fd684f9e82b431`, run 40648145952. It has **not** completed at this audit. No native result is inferred from the software pass.

Original negative gates remain: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight=0, Age0 RECORD_ONLY, Redmi unmeasured, full V13 incomplete. No user/private data published. Next: inspect run 40648145952 stage exits, source hashes, model verification and JEF/STEP12/ask actual evidence, then checkpoint without rewriting failed rows. Platform budget UNKNOWN.
