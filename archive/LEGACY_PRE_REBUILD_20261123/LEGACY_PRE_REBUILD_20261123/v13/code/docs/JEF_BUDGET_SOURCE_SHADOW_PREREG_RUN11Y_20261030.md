# Run11Y prereg — JEF source-bound budget arithmetic SHADOW candidate (2026-10-30)

**Problem:** Run11V native C2 genuinely selected 4/4 routes, yet the F auto arm gave **0/8** correct remainders; B2-only gave 6/8 on the same four-source native pilot. Do not tune/reuse frozen seed181 or seed163. This new package implements a bounded **non-generative source-bound arithmetic candidate** for JEF/Context OS, without giving it authority over C3/Body outputs. It is not a STEP2, learning or native utility claim.

**Parent:** Run11X PR #1254 HEAD `adb828fe3a1a0a5f6f7fce284bcb5f4bbab4af4f`. Original Run11V native ZIP SHA256 `9d34fe9b81ad9c5560ba44c4db3851c0be9129a012cdfdf6b47717346972885f`, privately byte-exact. Original scorer/runner/model/Canon untouched.

## Frozen design and tests before implementation

New seed **197**; eight previously unused synthetic projects with the exact tuple keys `project,budget,a,a_cost,a_days,b,b_cost,b_days`:

1. Maple197: 512; Larch 179 / 8d, Opal 284 / 3d → **333, 228, Opal**.
2. Dawn197: 333; Moss 162 / 2d, Flint 298 / 7d → **171, 35, Moss**.
3. Vale197: 618; Amber 459 / 4d, Juniper 523 / 6d → **159, 95, Amber**.
4. Pine197: 271; Birch 112 / 9d, Coral 205 / 1d → **159, 66, Coral**.
5. Drift197: 807; Quartz 633 / 6d, Willow 491 / 5d → **174, 316, Willow**.
6. Echo197: 426; Frost 324 / 3d, Cedar 218 / 8d → **102, 208, Frost**.
7. Glade197: 742; River 287 / 7d, Stone 689 / 2d → **455, 53, Stone**.
8. Hearth197: 365; Slate 249 / 1d, Fern 153 / 4d → **116, 212, Slate**.

Canonical `json.dumps(FIXTURES,sort_keys=True,separators=(',',':'))` SHA256: **`c900b1f498669f2b7192e1ea95cfe181270e25694d1f16374aac88b741642a0e`**. Two source grammar variants, evenly alternated: (1) Run11V-style complete English local-device spending question, (2) `Project P has a local budget of N EUR. Option A costs X EUR and takes D days; option B costs Y EUR and takes E days. Report both remaining budgets and the faster option.` Same information, different order/punctuation.

**Expected positive:** 8/8 exact computed structured outputs, real Store SOURCE_REF full-span integrity, no model calls, restart byte-equivalent, no source writes from readout. **Negative:** extra trailing instructions/injection, duplicate option labels, second project, malformed amount, grouped decimal, missing day, non-positive or over-budget costs, tie without specified policy, partial SourceRef, wrong SHA, revoked Store source, tampered blob, source substitution; all must abstain with no proposed numbers. Source hash/provenance preserved in output, no model-derived authority.

Implementation boundaries: new `v13/code/v13/agi/budget_en_source_shadow.py`, new tests `v13/code/tests/test_budget_en_source_shadow_run11y.py`, new focused CI workflow, scoped evidence and BUILD_STATE only. No edits to runtime, frozen Run11V files, Canon, model registry, seeds, original scores or safety gates. SourceRef validity proves bytes, **not** human approval; candidate `SHADOW_NO_AUTHORITY`, `authority=0`, `native_calls=0`, `weight_updates=false`. Future integration requires separately registered utility and authorization gates.

**Acceptance:** exact new cohort and adversarial tests PASS in CI, privacy CLEAN, negative gates unchanged; evidence artifact closed with SHA and private backup. Software success is not a native or Redmi result. Stop/freeze this cohort if it fails and preserve RED before fixing only new source/test.

**Next command:** implement pure read-only parser and Store-verified proposal; run focused tests, independent review and software CI. After a verified checkpoint continue another substantive canonical package.