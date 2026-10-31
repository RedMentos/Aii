# Run38 verified original real-file result — 2026-10-31 UTC

Owner GPT-6 scheduled continuation. Review-only branch `assistant/v13-run38-world-jepa-fullslot-training-20261031-hourly11`, PR #1365, heavy source `717a32bb46c975cf8721ce2e8abb41e0cc87f159`, prereg first commit `cf56daa3fa2e7785ef0125fcd57975f25f25de0e`. Canon, original Run28, Run35 evaluator/collector and seeds unchanged.

**Original Linux real-file evidence CLOSED:** GitHub Actions `41151531032` terminal **SUCCESS** (this means experiment executed, **not** model utility success). Original artifact `13022683736` ZIP SHA256 `392d8c37452b56262806b1f2d13e67794c2d76a27ce229a0ea7d6f5cb8bfafa5`, CRC PASS, **82/82** original SHA256SUMS entries, **9/9** stage exits zero, 29/29 software tests, privacy CLEAN, source pins exact. Raw three-seed work/per-arm JSON preserved. Original ZIP privately backed up at `/V13-Checkpoints/2026-10-31/Run38-WorldJepa-FullSlot/Run38_REALFILE_ORIGINAL_41151531032_SHA_392d8c37.zip`; independently materialized and SHA256 readback identical. Original preflight artifact `13022673117` also privately preserved.

**Registered disjoint seed401–403, exact-row two-slot vs six-slot, 4000/150/300/3000:**

| Frozen metric | Original two-slot | All-six-slot |
| --- | ---: | ---: |
| Covered CF retrieval | 0.9164 | 0.8956 |
| No-action covered CF | 0.1873 | 0.1873 |
| Shuffled-action covered CF | 0.1932 | 0.1885 |
| Confidence/error pooled Spearman | -0.3534 | -0.3382 |
| Action attribution balanced | 0.9618 | 0.9561 |
| No-action attribution balanced | 0.9816 | 0.9721 |
| Action-minus-no-action balanced | -0.0198 | -0.0160 |
| Original W1–W5 | PASS | PASS |
| Original **W6** | **FAIL** | **FAIL** |
| W7a / W7b / W7c | PASS / FAIL / FAIL | PASS / FAIL / FAIL |

H1 preregistered mean balanced-gap improvement **+0.003733** (per seed +0.0212, 0.0000, -0.0100), **FAIL** versus required >=+0.02 mean. H2 covered CF >=0.80 each seed and original W2 controls fail: **PASS**. Six-slot covered retrieval falls by 0.0208, and action-specific attribution remains below no-action control. The new cohort happens to pass W4 for both arms; this **does not** retroactively change Run35 W4 FAIL or grant whole-system/World-JEPA authority.

**Independent recomputation:** Re-read original `work/{two_slot,six_slot}-{401,402,403}-RESULT.json` and per-seed `_conf_err`; independently recomputed original W1–W6 and pooled Spearman with original double-argsort ranks, matched the archived six gate booleans and summary to 4 decimals for both arms. Shared same-seed training/validation counts and attribution class counts match 3/3. No row-level causal equivalence is inferred beyond source-bound same-in-memory runner and matched counts.

**Interpretation:** six-slot training changes the action/noop example ratio from 1:1 to 1:5 for affected transitions, so this is not a pure capacity or matched-data-volume test. Original W6 demands +0.20 action-balanced improvement; no-action control remains ~0.97–0.98, making W6 mathematically impossible at these control levels even with perfect action accuracy. No threshold is relaxed. A separately preregistered Run39 action-balanced all-slot candidate (seeds501–503, no heavy overlap) tests this confound without changing any original negative result.

**Next command:** verify Run39 software CI and its original raw; only after no active native owner, run separately pinned Run39 real-file workflow for seeds501–503. Then verify original raw/failed attempts, update scoped BUILD_STATE and continue another Canon package. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, World-JEPA SHADOW, no Redmi/learned German transfer/JEF fusion/whole-system completion. Remaining platform budget UNKNOWN.
