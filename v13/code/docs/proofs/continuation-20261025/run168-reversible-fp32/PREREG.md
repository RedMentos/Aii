# Run168 prereg — reversible private GGUF F32 slice patch (NO active model update)

Date 2026-10-25. Exact base Run166 `6c8a6c0b4eec5d6890d7171ecf3bb90aa7b0dc18`. Owner new script/tests/workflow/proof only. Frozen Runtime/Canon/model registration/cohorts/Run160–166 unchanged. No native inference/training or production activation.

## Purpose / exact precommitted source
Registered B1 GGUF revision `6767265158422fb8a19c62ceb45f16f05363615b`, size 695755488, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`. Recreate Run162 private F32 master (first four sorted eligible 1D F32 vectors), Run163 external-SHA byte audit, Run166 synthetic Torch micro candidate. **Only** those four proven source spans may change in a **new exclusive private GGUF copy**, never in registered model. No quantized tensor touched, no requantizer claimed.

## Test plan / pass criteria
- Bind source model/master/report/micro candidate to SHA, schema, selected names, shape, F32, baseline bytes and source offsets. Reject missing, overlapping, quantized, nonfinite, wrong baseline, symlink/existing output, altered hashes, oversized vectors.
- Stream-copy source GGUF into private output with bounded RAM. Overwrite exactly the selected F32 slices with Run166 `updated__` vectors; ensure no changes outside selected spans by byte-range comparison, same size/header/metadata, and original source SHA unchanged.
- Record patched private GGUF SHA (must differ), then **restore original source bytes in that private copy**, require final full SHA == registered original. No altered GGUF left for deployment; no model inference or semantic utility claim.
- CI serial with `v13-native-c3-run131-serialized`, pinned public B1 download and CPU Torch, no concurrent heavy job. Delete model/master/micro/patched copies on EXIT, upload metadata only, preserve failures, official privacy scan.

## Gates / limits
This proves a reversible binary file data path only. Run166 objective remains a synthetic quadratic, **not JEPA**; no actual native model receiver, inference output, train master lifecycle approval, retention, requantizer, Redmi or full V13. `STEP2=UTILITY_FAIL`, `B3_L1=FAIL`, `Body_JEPA=UNAVAILABLE`, `jepa_weight=0`, `DS2_H2=FAIL`, `V13=INCOMPLETE`.

Next after proof: exact pinned native llama.cpp loader + inference of temporary changed GGUF with paired ablation, real predictive latent target and utility/retention; no active installation until gates and user approvals.
