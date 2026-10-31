# Run40 — independent audit of original Run39 native RED (2026-10-31 UTC)

Review-only child of Run39 PR #1366 at `d05ad63679efed8c6af24a6904c79a4920efa30c`. The registered Run39 three-arm Linux real-file workflow **completed with failure** at Actions `41152326121`, exact source `ad8e3d43995b970342757b720d2c66dbb5697aa1`. This is **not** a successful registered experiment and must not be reclassified as one.

Original artifact `13022689982`, **ZIP SHA256 `b329db427059274a34d51fd5c4d06e90173c9cae06c478a8648aec7249a8410a`**: CRC PASS, complete **84/84** inner manifest SHA256 checks, original `PINS/VENV/DEPS/TEST/COMPILE/PRIVACY/DIFF` stages zero; `REALFILE_EXIT=1` and `REPORT_CHECK_EXIT=1`. All **nine** per-seed result JSONs are present (three exact-row arms × seeds501–503), together with file-world source logs and failure traceback. Original `RESULT.json` is `RED`, `ValueError: RUN39_W7_SUPPORT`. Frozen Run35/38 W7 support requires **at least 15 examples in every class per seed**. Seed501 has **14 `world_only`** examples for all three arms; it is not legitimate to lower that threshold or discard seed501. The independent auditor refuses a PASS.

Independent **read-only**, stdlib-only Run40 auditor checks original outer SHA, ZIP CRC, full inner manifest, exact source and stage exits, cohort and negative gates, nine raw-to-aggregate row identities, class support, and recomputes W1–W6 from per-seed raw `_conf_err` and attribution values. Original two-slot W1–W6 booleans match. Rank ties use a deterministic stdlib tie-break; Spearman magnitudes can differ slightly from original NumPy `argsort` ties, but **no gate is near a threshold crossing**.

| Arm | W1 | W2 | W3 | W4 | W5 | W6 | W7 support |
|---|---|---|---|---|---|---|---|
| Two-slot | PASS | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** |
| Unweighted six-slot | PASS | PASS | PASS | PASS | PASS | **FAIL** | **FAIL** |
| Action-balanced six-slot | PASS | PASS | PASS | **FAIL** | PASS | **FAIL** | **FAIL** |

**Descriptive only, not a registered H1/H3 verdict:** balanced minus unweighted six-slot action-attribution gap is `−0.004300` (per-seed `+0.0034/−0.0032/−0.0131`), below H1's `+0.05`; four-class macro gain difference `+0.000383` (per-seed `−0.0057/−0.004875/+0.011725`), below H3's `+0.03`. The candidate therefore provides **no evidence of the hypothesized improvement**. The original `RED` status and support failure remain binding. A fresh disjoint preregistered cohort would be needed for any confirmatory result; do not reuse these seeds as new evidence.

Local independent original-ZIP audit: `python scripts/run40_audit_run39_red.py --zip <original>` verified; **7/7** original/tamper tests pass (outer hash, inner manifest, stage tamper, gate tamper, W7 support, W1–W6). CI workflow downloads the **original** artifact by ID, checks the pinned SHA and runs the same tests without native refit. This is Linux raw-analysis evidence, **not** Redmi, live JEF, production World-JEPA, Body-JEPA or whole-system utility.

Original native ZIP privately saved and independently materialized byte-identical at `/V13-Checkpoints/2026-10-31/Run39-WorldJepa-ActionBalanced/Run39_NATIVE_RED_ORIGINAL_41152326121_SHA_b329db42.zip`. Preserve prior failed and green Run39 software ZIPs; do not overwrite frozen code or original negative gates. Age0 `RECORD_ONLY`; STEP2 `UTILITY_FAIL`; B3 `NO_PROMOTION`; Body-JEPA `UNAVAILABLE`; `jepa_weight=0`; World-JEPA `SHADOW`; no Redmi/learned German transfer/live JEF or whole-system completion.

**Next independent Canon work:** prioritize unblocked end-to-end C2/C3/Body/Context integration or measured JEF routing rather than tuning this World-JEPA cohort. No production merge/auto-merge. Remote branch/CI and private original byte backup are the durable handoff; runner source/model/seed pins remain unchanged.
