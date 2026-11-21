# Research & Perception handoff — RAW EAR V3 / WebRTC VAD comparison

**Date:** 2026-11-21  
**Scope:** V14-006 / A0-A5 / RAW EAR / A4 attention  
**Base dependency:** Perception PR #2177, exact producer blob `7b1d519cd36ede4b520d78e22c0f89132a1c73a5`, temporal state blob `f693f8b8394558a63d87a35fc67ea3db9dcb1929`.

## New executable artifact

- `v14/experiments/raw_ear_vad_compare.py`: local-only comparison harness for RAW EAR V3 against either a real `libfvad.so` C library (`ctypes`) or the test-only `webrtcvad-wheels` Python wrapper. It loads the V3 extractor via AST to avoid importing Runtime, requires caller-provided PCM16 WAV and separate timestamp annotations, aligns 20 ms WebRTC decisions into 40 ms / 20 ms-hop windows, runs raw and shared-temporal comparisons, and emits only aggregate metrics/source hashes.
- `v14/experiments/test_raw_ear_vad_compare.py`: positive/negative contract tests, actual WebRTC wrapper smoke, and a compiled fake C ABI stub test for ctypes argument/lifecycle handling. The fake library is not evidence of real libfvad.
- `.github/workflows/v14-raw-ear-vad-comparison.yml`: test-only pinned `webrtcvad-wheels==2.0.14.post1` matrix for Python 3.13/3.14; no product dependency or model change.
- Research entry R-023 appended to `V14_RESEARCH_LEDGER.md`.

## Evidence

- LOCAL_LINUX isolated scratch mirror: `py_compile` PASS; `pytest` **5 passed in 0.42 s**.
- Actual local comparator: `webrtcvad-wheels 2.0.14` on synthetic 2 s harmonic signal, mode 2. V3 raw F1 0.8276 / FPR 0 / FNR 0.2941 / onset 20 ms / offset 40 ms / wall 135.3 ms / CPU 134.7 ms. WebRTC raw F1 0.9444 / FPR 0.125 / FNR 0 / onset 20 ms / offset 160 ms / wall 0.442 ms / CPU 0.443 ms. Whole-process peak RSS 98,316 KiB; not per-backend or Android.
- Synthetic noise-only and impulse-only negatives were run; see R-023 for counts. These are not speech-corpus accuracy claims.
- Full Aii checkout/local exact tests: BLOCKED by GitHub DNS. The local scratch copy contains the V3 algorithm excerpt, not the full repo source file.
- Real `libfvad.so`: unavailable locally; its C adapter is only ABI-smoke-tested against a fake stub. Actual libfvad build/test is BLOCKED.
- Exact-source CI: run 44891098086 PASS, Python 3.13 5/5 and Python 3.14 5/5; both verified V3/temporal Git blob hashes and ran WebRTC + fake-C-ABI checks. Existing V14 model-lab run 44891067617 PASS (28 tests, 2 optional WebRTC skips). An initial model-lab failure 44890888702 from a pytest import was fixed by converting tests to unittest; the correction is verified.
- Redmi / Termux / microphone: REDMI_UNVERIFIED. No deployment or device action.

## Source/license boundary

- `dpirch/libfvad` master `532ab666c20d3cfda38bca63abbb0f152706c369`: BSD-3-Clause plus separate WebRTC `PATENTS` notice/grant; no code imported.
- `daanzu/py-webrtcvad-wheels` release `726a8c72ce8b33b2df7ecd292372690fea2bad0c`, 2.0.14.post1: MIT wrapper + BSD WebRTC C; desktop wheel support only, no Android/aarch64 wheel evidence.
- S4VAD arXiv:2609.11110 remains paper-only; R-022 contains the prior full-text review. This run only rechecked the abstract because PDF fetch failed.

## Integration boundary and next owner action

This is an evaluation tool, not a Runtime microphone consumer and not a replacement for RAW EAR's nonverbal/prosody channels. Do not mark A0-A5, VOICE_AUDIO or V14-006 accepted. Do not add a product dependency, download model weights, or swap models.

**PR:** #2187, head `6333a2c95b85342c341fcfe00a6e4693bd56f2c0`, stacked on #2177 and still DRAFT / NOT_RELEASED. Exact-source CI is green. **Next:** Boss independently reviews/merges #2177 first; then rebase this stacked comparator onto the integrated release head, build the pinned C library for Termux/aarch64 and evaluate on an appropriately licensed annotated speech/noise corpus. Core may later use a fast native VAD gate alongside RAW EAR prosody, but only after matched CPU/RSS/onset/FPR/FNR and Redmi measurements. Boss owns shared board and user-next-action synchronization; proposed V14-006 note: `LOCAL_LINUX_ISOLATED_SYNTHETIC` harness added; exact-source CI pending; real libfvad/ARM/Redmi unverified.

No user action is required.
