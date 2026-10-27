# Run630 prereg — real llama.cpp C3 GGUF adapter consumption

2026-10-27 UTC. Review-only child of Run629 PR624 exact verified head `9186dec6609a45f18eeb3063c68f9a267e0b601e`. Run629 actual CPU LoRA result (Actions 40424448052) is immutable evidence, **not** a deployed-model result. This experiment is preregistered before new probe code, tests and native execution. Exclusive new files: Run630 script/tests/workflow/proof only.

## Frozen inputs

- Existing V13 `specs/models.json` runner: **llama.cpp b10964**, source revision `b29c606e2`, source archive 37,420,323 bytes SHA256 `4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe`; official Ubuntu x64 release archive 16,825,086 bytes SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Download only pinned official source/release, verify before use.
- Official HuggingFaceTB/SmolLM2-135M-Instruct revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, Apache-2.0, master safetensors SHA256 `5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c`. Convert **this exact master** to F16 GGUF using the verified b10964 converter. Record converted GGUF SHA and bytes. This is a new F16 conversion, not the production C3 Q4 GGUF.
- Run629 native adapter from original Actions artifact 12698827815, ZIP SHA256 `27e3aa76ef58bcdfc1682aa0c0cb6da429048a0fa910eb90801dbe49204862f5`, GGUF SHA256 `e2f84ae657b0b90891d7c5c042a897b9bd30021f8a16e399a27fa2704b793f4b`, PEFT SHA256 `516177efae6ce05ca2121b1c106ecbcddbf257bf0bc5b925e86589ce241aa345`. Verify both before inference; never silently retrain or change weights.
- Fixed synthetic train prompts (marker color, gate number) and disjoint heldout (2+2, greeting) from original Run628 cohort. No new model/seed/label or source selection.

## Experiment and interpretation

Run pinned Linux native `llama-server` with the converted F16 master (a) without adapter, then (b) with the exact Run629 GGUF adapter, making bounded deterministic `/completion` requests at adapter scale 0 and scale 1 on the same prompts (seed 13, temperature 0, one generated token and up to 64 logprobs). Require real adapter loader success, valid finite native outputs, owned-process teardown, and hash-closed raw. Compare base-vs-scale0 parity and scale0-vs-scale1 logprob changes with exact token IDs and non-overlap explicitly reported. If delta is zero, missing, noisy or parity fails, record `NO_NATIVE_EFFECT` or `PARITY_UNVERIFIED`, **not** success by assumption. A nonzero delta is a native C3 adapter effect, **not** answer quality gain. The two-step Run629 master learned recall was 0.0 and must remain recorded.

Source-only negative controls: wrong adapter/master SHA, malformed GGUF, mismatched evidence scope/gates, non-loopback server target and unsafe executable rejected before spawn. No external HTTP except pinned artifact/model/source downloads in CI; server binds loopback only. No production import/activation, model rights, age change or user data.

Original Run628 RED and Run629 GREEN artifacts remain unchanged. All STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, Redmi `UNMEASURED`, V13 `INCOMPLETE` gates persist regardless of result. This is Linux-native **reference C3** only, not current deployed Q4 C3 or phone. Record all failed attempts and independently review.
