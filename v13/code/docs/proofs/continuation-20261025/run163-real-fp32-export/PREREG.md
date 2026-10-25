# Run163 preregistered real B1 FP32 inference slice export, no training

Base Run162 `001e7af6748186b4c1c21ad357a06680079aef44`. Owner Run163 only new serialized CI workflow and proof. Do not edit Run162 exporter, frozen Runtime, model manifest, native runner, or original V13 gates.

Run161 independently verified full B1 model bytes: registered LiquidAI/LFM2.5-1.2B-Instruct-GGUF revision `6767265158422fb8a19c62ceb45f16f05363615b`, size 695755488, SHA-256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`. Run162 synthetic 10/10 plus inherited GGUF parser 8/8 PASS.

New CI will serialize with existing heavy native group, download exact full B1 again, verify full SHA before any extraction, select exactly `blk.0.attn_norm.weight` and `blk.0.ffn_norm.weight` (both declared F32 in Run160 verified prefix metadata), export to separate ephemeral NPZ using Run162, verify exact roundtrip and unchanged source SHA, delete both original model and NPZ, and publish **metadata/hashes only**. No model weights or tensor values may be uploaded to GitHub.

The export is **not native training**: no gradients, teacher signal, EMA, requantization, model swap, retention, Redmi or utility proof. Train authority 0, Body-JEPA UNAVAILABLE, jepa_weight 0, STEP2 UTILITY_FAIL, B3 L1 FAIL, DS2 H2 FAIL, V13 INCOMPLETE. This CI should only be triggered when Run159 full-suite heavy job is no longer active; do not overlap.
