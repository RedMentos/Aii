# C3 German one-line format intervention — preregistered paired native pilot

UTC 2026-10-29. Review-only child of PR #1138 at `74d95a54bd1c2bbd3c6ccfc1c52db1b42b1342ef`. Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. Previous Project Lumen native heldout scored EN 3/3, DE 0/3 under a strict oracle. This is a **new, unseen** German-only paired prompt-format experiment, not a retrospective rescore and not model training.

## Fixed new cohort and arms

Use fictional **Projekt Solis**, unseen budgets **180 Euro** (source-present) and **65 Euro** (latest revision of earlier 180). Three conditions: present, absent, revised. For each, two arms: BASE (the earlier German style asking `Nenne Betrag und Waehrung`) and FORMAT (same verified fact/absence/revision but explicit one-line output constraint `<Zahl> Euro` for present/revised or exactly `UNBEKANNT` for absent, no other fields/numbers). **Do not insert the expected literal numeric answer in the FORMAT instruction**; the number may appear only in the source note. Fixed order: `de_base_present`, `de_format_present`, `de_base_absent`, `de_format_absent`, `de_base_revised`, `de_format_revised`. Each arm runs in an independent fresh llama-cli subprocess; no conversational memory.

Reuse exact official current C3 GGUF SHA256 `3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d`, revision `657e078c94084481950a2d555a941481f715536b`, LFM Open License 1.0; llama.cpp b10964 tar SHA256 `9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443`. Temperature0, 48 max generated tokens, context512, 2 threads. No model/seed/source/cohort pin rewrite.

## Frozen extraction and scoring

Reuse the already source-pinned **exact generated-only** CLI parser from PR #1138: one literal exact prompt echo, one complete timing footer, nonempty generated text; reject prompt echo, malformed/truncated/duplicate delimiters, invalid UTF-8, nonzero native exit and capped output. Fixed per-case strict oracle: present iff only numeric token 180 and euro/euros present; revised iff only numeric token 65 and euro/euros present, with no old 180; absent iff normalized generated-only output exactly `UNBEKANNT` (terminal punctuation allowed). Any extra number, unsupported field with a number, or wrong abstention fails. Keep all six raw outputs and each row's 0/1.

Report `base_correct/3`, `format_correct/3`, `paired_gain=format_correct-base_correct`, six-case `n_scored`, and all failures. No claim of statistically significant improvement from three pairs; do not change production `prompts.py` or German default on this pilot alone. Even if FORMAT wins, utility_proven remains false and STEP2/B3/Body-JEPA/LP3/Redmi/V13 gates unchanged. No JEF/C2, B1/B2, memory consumer or tool action.

## Evidence

Tests must freeze IDs, order, new project/budgets, forbid answer literals in format instructions, verify exact parser/oracle controls, and keep negative gates. Native CI must verify official model/runner SHA256, execute six bounded rows, preserve original failures, close raw with SHA256SUMS and private backup byte-exact. A native/parse failure remains incomplete, never silently excluded. Original Project Lumen heldout and original Aurora pilot remain immutable.

Owned files: `v13/code/scripts/current_c3_native_german_format_pair_20261029.py`, `v13/code/tests/test_current_c3_native_german_format_pair_20261029.py`, `.github/workflows/v13-current-c3-german-format-pair-20261029.yml`, this prereg, dedicated BUILD_STATE.
