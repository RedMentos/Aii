# Run37 prereg — C3 rule-use / remaining-field prompt intervention (2026-10-28)

**Parent:** Run36 #945 at exact `7b0fab0a21edcbe5c35dc98118c02c97014b38d0`, independently audited original C3-only Linux-native five-arm Velaris result (Actions 40734479879, ZIP SHA256 e6b9f6454a451c1001ea45072bc4e738c455abbd2cfdbe8a6af0c0ab52328cbd). Original Run33 cohort, Run34/35 source and all original negative/failed evidence remain immutable.

**Motivation from preregistered Run36:** B1_B2_EXACT and B1_ONLY produced byte-identical answers; no action/remaining gain despite exact B2 rules. +1/12 exact-minus-missing came solely from the project field. A *new* preregistered, distinct-fixture intervention must distinguish (a) absent rules, (b) source-exact rule presence and (c) generic instruction to actually apply rules.

**Fixed new case:** `Elyndra`, EN SPLIT, seed `20261122` from Run33 registered cohort but **not** previously run in Run36. This is a new separately labelled exploratory intervention, not a retroactive change to the original cohort. C3 GGUF LiquidAI/LFM2.5-350M-GGUF revision `657e078c94084481950a2d555a941481f715536b`, SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`; llama.cpp b10964 x86_64 tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Frozen consumer JSON schema, scorer, source quotes and runner remain unchanged.

**Five ordered arms (one native process each, same seed):** `B1_ONLY` (frozen Run33 B1_ONLY); `DISTRACTOR_FROZEN` (Run33 B1_B2_DISTRACTOR, frozen consumer system); `EXACT_FROZEN` (Run33 B1_B2_EXACT, frozen consumer system); `DISTRACTOR_HINT` (same distractor source but append fixed hint to system); `EXACT_HINT` (same exact source but append fixed hint). This is a 2x2 exact/distractor × frozen/hint plus B1 baseline. No B1/B2 model inference; quote provenance remains SOURCE_EXACT and oracle never appears in model prompt.

**Fixed hint, UTF-8 SHA256 `5ac5fa2aa13a7d82edeb66b960eff443e7ed60b4ebf8f775987cb4fd4739a9c7`:**

> Use only the current source and source-exact verified quotes. If the quoted rules specify a budget, compute each option's remaining amount from that budget and its cost; if the rules specify a decision procedure, apply it to choose action rather than defaulting to NONE. Do not invent missing rules or quote text. Return only the required JSON schema.

**Primary outcomes (predeclared):** exact `action` correctness and count of correct `remaining` fields (0,1,2). Secondary: full `score_decision` utility, exact answer, all field checks. Report `EXACT_HINT - EXACT_FROZEN`, `EXACT_HINT - DISTRACTOR_HINT`, `EXACT_FROZEN - DISTRACTOR_FROZEN`, `DISTRACTOR_HINT - DISTRACTOR_FROZEN` for each primary/secondary outcome; do not equate a project-name-only utility gain with rule application. One case/seed is exploratory, no significance, no STEP2 promotion.

**Execution prerequisites:** source-only deterministic envelope tests, source/blob pin and privacy checks GREEN; independent review; exclusive native Actions group `v13-run11-age0-native-endtoend`, no active owner; pinned fresh installed C3+Needle support and runner; original raw receipt, failed attempts, hash verification, private Library byte-identical backup. Do not provision paid resources or change model/seed/cohort.

**Negative gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Remaining platform budget UNKNOWN.
