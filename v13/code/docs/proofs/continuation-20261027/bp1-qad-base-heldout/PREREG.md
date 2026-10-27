# BP1 pinned QAD Q4 native base-only 22-response heldout baseline — prospective (2026-10-27)

Owner: GPT-6 independent review; child of active V2 LoRA evaluation source `f6d6812a493cc7d2235e97bf16e0324242d1ecd6`. Purpose: obtain the first **genuine QAD Q4 base model** source-disjoint heldout baseline independently of LoRA training, without needing adapter bytes or changing any cohort. This does not promote C3 utility or STEP2.

Immutable inputs: original PR677 BP1 heldout `heldout_paired.jsonl` SHA256 `7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c` (11 source pairs × no_offer/offer = 22 prompts), source artifact `12715684803` ZIP SHA256 `12a66c12019ee267cac12defd0b281f34fbcac5dc1f2e941236ae4ebf9a5f56c`; original official QAD Q4 GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d` at HuggingFace revision `657e078c94084481950a2d555a941481f715536b`; pinned llama.cpp b10964 binary release SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, `llama-server` binary SHA256 `79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39`. Seed13, greedy JSON-schema, max192, thinking off. Only prompt leaves the dataset reader, never target/answer key.

Implement a base-only collector that emits the same six-field prediction row schema as V2, with `model=base`, exactly 22 rows, source and prompt hashes, append-only resume with exact binding and duplicate/partial checks, owned loopback server and explicit no-adapter launch. A separate source-bound software scorer counts supported/abstention/invalid quote by no_offer/offer and retains raw outputs; it must mark native evidence as unverified until original runner raw is independently audited, and must never claim training or utility.

Software tests first: no source/runner/model/seed drift, no target leakage, no duplicate/missing rows, resume strictness, owner confirmation, negative gate preservation. Run genuine native **only after** the active 25-row train owner finishes; use same concurrency group to serialize. Save original raw ZIP and hashes, no private weights, no public secrets. Synthetic mocks are software-only.

This base-only result is a baseline, **not** paired candidate-vs-base proof; candidate remains pending real LoRA export/adapter retention and separate 44-row V2 preregistered evaluation. No retention/near-miss promotion from these 22 prompts.

STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Redmi unmeasured, full V13 incomplete.
