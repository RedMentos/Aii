# Run36 — original Linux-native C3 Velaris five-arm result and handoff (2026-10-28)

**Scope / owner:** Review-only PR #945, branch `assistant/v13-run36-c3-only-native-velaris-20261028`, source-only parent Run35 #944 at `1f2039f3fa7b62ed6c9e3699672af91dfe532144`. Native Actions `40734479879` ran at exact immutable source commit `436414f4c7c8dcebf5afc4bffdce57c8bb787284`. This is one Linux-native C3-only conditional input pilot, not B1/B2 inference, phone proof, STEP2 promotion or complete V13.

## Verified native execution

- Pinned source blobs for Run34, Run33, ModelManager, bootstrap, runner, scorer, catalog, consumer and Run15 all matched (9/9). Pinned C3 LiquidAI/LFM2.5-350M-GGUF revision `657e078c94084481950a2d555a941481f715536b`, GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; llama.cpp b10964 x86_64 archive SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, installed binary SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Only pinned C3 and Needle support were installed; no B1/B2 model download/inference. Runner override `V13_LLAMA_SERVER` was unset.
- Five source-exact, preregistered Velaris EN SPLIT arms, seed `20261121`, each produced a nonempty native `FINAL` answer with model identity and reaped process. `model_unchanged`, `runner_unchanged`, `source_unchanged` all true. Oracle was absent from native prompts. Receipt status `PASS_SCOPED_C3_ONLY_NATIVE_NO_STEP2_GATE`, **structural only**.
- Original Actions ZIP artifact `12835973234` SHA256 `e6b9f6454a451c1001ea45072bc4e738c455abbd2cfdbe8a6af0c0ab52328cbd`, CRC PASS, **22/22 inner SHA256 PASS**, nine proof-stage exit files all zero, 16 focused tests PASS, privacy CLEAN. Independent raw row SHA256, raw answer SHA256, arm/fixture/seed, oracle-free input and native status checks **5/5 PASS**.
- Raw report SHA256 `655b7da0917ec7fcb2eb8eec82d11980e11e865062cbeb8c5a2474ded7d79288`. Original ZIP privately persisted at `/V13-Checkpoints/2026-10-28/Run36-C3-Velaris-Linux-Native/RUN36_NATIVE_GREEN_40734479879_shaE6B9F645.zip` and independently re-materialized **byte-identical**. No private user data published; source is synthetic fixture.

## Actual utility, not just structural PASS

| Arm | Utility | Exact answer | Key error |
| --- | ---: | --- | --- |
| CURRENT_ONLY | 0.166667 | no | action + most fields |
| B1_ONLY | 0.750000 | no | action + both remaining |
| B1_B2_MISSING | 0.666667 | no | project string + action + both remaining |
| B1_B2_EXACT | 0.750000 | no | action + both remaining |
| B1_B2_DISTRACTOR | 0.666667 | no | project string + action + both remaining |

**Crucial negative result:** `B1_B2_EXACT` and `B1_ONLY` have **byte-identical raw answers** (SHA256 `653c47481d904a7a8ce2d9627ae39ec9028c78591223b46e536ce93cf011672b`), despite extra exact B2 rule text. `B1_B2_MISSING` and `B1_B2_DISTRACTOR` are likewise byte-identical (SHA256 `54fccad3d9d9f22c9ff808391680a5f43d83c7fd19e2fa53546391a497027dfb`). The observed +0.083333 exact-minus-missing utility is **only the project field** (`Velaris` versus `Project Velaris`), **not** an action/rule inference gain. All five arms choose `action=NONE`, whereas the registered oracle requires a different action. Both `remaining` fields are null in the B1-bearing arms. There is no evidence of C3 benefiting from B2 rules on this fixture. This one case cannot support population causal or utility claims.

## Next authorized work

Do **not** alter this original frozen five-arm evidence. Preregister a separate controlled, disjoint C3 instruction/decision extraction intervention (or balanced 6-fixture x 3-seed cohort from Run33) with action/remaining field metrics as primary outcomes and explicit no-B2/B2-exact/B2-distractor controls; keep B2 quote generation separately unproven. Use a new review branch and exclusive native owner; capture failed attempts and original raw, model/source/seed pins, privacy and byte-identical private backup. In parallel continue other Canon organs, especially JEF/C2, Context OS, B1/B2 JEPA, Callosum and Dream/Sleep. Do not claim STEP2 utility, B3, Body-JEPA, jepa_weight or Redmi proof from this one native pilot.

**Negative gates unchanged:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; V13 incomplete. Remaining platform budget UNKNOWN.
