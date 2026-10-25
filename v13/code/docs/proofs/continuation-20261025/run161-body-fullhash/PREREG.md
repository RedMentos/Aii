# Run161 preregistered full pinned B1 body GGUF integrity preflight

Base Run160 `36f2b57aeba3d5c1117350e8955ad78b71d2e578`. Owner Run161 only new workflow and proof; no source/model/runtime edits. Registered B1: LiquidAI/LFM2.5-1.2B-Instruct-GGUF revision `6767265158422fb8a19c62ceb45f16f05363615b`, file `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf`, size 695755488, SHA-256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, license LFM Open License 1.0. These values come from current frozen `specs/models.json`; no substitute permitted.

CI plan: serialized Linux runner with existing native group, download exact public pinned GGUF to ephemeral temp, check file size and full SHA-256, read first 32 MiB and run existing Run160 metadata audit. Assert model authority remains 0 and original gates negative. Delete model bytes after test, do not upload model weights or inference outputs. Preserve failed download/hash attempts in logs; do not call partial download a verified model. No model inference or training; no Redmi proof.

This is a prerequisite toward an independent train master and native gradient path, **not** a trainable Body-JEPA implementation. After full model proof, design separate FP32 slice extraction with data offset/size checks and no weight mutation; then actual native gradient/EMA/retention proof remains required.
