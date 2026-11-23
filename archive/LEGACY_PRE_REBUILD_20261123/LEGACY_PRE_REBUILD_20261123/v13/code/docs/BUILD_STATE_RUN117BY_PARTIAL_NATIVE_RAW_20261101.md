# Run117BY — future-only partial native C3 failure receipt preservation

Date: 2026-11-01 UTC. Review-only child of Run117BW PR #1553, exact base `06be668f1345135382a511ae575412cbe8806fa3`. Source owner: Run117BY branch only; no changes to the preregistered seed1103 fixture, model/runner pins, original Run117BW native workflow or original raw. This patch **must not** be used to reinterpret the original completed seed1103 native experiment.

## Concrete defect and repair

The earlier `scripts/run117bu_disjoint_budget_native.py` only appended an arm after its generator returned, and joined all tokens in one expression. If native generation raised mid-stream, the arm and its partial raw output disappeared from the per-row report, even though a native attempt had occurred. Future-only repair: register the arm before execution; append native chunks incrementally; capture last native metrics and unload in `finally`; preserve partial output, release history, exact error type and a non-promoting `STRUCTURAL_RED` arm when interrupted. No new model authority, no change to scoring thresholds, order, fixture, prompt or success-path semantics.

New regression `tests/test_run117by_partial_native_receipts.py`: real Store + synthetic runner injected (1) RAW_SOURCE-first midstream exception, and (2) TYPED_JEF callback failure followed by RAW_SOURCE. Both retain failed-arm receipts, do not promote, and close Store. These are software stubs, **not native inference**.

## Closed verification

- CI workflow: `.github/workflows/v13-run117by-partial-native-raw-preflight.yml` (software only).
- Terminal Actions: [41254792295](https://github.com/RedMentos/Aii/actions/runs/41254792295), SUCCESS at source `62d29b5e63186f1e0352b7774d4af357e14cae09`.
- Original artifact `13062563391`, 4,063 bytes, SHA256 `3f67e64848cbb71b2893221699bfddb9c3f1f3b0a8e307067a5bbd88c203ba1c`. Independently downloaded: ZIP CRC PASS, **16/16** manifest hashes with exact coverage, **7/7** stage exits zero, **23/23** software tests PASS, py_compile PASS, privacy scan CLEAN, git diff --check PASS.
- Source Git blob `790fd0351dbe47398b760ef582531a1d0d49eabd`, new test blob `aa2bbb40aeb06177fbe7e3ea3729aa4ff26f38ac`, Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged.
- Private Library backup: `/V13-Checkpoints/2026-11-01/Run117BY-Partial-Native-Receipts/RAW_41254792295_sha3F67E648.zip`; re-materialized and compared byte-identical to original downloaded ZIP.

## Gates, owner, next command

Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`, no Redmi measurement, no native JEF/B1/B2/C2 or learned utility, no output/tool/learning authority, no whole-system completion. This patch only repairs **future failure evidence preservation**; Run117BW native result is unchanged. Review owner: independent reviewer on this isolated branch; no production merge implied.

Exact next command for a software-only reviewer, after checkout of this branch and pinned Python dependencies: `cd v13/code && python -m unittest -v tests.test_run117by_partial_native_receipts tests.test_run117bu_disjoint_budget_native tests.test_run117bo_jef_c3_budget_formatter_shadow`. Check `git diff 06be668f1345135382a511ae575412cbe8806fa3..HEAD`, privacy scan and no promotion. A future native error-path run requires **new** registration, owner clearance and preserved failed raw; do not rerun seed1103 as a fresh cohort. Remaining platform execution budget UNKNOWN.
