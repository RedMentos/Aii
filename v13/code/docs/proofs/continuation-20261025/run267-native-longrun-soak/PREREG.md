# Run267 — actual native Linux G13 two-day restart soak (prereg 2026-10-25)

Base: PR265 exact head `bff28504ffc682a3f63a2e4165d0547f6ce3d539`, incorporating PR264 synthetic WorldModel ablation fix; PR265 full suite is independent and pending. Owner: `scripts/longrun_soak.py` only for native asset binding, new focused test/workflow/proof. No Runtime/Store/WorldModel/Canon/seed/model registry/native runner source edits; no other active owner overlap.

Problem: `longrun_soak.soak(..., native=True, models_from=...)` linked the installed `models/` but **not `bin/`**, leaving an isolated Runtime with registered model bytes but missing `llama-server` and Needle native runner binaries. This is a test-runner integration defect, not evidence that the models failed. New `attach_native_assets` binds both installed directories plus the exact model manifest and refuses foreign existing directories/symlinks/manifest drift rather than overwriting operator data. Native evidence stays isolated from the source installation.

Predeclared software tests: binding both models/bin, idempotence, mismatch refusal, missing runner refusal, and existing 3-day fixture soak; no model utility claim from these.

Predeclared native CI: shared serialized heavy group; fresh GitHub Linux host; pinned isolated Python; exact registered public models/native runner through existing hash-validating bootstrap. Run existing `longrun_soak.py --native --models-from` for **two simulated days and two actual native user turns per day**, with real Runtime process restart, durable turn queue, G13 scheduler priority, replay, full sleep job, fact recall, Age stability, store integrity, no job errors and bounded DB growth. Preserve full raw log/report and true exit code. A FAIL remains FAIL. `longrun_soak` internally labels native mode `NATIVE_DEVICE_RUN`; in this CI the correct external evidence classification is **GITHUB_LINUX_NATIVE**, not Redmi.

Claim boundary: even a PASS is only 2-day simulated-wall-clock Linux native lifecycle, not seven-day actual phone thermal/battery/RSS, not two-body semantic improvement, not native JEPA learning. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE. No Drive rejected backup retry.

Exact next step: inspect focused and native CI, closed raw hashes, all per-day checks and process status; if failure, fix only proven harness issue or document true native blocker. Separately reconcile Run261 terminal outcome patch under PR259 owner and real STEP2 utility cohort.
