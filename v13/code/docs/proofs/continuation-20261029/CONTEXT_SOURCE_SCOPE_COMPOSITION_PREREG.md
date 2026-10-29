# V13 Context OS pair + project source-scoping composition — prereg (2026-10-29)

Owner: GPT-6 integration review, separate branch based on exact Run141 PR #1042 `130f8424f4cc993e4287c7cfb94c4e58e551ac07`. This is a **planned conditional package**, not an accepted integration. The source/test donor PRs #1043 (pair scope, head `eaf32168e32a5ca0870ea547534d6789eda06c16`) and #1044 (project scope, head `90c34a609cfabc14cba460700f2501243b6d0872`) require exact-head CI GREEN and independent raw audit before import. Do not edit their branches or original Run141 source.

## Problem

Pair-scope guard alone does not prevent cross-project history leakage. Project-scope guard alone does not prevent unscoped typed values shared by A and B. They must be composed before any claim of safe Context OS fallback, with exact authenticated source/history as an upstream prerequisite. Neither changes Age0 authority or proves two-body learning.

## Predeclared method and checks

Import **exact** donor source/tests (no reimplementation or cherry-pick of unrelated files) into this separate branch after donor acceptance. Add default-off `context_option_safe_scope_candidate.py` that first enforces unique leading project identity and filters foreign/ambiguous/unheaded earlier sources, then applies pair-clause refusal to selected current/history. Test valid same-project multi-turn, foreign-only history, interleaved foreign sources, current typed shared pair, older shared pair, conflicting project names, partial current updates, and original frozen six-fixture full-history replay with unchanged values and 0 wrong committed. Original six fixtures are **post-observation full-history upper bound**, not B2-limited/native held-out proof. Source, tool, model, seed, fixture hashes immutable. Strict source blobs, focused/full/privacy, raw ZIP CRC + SHA256SUMS and independent review; preserve all RED attempts.

## Gates and claim limits

Default OFF; no runtime, AgeControl, model weights, native/Redmi calls or main merge. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 FAIL, Body-JEPA UNAVAILABLE, LP3 FAIL, jepa_weight=0, V13 INCOMPLETE. Parent Run141 original exact source remains unchanged.

Next command: independently audit exact-head CI artifacts of PRs #1043 and #1044; if GREEN, import donor blobs into this branch and run composition tests. If RED, preserve raw, fix donor in its own branch first and update this prereg handoff with exact replacement SHA (do not silently claim original donors GREEN).
