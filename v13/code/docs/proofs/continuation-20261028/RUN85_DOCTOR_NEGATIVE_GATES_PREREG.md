# Run85 prereg — model-less Age0 doctor and negative acceptance gates (2026-10-28)

Owner GPT-6 scheduled continuation. Independent review-only sibling of Run82-84, exact independently raw-verified Run76 #983 GREEN head `2fa443822f99b367d137f0254e69e20268f664e8`. Scope: real Linux Runtime/Store/Operator in a fresh temporary home, no model files or native runner installed. No production source changes.

## Frozen tests before implementation

1. Real Runtime with Sleep disabled, learning RECORD_ONLY; `:doctor` and `:doctor full` must return parseable JSON with `canonical_architecture_complete=false`, `data_integrity_errors=[]`, nonempty `missing_models` including language/body/gist/needle, `native_runner_exists=false`, `needle_embedding_worker_exists=false`, and no claimed native/phone readiness. This is an intentional **diagnostic success, not system acceptance**.
2. Native capability report must keep latent injection OFF, live receiver unavailable, body training unavailable, model-callable tools OFF; gate inventory B3 latents OFF, higher age OFF, vision/audio UNAVAILABLE. Completion ledger B3_LATENT blocked by proof, BODY_JEPA NOT_STARTED, STEP1 JEF only PARTIAL.
3. `:ledger` and `:gates summary` must not promote any unavailable gate. Persisted generated build artifacts should be present and inspectable under the temporary home; a restart must keep Age0 RECORD_ONLY and no newly installed model.
4. Patch native pool access to raise on any attempted call, prohibit network/model download, do not call `:probe` or model generation. Run focused new E2E + verification/age tests, full suite, privacy and original raw hashes in source-bound CI. Any mismatch RED; no change to frozen gates.
5. Linux software proof only. Missing native/Redmi/B1/B2/C3/JEPA/STEP2 acceptance remains. The doctor CLI exit code 0 for data-integrity success does not mean a runnable native model is installed or V13 complete.

Next after GREEN: use exact negative diagnostics to prioritize real pinned model/Redmi prerequisites, not to claim completion.
