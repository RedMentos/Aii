# V13 current-source C3 native Linux smoke recheck — prereg 2026-10-30

Review-only child of verified #1187 at `eec47c269eadd08a1d6035107ea6351cc5af1268`. **No runtime/model/catalog edits.** This is an independent C3 execution evidence package, not the other owner's Body-JEPA experiment.

Goal: re-run the existing `scripts/current_c3_native_linux_smoke_20261028.py` against the current integrated JEF/C2 source using immutable official `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` (219,312,832 bytes), pinned official llama.cpp runner tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443` (16,825,086 bytes), original catalog and manager Git blobs unchanged. Prompt `Hello.`, 12-token cap, CPU/Linux x86_64, one native call, no private inputs.

Required: preserve original complete stdout/stderr, runner and model hashes, dependency provenance, exact head, exit codes, native report, source/Canon hashes, privacy/diff and artifact SHA256. Native Linux C3-only evidence **does not** prove JEF/C2, B1/B2, JEPA, STEP2, Age, Redmi performance or full V13. Do not publish model weights. Failure remains RED; do not silently swap artifacts or change seeds.

**Serialization:** a pinned Torch/Transformers/PEFT unfiltered full-suite job `40984606331` is active. Do not trigger this heavy native job until that one has completed; a workflow file will be added only after it closes. Exact next command after release: `PYTHONPATH=v13/code python3 v13/code/scripts/current_c3_native_linux_smoke_20261028.py --scratch-home <fresh> --evidence-dir <fresh>`. Runtime budget UNKNOWN.
