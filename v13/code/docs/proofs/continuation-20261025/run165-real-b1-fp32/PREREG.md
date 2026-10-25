# Run165 preregistered pinned B1 FP32 read-only extraction and cross-audit

Date 2026-10-25. Base exact Run163 `c1f124d9db687e89cf16398797b5e453b02c5c9f`. Owner Run165: new workflow and proof only. Run160/161/162/163 source, frozen Runtime, Canon, model registration, original gates unchanged.

## Registered input (no substitution)
`LiquidAI/LFM2.5-1.2B-Instruct-GGUF`, revision `6767265158422fb8a19c62ceb45f16f05363615b`, `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf`, exact 695755488 bytes, full SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, license `LFM Open License 1.0`. Run161 independent Linux CI full hash PASS is prerequisite, but Run165 **must independently recheck full SHA and size**.

## Precommitted selection and proof criteria
Parse first 32MiB with the existing Run160 GGUF v3 parser. Select the first **up to four** tensor names sorted lexicographically for which `type=='F32'`, exactly one dimension, and `1 <= dimension*4 <= 16MiB`. Fail if none; do not change selection rule after inspecting data. Export selected F32 source slices to a separate ephemeral NPZ with Run162 exporter, check full model SHA, manifest and roundtrip. Independently verify the same NPZ with Run163 external-SHA-bound audit. PASS only if all exact checks succeed and all negative gates remain unchanged.

## Isolation and artifact policy
CI uses the existing `v13-native-c3-run131-serialized` concurrency group, `cancel-in-progress: false`, no concurrent native job by this owner. Download/read only, no inference, gradients, training, EMA, requantization or Runtime update. Model and NPZ stay in private runner temp and are deleted via trap even on failure; **never upload weight bytes**. Upload only metadata-only report and parser counts/hashes, preserving failures and source hashes in job log. Official privacy scan required. No paid provisioning.

## Evidence levels and gates
Expected `LINUX_CI_REAL_PINNED_B1_FP32_SLICE_EXPORT_ONLY`, not native training or Redmi. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

## Failure policy and next
Any SHA mismatch, unavailable model, no eligible tensor, parser/export/audit error or CI resource failure remains FAIL and is preserved. No posthoc tensor selection. Next after successful proof: separate train-master lifecycle, gradients, EMA, quantized roundtrip and real retained answer utility, all gated and independently reviewed.
