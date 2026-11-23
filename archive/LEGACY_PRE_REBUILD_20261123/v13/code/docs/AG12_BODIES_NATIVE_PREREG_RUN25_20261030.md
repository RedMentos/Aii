# Run25 preregistration — two distinct native Body organs on existing AG12 German/English suite

Owner: GPT-6 scheduled continuation. Review-only child of Run24 PR #1351 at exact source head `f86c93b40d84d66a05bad0fa672a1f35bb8ac93e`. Binding Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`; source, model catalog, solver, and seed unchanged. This document is committed before executable Run25 code and before any native run.

## Fixed identity and procedure

Use the current exact catalog `v13/code/specs/models.json` blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` and `v13/code/v13/agi/solver.py` blob `66a9419143c456f01747b4796fb327b3b36711b3`. Two **distinct** public models, no substitutions:

- B1_DETAIL: LiquidAI/LFM2.5-1.2B-Instruct-GGUF, revision `6767265158422fb8a19c62ceb45f16f05363615b`, LFM Open License 1.0, file 695755488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`.
- B2_GIST: ggml-org/Qwen3.5-0.8B-GGUF, revision `8fea620810c4afa23dd6443f999a48574c1611a3`, Apache-2.0, file 563036064 bytes, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`.
- Native runner: official ggml-org/llama.cpp `b10964` Linux x86_64 tar 16825086 bytes SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Download only immutable official HTTPS URLs, verify exact file size, hash and runner binary. No user-private material.

On isolated Ubuntu Linux x86_64, serialize bodies, using separate fresh home and closed SQLite Store per body; only one native body resident at a time. For each body run existing `sv.run(growth,runtime,name,lang=lang)` for the full **seed13 German 88 items then English 88 items**, existing prompts, grammar, max tokens, confidence and scorer, at most 12 minutes per language. Exact 2 × 2 × 88 = **352** scored role-calls. Preserve failed, partial, timeout and cancelled attempts, original native raw, stage exits, model/runner hashes and source HEAD. Export only per-row ID/correctness/confidence and aggregate diagnostics, not prompts, answers, private conversations, models or training data. Verify no events/messages were added, native process reaped, and role isolation (B1 never B2 or C3; B2 never B1 or C3). Keep separate AG9 English/German components. Do not overwrite the C3 Run24 original artifact.

## Scope and acceptance

Preflight software tests must check catalog/model role binding, tamper/host rejection, no preexisting home, language order, no silent synthetic fallback and no cross-role mixing. Native success requires both models' exact verified bytes, 88 DONE rows in each language for each model, 352 actual calls, no runner errors, and closed runtime. A failed native stage is RED and retains original raw, not a fake PASS.

Results are Linux-native **procedural diagnostics only**, not proof of learned German transfer, Body JEPA or functional two-hemisphere advantage. AG12 English/German prompts differ; comparisons are descriptive. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; no Redmi measurement, learning promotion, production merge, AGI or whole-V13 completion. The existing 4 failures / 66 errors / 16 skipped historical full-suite baseline is not waived. No paid provisioning or auto-merge.
