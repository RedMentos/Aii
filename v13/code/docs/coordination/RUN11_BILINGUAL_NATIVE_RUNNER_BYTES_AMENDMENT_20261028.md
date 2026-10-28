# Run11 native collector actual-runner byte identity amendment — 2026-10-28

Independent review before native execution: mapping `runner.role` directly to the expected catalog SHA in a collected answer is **not a measurement** of which file the native runner actually loaded. AG0/BodyFabric routing can select a different path. The collector must never fill `runner_model_sha256` from a static role map and present it as observed.

Before each row is finalized, read the persisted `metadata.runner.actual_model` and the Runtime's selected `models.path_for(role)`; require exact basename agreement, compute the **actual file SHA256** from the selected path, and store that measured hash. On any missing/changed path or absent actual_model, retain raw row with explicit failure and let the strict scorer refuse it. Preflight still pins the original model catalog and verifies installed bytes before any turn; this extra per-row check protects against live route/path mismatch. No model, runtime, prompt, seed or age policy changes.

Falsifier: forged B1 role with a C3 actual_model must fail, even if the expected B1 SHA is known. A software mock proves the guard, not native model identity. Native evidence requires real execution and independent raw review.
