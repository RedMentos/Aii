# HB1a / P0 native two-body source-offer pilot — preregistration (2026-10-29)

Owner: GPT-6 scheduled continuation. Independent review branch based on **verified HB0c native PR #1050 exact `17c989f1cf2f7f5ca25d388afa47044d6f69898b`**. Commit this registration BEFORE any HB1a implementation or native calls. The Canon `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` and original STEP2/LP/B3/JEPA registrations remain unchanged. This is a small public synthetic **diagnostic**, not a blind held-out acceptance cohort.

## Question and fixed source

Can real, distinct native B1_DETAIL and B2_GIST models produce source-grounded offers which a real C3_LANGUAGE receiver can use for the current project, beyond C3-only and same-model/two-timescale controls? Do source-separated offers preserve project identity when B1 is foreign? This is not a claim of JEPA learning or semantic complementarity.

Use the **unchanged** HB0 fixture generator source Git blob `329153aaa73df009fdc433523994e372e0fd2c95`, exact externally registered 150-row fixture SHA256 `73c9f4096a928ece659cfa5aff0c483001346834f6117765ed1c53c9c2b7939b`, and only family=5 (six paired 2×3 counterfactual rows, two each A/B/NONE). No new seed, fixture, or oracle in model prompts. Parent HB0b source-view exporter blob `8d6f5b9f0830540d2de72cc624778ff03e7b90ec` stays immutable. Model-facing inputs must be independently allowlisted; never serialize a fixture dict.

## Models and permissions

Use only existing pinned public catalog models (no replacements or unreviewed model download):
- B1_DETAIL LiquidAI/LFM2.5-1.2B-Instruct-GGUF revision `6767265158422fb8a19c62ceb45f16f05363615b`, SHA256 `bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1`, LFM Open License 1.0.
- B2_GIST ggml-org/Qwen3.5-0.8B-GGUF revision `8fea620810c4afa23dd6443f999a48574c1611a3`, SHA256 `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf`, Apache-2.0.
- C3_LANGUAGE LiquidAI/LFM2.5-350M-GGUF revision `657e078c94084481950a2d555a941481f715536b`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, LFM Open License 1.0.
- Existing llama.cpp runner tag b10964 and exact source pin from catalog. Linux x86_64 CPU only; no Redmi claim.

Age0 RECORD_ONLY, latents off, jepa_weight=0, no adapters, no tools, no training or model writes. Fresh isolated V13_HOME; one native runner at a time with teardown on role changes, no concurrent heavy owners. Resource admission requires at least 3.5 GB available memory, 3 GB cgroup cap, 4 GB disk free. Fixed seed=13, temperature=.1, threads=2, 96 max output tokens for each body, 48 max C3 tokens, 90s per native call, 50-minute overall cap; source and model/binary hashes checked before and after.

## Fixed generation plan (54 serial native calls)

For each of six rows, run exactly four source-bound body calls: B1_DETAIL on current B1 supplier sheet only; B2_GIST on current B2 rule notes only; B1_DETAIL on both current exact sources as a single-body/two-timescale control; B1_DETAIL on a **foreign-project** supplier sheet with its original foreign header (no relabeling). The four calls are 24 total. Each prompt asks to quote or summarize only its own source, retain exact project identity, never guess missing values, and not decide an action. Raw outputs are **model-derived and untrusted** even if source hashes are authentic.

Then for each row run C3_LANGUAGE in exactly five arms (30 calls total): `c3_only` (current request, no sources); `both_exact` (both exact source texts); `both_native` (current B1 and B2 model-derived offers with their original project labels); `single_body_native` (one body summarizing both sources); `shuffled_native` (current B2 offer plus foreign B1 offer, explicitly labeled foreign). Never pass answer keys, oracle, family/sheet/rule index, or a generated offer as if it were exact source text.

For C3 use the existing native `schema` / `json_schema` interface with a single required `action` enum `A|B|NONE|UNKNOWN` and no other fields; count malformed JSON as UNPARSEABLE, do not repair or silently replace. The schema is a **new registered output format**, not a rescore of HB0c. Compare exact/wrong/unknown/unparseable per arm; count foreign-source commitments explicitly. Preserve body source/role/revision/input hashes, all raw outputs, timing and RSS, schema, native call counts and failed attempts. Exact source may be used as a deterministic non-model control but never as evidence of generated body competence.

## Gates, evidence and failure

Before native: software tests for six×four body plan and six×five C3 plan, no-oracle inputs, foreign identity, hashes, missing/duplicate/tampered records, malformed schema output, nonfinite metrics and failed admission. During native: serial owner, model/runner SHA before/after, exact call count, restart/teardown, closed RAW, SCORE, RECEIPT, SHA256SUMS and privacy scan. Preserve every RED attempt. Use GitHub Actions branch-only, no production merge, and keep original raw in permitted private backup only; no public private data.

**No gate promotion regardless of result:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; V13 INCOMPLETE; Redmi unmeasured. This six-row public diagnostic cannot establish independent 150-row P0 utility, source-verified native B1/B2 complementarity, B3 latent authority or JEPA learning. Next acceptance package needs a fresh preregistered independent 150-row held-out model-native cohort with confidence intervals and real Redmi checks.