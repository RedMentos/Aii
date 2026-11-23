# Context OS exact-span: single-quoted literal safety — preregistration

UTC 2026-10-29. Review-only child of #1132 at `f4f537c398c0a47b8595ca9c9a0b24b2ca7eb2ba`. Canon `218464b12a2d27d92524c751922fa8e1c3fb0ea7` unchanged. No live activation, no source mutation, no age/gate promotion.

## Concrete source-loss counterexample

`context_os.compress` protects double-quoted and German `„…“` literals but not English single-quoted spans. A long earlier turn with an exact later sentence such as `'magenta sparrow'` may compress to its first sentence and silently drop the exact literal. This violates Context OS §8.4 exact-span preservation. Existing source refs remain in Store, but the model's compressed view may lose a user-specified literal without an exact-need trigger.

## Registered controls

1. Balanced, delimiter-style English single quotes after the first sentence must be preserved verbatim in `exact_spans` and any accepted `compress` output; otherwise keep RAW.
2. Quoted contractions such as `'don't forget'` must be preserved, without confusing apostrophes inside words with delimiters.
3. A single unmatched delimiter quote, or an overlong/ambiguous single-quoted literal, must force RAW rather than silently truncate.
4. Ordinary contractions/possessives (`don't`, `John's`) must not become fabricated quoted spans or needlessly block safe compression.
5. Existing double/German quote, URL, numeric, code, cache layout, warm source and Age0 SHADOW controls remain unchanged. No original source or registered test cohort modification.

## Minimal candidate and proof

Extend `QUOTE` exact-span matching for bounded single-quoted text, and add a delimiter-coverage fail-closed guard that ignores intra-word apostrophes but rejects unmatched/ambiguous quote markers. No change to model prompts, context authority or compression policy knobs. Add a new deterministic test module, run original RED then corrected GREEN on source-pinned Linux CI, preserve raw exits, SHA256SUMS, privacy/diff checks and private backup. Full native/Redmi quality not claimed.

Owned files: `v13/code/v13/context_os.py` (minimal literal handling), `v13/code/tests/test_context_os_singlequote_exact_20261029.py`, new CI workflow, dedicated BUILD_STATE. All other organs remain binding.