# Run52 — JEF/C2 C_fast SHADOW persistence and exact restart (isolated)

Preregistered FIRST at `11c1709c13bfb0ae4d3cac25f4344a4e9ef0271f`, parent Run51 `6aaf8b29fe40428a2316513c4a344eaad4109401`. Only this folder owned. No production, Run40/41, native weights, user rights or Canon modified.

Canon §3.4.6–3.4.9 and §14.2: C_fast route/wake/halt/report learning and fast persistence, local eligibility and one authorized external Action/Report Gate. **New synthetic CPU microcandidate**, NOT native C2/C3. Frozen six binary features, 6→32 ReLU trunk and four heads, Adam 0.03, 200 batch64 updates, one CPU thread. Source hash and dataset fingerprint checked, weights in safetensors, Adam moments/step in non-pickle NPZ, generation-specific files and manifest-last atomic write. SHADOW only, no Age/action/latent authority.

**100 updates + checkpoint + restore + 100 updates equals uninterrupted 200 updates bitwise** for all weights, Adam moments and predictions. Two-restart chain also bitwise. Simulated pre-manifest crash leaves previous generation accessible. No physical power-loss proof or signed external source trust root.

Evidence: initial **13/13 PASS**. Adversarial review added source-hash and optimizer dtype controls, reproduced **2 FAIL of 15** before fix. Final **15/15 PASS**, Python -O **15/15 PASS**, compileall PASS. Balanced synthetic 128 examples, 32 per route with replacement from the 64 possible binary states: candidate route accuracy **1.0**, report Brier **1.982e-6**, untrained accuracy **0.1953**, shuffled-label control accuracy **0.25**. This is synthetic label memorization, not real user generalization. Run40 original negative result and Run41 prereg remain unchanged.

Closed source/tests/red and green logs/metric JSON in `run52-code-raw.part1.txt`…`part3.txt`; concatenate without separators, base64-decode, Brotli-decompress and untar in disposable directory. Decoded tar.br SHA256 `c6e19aa34d2bfd8a14eaf905f605a46bdb7c761396366c4fa52cf05b4a2192de`. All parts re-read and verified by Git blob. Reproduce: `python -m unittest discover -s tests -v`, `PYTHONOPTIMIZE=1 python -m unittest discover -s tests -v`, `python scripts/run52_metrics.py`. Requires PyTorch, NumPy, safetensors; no model downloads.

Primary technical sources checked 2026-10-24: https://huggingface.co/docs/safetensors/api/torch and https://docs.pytorch.org/docs/main/generated/torch.optim.adam.Adam_class.html.

Open: full checkout/official privacy scan; real C2/C3 weights, real outcome labels, distributed neuromodulation/eligibility, source authority, Android power-loss tests, concurrent checkpoint owners. No native/Redmi/full-system claim. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE unchanged.