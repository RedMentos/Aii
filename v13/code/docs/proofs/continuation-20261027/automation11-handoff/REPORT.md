# V13 2026-10-27 independent continuation — durable review handoff

**Integration chain:** `main` is older than the active review chain. Current source ancestry: PR #713 `c13aee9b1ab29bb197b9a8c4a42bb664e1a353fc` → PR #714 `2b3a4b934fa0283aa9a24fd25879b7bea6504588` → PR #715 `73f8d4446cca234628fced82f2fe1ab8d9de5a7a` → PR #716 `e38d72a316b4aab57ff629cfe13300b4298cea25` → PR #717 `a718ee365eccd968930deccdfce740d71e3ac709`. All are **review-only draft PRs**, not production-integrated.

## Four verified independent software packages

1. PR #714: batch attempt prefix validated against real native child regex (max 17 prefix chars, no periods). RED Actions `40508297873` 3/29 expected failures → GREEN `40508433741` **29/29 PASS**. Original raw ZIP SHA256 RED `90bbae84cbcfda45dd43ac61ad03a5420f0f1980204cbaf24d3adfc4040a2c32`, GREEN `33e4b33d473b50757c11d64e67b8e981fb5fcf265d3ced0e15b054fdb1510cee`.
2. PR #715: fsync original raw subprocess log before completed/failed checkpoint. Strict FD-path RED Actions `40509034227` 2/31 expected failures → GREEN `40508999107` **31/31 PASS**. Original ZIP SHA256 RED `92918ca02130c5d56334abcd4b8b29f435ccf961fc10ef29f85264fbadb52304`, GREEN `1765cebe19200a06b03f78f59a901058e755cb92b9c4a09087548aee3da818a5`. Initial inode-based false-positive test was rejected and replaced.
3. PR #716: real full-master preflight adapter binds `PIN_PATH` and rejects wrong `MASTER_SHA`. RED Actions `40509315923` 1 expected ERROR + 1 expected FAIL /33 → GREEN `40509359008` **33/33 PASS**. ZIP SHA256 RED `ca4357c9806cead5b98e0aacadc3502edba03928822aa165e67e0191fe21a3b4`, GREEN `9eaa72753557265464931d6e175c2d4a9ca92c936b738cae4791c6574e6fe247`.
4. PR #717: native ATTEMPT/SCORE/prediction sidecar hashes required for completion and resume. RED Actions `40509777121` 3/35 expected failures → GREEN `40509825442` **35/35 PASS**. ZIP SHA256 RED `0b6020bfba89e79bfd5ec0d183b7353b26a203248049668dcaa192165178354d`, GREEN `ca06c87a021fb73295f7a912c7e4e9118ca60b930fd84c6bf5b49222db0ebcb5`.

All original ZIPs CRC/SHA256/HEAD/exit checked and privately saved in ChatGPT Library `/V13-Checkpoints/2026-10-27/BP2b-{Prefix-Contract,Log-Durability,Master-Call,Sidecar-Restart}/`; all four RED/GREEN pairs were re-materialized byte-identical. Full details in the four sibling `REPORT.md` files. No raw weights or private data committed to GitHub.

## Current owners and gates

- Separate genuine Linux-native seed41 legacy attempt Actions `40506115941`, SHA `7243d71f51ff53587b5062953a7d79f786648e87`, was **IN PROGRESS** at this checkpoint. Earlier `40505978531` failed at environment import; original failure preserved. Do **not** start a competing heavy model job until owner and its evidence close.
- Full software regression suite on this branch: workflow `.github/workflows/bp2b-fullsuite-review.yml`, Actions `40510172446` initially **IN PROGRESS**; result must be checked before a pass claim.
- No new native BP2b utility proof from these four packages. STEP2 UTILITY_FAIL, B3 L1 FAIL, BJ1_NO_SIGNAL/Body-JEPA utility unproven, `jepa_weight=0`, Age authority 0, Q4/Redmi unmeasured, canonical architecture and full user scope incomplete. No gate promoted.
- Full SSOT remains `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`; no organ or requirement removed. Other concurrent Claude/Codex branches remain owned separately.

**Next commands:** `cd v13/code && PYTHONPATH=. python -m unittest -v tests.test_bp2b_native_batch tests.test_bp2b_native_runner tests.test_bp2b_transfer_score`; inspect Actions `40510172446` original raw ZIP for full suite; inspect Actions `40506115941` and preserve original native raw evidence. After heavy owner clears, review whether actual training, adapter export, heldout and retention ran; do not infer learning from software-only tests. Then continue the next canonical package, including remaining Context OS/JEF/C3/B1/B2/JEPA/Callosum/Dream/Sleep and Redmi gates.
