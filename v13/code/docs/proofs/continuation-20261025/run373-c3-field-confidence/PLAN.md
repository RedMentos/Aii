# Run373 — pinned Linux-native C3 answer-field confidence diagnostic (preregistered)

Parent: Run372/PR367 checkpoint `8d204939c62ba35ef6a457cebd469bafbb1d4f2d` (review chain, not main). Run369/PR364 original native smoke script/workflow remain owned by that PR and **unchanged**. Its exact Linux-native raw Actions 40233093916 shows native C3 loaded, generated plain correct text, then AG12 JSON answer `","` with `confidence_source=mean_prob`; the workflow's native plumbing passed but answer-field confidence and useful solver answer were not demonstrated. Independent review was submitted on PR364.

Owner: new `v13/code/scripts/run373_c3_field_confidence_native.py`, new `.github/workflows/run373-c3-field-confidence-native.yml`, this proof directory only. Existing `v13/runners.py`, `v13/agi/solver.py`, `v13/focal.py`, catalog and all registered cohorts are read-only for this package.

Artifacts (exact unchanged catalog pins):
- `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, GGUF size 219312832, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, LFM Open License 1.0 per `specs/models.json`.
- `llama.cpp` b10964 Linux-x86_64 release size 16825086, SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`.
- Isolated runner temp, verified hashes and confined tar extraction; same serialized heavy native concurrency group as Run369. No model bytes in raw ZIP.

Fixed preregistered prompts and expected answers (English, seen-style, no training): `Compute: 7 + 5 = ?` -> `12`; `Compute: 9 + 1 = ?` -> `10`; `Write backwards: dog` -> `god`; `Continue: 2, 4, 6, ?` -> `8`. Four actual `BodySolver.ask` grammar calls. Plain-text control: `What is two plus two?` and `Compute: 7 + 5 = ?` without JSON grammar. Use current Run372 structural abstention and original `focal.token_confidence` implementation; record `field_tokens`, `field_min_prob`, `field_mean_prob`, `mean_prob`, `confidence_source`, answer, correctness, timings and sampled RSS.

Separate acceptance: `native_plumbing_pass` requires hash-verified model/server, actual FINAL generations, unload/reap and no training; `field_confidence_supported` requires >=3/4 grammar calls with **exact correct answer**, >=1 field token and finite field-specific probability (`field_min_prob` or `field_mean_prob`). If not, label `FIELD_CONFIDENCE_NOT_SUPPORTED` and fail the enforcing workflow **after** raw evidence upload; do not claim a field-confidence PASS from generic `mean_prob`, or retune thresholds after observation. Plain controls are diagnostic, not promotion.

No Redmi, STEP2_EXIT, B3, Body-JEPA, jepa_weight, Age, whole V13 promotion. Preserve all original failed attempts. After native diagnostic, continue independent blueprint packages rather than blocking on C3.
