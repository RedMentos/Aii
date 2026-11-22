# Run92 prereg — current pinned C3 350M real Linux causal streaming baseline/zero (2026-10-29)

Owner GPT-6 scheduled continuation. Independent review-only child of **raw-verified GREEN** Run83 #990 exact `3545dab0faa3d548df58557ed8376a6162c51d9a`. This is the first fresh **current-source native C3** check in this continuation, not a repeat of historical 2026-10-09 230M/older runner proofs. Do not alter registered model/source/seed/cohort hashes or existing failed attempts.

## Frozen exact public artifacts, provenance and licenses
- C3 `LiquidAI/LFM2.5-350M-GGUF` exact revision `657e078c94084481950a2d555a941481f715536b`, `LFM2.5-350M-QAD-Q4_0.gguf`, **219312832 bytes**, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, **LFM Open License 1.0**; never upload model bytes.
- Pinned `llama.cpp` release tag `b10964`, Ubuntu x64 archive 16825086 bytes SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`; source tar SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`.
- C2 Needle-3 support required by current `install_native`: `Cactus-Compute/needle3` revision `b274efcb211a9eef48c9a88da4b43bd569696a39`, Apache-2.0, `needle3.cact` SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`. Do not claim a C2/Needle proof from this C3 test.

## Fixed test protocol
1. Ubuntu 24.04 fresh isolated home/venv, no existing user data. Install **only** pinned language and needle via `ModelManager.install("language")` / `install("needle")`, then `bootstrap.install_native(home)`. Capture original install, model deep-hash and runner provenance in closed raw logs. Do not use setup.sh to download all bodies.
2. Run existing `scripts/test_native_prefill_stream.py` **unchanged** with `--baseline-zero`, authored synthetic prompt `Hallo! Was kann ich als Erstes fragen?`, `--max-tokens 64 --seconds 90 --rss-limit-mb 768`, isolated out-dir. Require source-bound native guard, exact context binding, baseline/zero token parity, real native decode and child process teardown as enforced by existing script; do not weaken limits if RED.
3. Run existing stream protocol software tests, source/hash checks, privacy/diff, raw logs/report and SHA256SUMS. Archive only logs, source identity and hashes, **never GGUF, binaries, private data or cached model**.
4. If download/compile/native fails, preserve full original RED, exact prerequisite and continue other authorized paths. No synthetic replacement for native. No source/seed/cohort change, no phone claims.

## Fixed source blobs
`specs/models.json` 7af05962af41d0bc3f7dd18ef01d4eba55eabf99; `v13/bootstrap.py` dc23e192bcd01589475692666ebb6568c80d078b; `v13/models.py` bd035cf8029850cce00b179edf533e53bf24358a; `v13/runners.py` efda7aa1aa5729e974d0d641870d4da05d21c961; `scripts/test_native_prefill_stream.py` ef5f4097c6cf40bae38b083312c7e621f6a3ebb6; `scripts/native_prefill_stream.cpp` 97b4d12648961b80a4e43b8e84e50b9d6369eefb; `scripts/native_prefill_stream_client.py` ded6a16ee428d7857f7a525d0688b25061e66d25; `scripts/native_prefill_worker.cpp` cdf7450e9d8032218afbc73062836d4d81edf605; `scripts/test_native_prefill_port.py` 64fb49deb7ab53d05ce4c4afbe9f7d0e71068cfe; `scripts/test_native_prefill_stream_protocol.py` 28258346937142968146a42e558c4d7da6959e54; canonical SSOT 218464b12a2d27d92524c751922fa8e1c3fb0ea7.

## Claim limits
Linux x86_64 **native C3 stream only**, not Redmi RAM/thermal/battery, C3 semantic quality, B1/B2 learning, JEPA, B3 receiver, STEP2 utility, Body-JEPA, LP3 or whole V13. Keep all original negative gates, Age0 RECORD_ONLY and zero learning/approval authority.
