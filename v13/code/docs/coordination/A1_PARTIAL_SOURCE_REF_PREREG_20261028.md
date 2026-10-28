# A1 / B1-B2 partial SourceRef segmentation — preregistration, 2026-10-28

Independent branch from verified PR #806 `5aa5888e32c158aab67ed5d8d1b9f6b19c1b70eb`; separate owner from F5/AG8/HX1/HX3 integration PR #809. Only `v13/code/v13/cognition.py:segments`, `v13/code/v13/episodes.py:text_segments`, a new test and workflow are in scope. No Canon/model/seed/registered cohort changes.

## Source-inspected bug hypothesis

`cognition.segments(text, ref, width, 'fixed')` constructs child SourceRefs with `char_start=i`, `char_end=i+width` rather than `ref['char_start']+i`. `episodes.text_segments(text,ref,...)` similarly emits `char_start=s`, `char_end=e`. This is correct only for full-source refs whose base is zero. If a caller passes a validated excerpt with a nonzero `char_start`, its child segments point to unrelated source characters despite containing the correct displayed text. This risks corrupting exact provenance for future A1/B1/B2 partial-view composition; current known full-event call sites use base zero, so **do not claim an observed live failure**.

## Registered test before edit

- Create a real Runtime/SQLite source with a non-ASCII prefix and suffix and a validated nonzero-offset excerpt SourceRef. For fixed and event segmentation, assert lossless text tiling, exact contiguous child SourceRefs covering **only the excerpt**, and `Store.read_source(child_ref)==child['text']`.
- Verify the original base-zero full-source case still matches exact Store bytes, including multi-byte Unicode, and source SHA256/id/modality are preserved.
- Test-only RED on the unchanged parent source; preserve raw failure ZIP. Narrow production change: add the input ref's char_start to the emitted child spans, no new authority, no source rewrite, no tokenizer modification. Run focused and full Linux software tests with hashes/privacy/diff evidence.
- Keep A1/B1/B2/STEP2 and native claims separate: this proves a SourceRef offset invariant in software, not gist complementarity, B3 L1, native C3 consumption, Body-JEPA or Redmi.

Original STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0/RECORD_ONLY unchanged. Owner: GPT-6 isolated A1/B1/B2 provenance package; next command after test commit: branch-scoped GitHub Actions focused RED and raw inspection before source edit.
