# Run11 World multi-action recovery — original RED evidence (2026-10-28)

Prereg commit `3688f1eadc51aafd34cf378bdce35f093918cf7b`, red-test commit `86dbfcb15e9e9d8e73a725b7466f2b3ded53a384`, workflow/source run commit `189187c5c91cb849f4028340515aec68e7c06c97`. Source `world.py` remains parent blob `d9a5e9481acf8c644c956a26201a1eaeaa8baa7a`. No implementation change before this RED.

Actual GitHub Actions Linux software run [40644968809](https://github.com/RedMentos/Aii/actions/runs/40644968809) **RED as expected**: 13 focused tests, 3 failures (two same-event crash-recovery directions, one per-action observed count); 10 prior/single-action tests pass. FOCUSED exit1; FULL intentionally SKIPPED_RED; BLOBS/INSTALL/COMPILE/PRIVACY/DIFF exit0. This is a software Runtime/SQLite counterexample, not native inference or Redmi proof.

Raw ZIP artifact ID `12797261962`; SHA256 `f35395f8bdd2e21476cc22171e1fed04b8b00c8e62aa613c1d8bcd3f5c2deea9`, ZIP CRC pass, 16/16 internal SHA256SUMS pass. Private Library `/V13-Checkpoints/2026-10-28/Run11-World-MultiAction/WORLD_MULTIACTION_RED_40644968809_shaf35395f8.zip` uploaded and re-materialized byte-exact (cmp0, same SHA). Do not erase this failed attempt.

Source-level review also found historical unmerged PR #422 already has a more elaborate World receipt identity/recovery implementation on a **different review chain**. This package is a minimal current-branch regression repair only; full cross-chain reconciliation is separate and must preserve prior atomic outcome/Modulator semantics. No promotion of STEP2/B3/Body-JEPA/LP3/jepa_weight/Age, no production merge.
