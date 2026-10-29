# C3 native heldout bilingual source-grounded oracle — preregistration

UTC 2026-10-29. Review-only child of PR #1136 at `eaa86721edf634e3325d045905f94443cbb7c795`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. The prior six-case C3 native pilot has already been inspected and is **not** preregistered semantic evidence. This is a distinct, unseen fixed heldout cohort with new fictional project and budgets, fixed **before any native output**.

## Pinned artifacts and execution

Use unchanged official current-catalog C3 `LiquidAI/LFM2.5-350M-GGUF` revision `657e078c94084481950a2d555a941481f715536b`, model SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, 219312832 bytes, LFM Open License 1.0; llama.cpp b10964 runner tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`, 16825086 bytes. No model or source pin changes. Six fresh independent `llama-cli --single-turn` calls, temperature0, max48 generated tokens, context512, 2 CPU threads, bounded raw stdout/stderr, per-row fsynced progress, fresh scratch, exact SHA256 verification.

## New fixed heldout prompts

Use fictional **Project Lumen / Projekt Lumen**, not Aurora. In both EN and DE, in this exact order: (1) verified source gives budget **160 euros**; ask for amount/currency, (2) no verified budget source; explicitly request **UNKNOWN** (EN) / **UNBEKANNT** (DE), (3) earlier budget 160 but latest verified correction is **75 euros**; ask current amount/currency. Six IDs: `en_present`, `en_absent`, `en_revised`, `de_present`, `de_absent`, `de_revised`. No unsupported numeric value appears in absent prompts. The exact strings and SHA256 in the committed source are the binding cohort; never edit after first native output.

## Fixed generated-only parser and oracle

The pinned CLI observed in the **earlier** pilot emits a unique literal `\n\n> <exact prompt>\n` followed by generated text and then `\n\n[ Prompt: <speed> t/s | Generation: <speed> t/s ]`. The parser must require exactly one prompt delimiter, exactly one generation timing delimiter, a complete bounded native row, and nonempty generated text. Extract **only bytes between** the exact prompt and timing delimiter; never score echoed prompts, CLI banner, stderr or timing metadata. Fail closed to `UNSCORABLE` on missing/duplicate/malformed delimiters, decoding errors, truncation, nonzero exit, or an echoed full prompt.

For present cases, pass iff the generated-only answer contains exactly the integer **160** and currency `euro/euros`, no other decimal/integer tokens, and no UNKNOWN/UNBEKANNT. For revised cases, pass iff exactly **75** with euro/euros, no old 160, no other numeric tokens and no UNKNOWN/UNBEKANNT. For absent cases, pass iff the normalized generated-only answer is exactly `UNKNOWN` or `UNBEKANNT` (allow only terminal whitespace/punctuation), contains no digits, and no extra answer text. Use Unicode casefold and ASCII-digit token boundaries. Each row is scored 0/1; a failed/unscorable row remains zero in the fixed six-row denominator and its raw is retained. `n_scored`, `n_correct`, `n_unscorable`, `correct_fraction` are **C3-only diagnostic** metrics. Even 6/6 does not promote STEP2, B3, Body-JEPA, LP3, jepa_weight, native end-to-end, Redmi or whole-system utility.

## Verification and persistence

Software tests must prove parser excludes prompt echoes, rejects duplicate/truncated markers and nonfinite/malformed rows, rejects extra numbers, accepts fixed valid controls, and maintains the six frozen cohort IDs. CI must preserve original raw and closed report, SHA256SUMS, official model/runner hashes, and all failures. Private Library backup with byte-exact readback. Native execution is Linux-only; no B1/B2/JEF/C2, memory consumer, tool action or user data. All original negative gates remain.

Owned files: `v13/code/scripts/current_c3_native_bilingual_heldout_20261029.py`, `v13/code/tests/test_current_c3_native_bilingual_heldout_20261029.py`, `.github/workflows/v13-current-c3-bilingual-heldout-20261029.yml`, this prereg and dedicated BUILD_STATE. Original six-case pilot and its raw remain unchanged.
