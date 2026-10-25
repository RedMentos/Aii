# Run263 — pinned public weights and Linux-native Age-0 smoke result (2026-10-25)

## Exact evidence and failure retention
- **Tested workflow head** `5b1900666e6a8ba3186c19a93b5507e811012fb1` (PR263, production source based on PR259 `28a9ebcbe51661adb716ae5bdd9ca999dbf2af3c`). Later proof-only commits did not alter model/Runtime source or workflow code under test.
- GitHub Actions run https://github.com/RedMentos/Aii/actions/runs/40186015827, job `121146839174`: **SUCCESS**, `RUN263_BOOTSTRAP_EXIT=0`, `RUN263_MANIFEST_EXIT=0`, `RUN263_NATIVE_EXIT=0`, privacy **CLEAN**.
- Closed raw artifact `12595468847`, ZIP SHA256 `9d9396b5f8d6bf4f4e3e6e41d4bbfc23452c99d2a4272a821b8b823e95879ffa`. Includes fresh host preflight, model hashes, bootstrap/build logs, native probe JSON, exact exit codes. No model bytes published.
- Initial preflight FAIL run `40185883125` remains recorded in `FAILED_PREFLIGHT.md`: wrong synthetic merge checkout; **no native execution** on that attempt. Corrected exact-head checkout; no force push.

## Actual registered native model evidence
- Host: GitHub Linux x86_64, 4 CPUs, Python 3.12.3, kernel 6.17.0-1022-azure. **Not Redmi/Android.**
- Downloaded all registered public models and pinned native runner through existing `v13.bootstrap`. Deep size/SHA256 checks passed for every installed model file and Needle platform dependency.
- B1 DETAIL `LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf`: 695755488 bytes, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`.
- B2 GIST `Qwen3.5-0.8B-Q4_0.gguf`: 563036064 bytes, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`.
- C3 LANGUAGE `LFM2.5-350M-QAD-Q4_0.gguf`: 219312832 bytes, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`.
- C2 CONTROL `needle3.cact`: 35335380 bytes, SHA256 `c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38`.

| Native role | Probe | Generated tokens | Duration (s) | TTFT (s) | sampled peak RSS (MiB) |
| --- | --- | ---: | ---: | ---: | ---: |
| C3 LANGUAGE | FINAL | 32 | 0.678 | 0.382 | 486 |
| B1 DETAIL | FINAL | 25 | 1.196 | 0.563 | 1395 |
| B2 GIST | FINAL | 10 | 1.398 | 1.154 | 1266 |
| C2 CONTROL | FINAL | separate Needle result | 0.101 | n/a | n/a |

- `probe.status=SMOKE_PASS`, all four roles `ok=true`. Native bodies were unloaded and their processes reaped after each probe.
- This establishes **Linux-native smoke inference with registered model weights** on this exact host; it does not establish quality, sustained resident memory, two-body complementarity, learned weight updates, thermal/energy, phone proof, STEP2 or B3.

## Original gates unchanged
- `STEP2=UTILITY_FAIL`; `B3_L1=FAIL`; `Body_JEPA=UNAVAILABLE`; `jepa_weight=0`; full V13 `INCOMPLETE`.
- `CAN_TRAIN_BODY=false` for B1/B2; latent receiver authority absent; Age-0 higher-age OFF; C3/Body learning remains SHADOW.
- Next: verify PR265 exact-head full suite after synthetic source-scope fix, independently resolve Run261 terminal failure evidence under PR259 owner, then preregister real paired B1/B2/C3 second-attempt/STEP2 utility using unchanged source/model/seed hashes. Run Redmi longrun only on the actual phone.
