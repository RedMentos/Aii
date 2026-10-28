# Current-catalog B1/B2/C3 artifact-only Linux verification prereg — 2026-10-28

This is a distinct **artifact retrieval and byte-hash proof**, not native inference, not an experiment cohort, not a new model selection, and not a step toward automatic age/gate promotion. Do not alter `specs/models.json` or an installed user's home.

Pinned source prerequisites on review chain: `v13/code/specs/models.json` Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`, `v13/code/v13/models.py` Git blob `bd035cf8029850cce00b179edf533e53bf24358a`. Current catalog exact roles:
- B1 body LiquidAI 1.2B QAD `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`.
- B2 gist Qwen3.5-0.8B Q4_0 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`.
- C3 language LiquidAI 350M QAD `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.

Use only existing `ModelManager.install`/`verify(deep=True)` into an isolated ephemeral Linux scratch home with bounded disk and time; no heavy jobs concurrent with an active full-suite/native owner. No model file upload, cache publication or paid resource provisioning. The only persisted output may be a sanitized report containing exact model IDs/revisions/sha/size, verified GGUF header and license identifiers, plus closed raw logs and exit codes. If downloads fail, retain failure and continue other work; do not claim verified bytes from metadata alone. Never infer Redmi hardware proof from Linux download success.

This package must not alter the historical STEP2 fixture, model or seed cohort. Any subsequent native 12-run test requires separately registered actual installed model/runner/source bytes, lock owner and resource preflight, and may still fail utility.
