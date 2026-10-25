# Run350 second independent review amendment — escaped literals and Run198 historical baseline

Run199 workflow `40225225365` at `64d5ea926431da63ae29176e518718c73fe4aa0f` exposed two additional consequences after productionizing the previously SHADOW-only Run198 inline guard:

1. The old Run198 `test_existing_v1_loses_unclosed_late_inline_code` expects the *live* implementation to retain the old bug. Preserve that negative test by running its exact historical assertion against the same frozen test-only `legacy_compress_run199` algorithm, without deleting/weakening it or altering registered model/cohort/seed hashes.
2. `test_escaped_backtick_does_not_force_raw` shows the initial conservative production guard over-rejects a backslash-escaped backtick that is not a Markdown delimiter. Refine the source-only guard to ignore delimiters preceded by an **odd** run of backslashes (even run means unescaped), preserving Run198's prior candidate behavior. Keep unmatched real delimiters RAW.

Owner scope extended only to `v13/code/tests/test_context_inline_guard_run198.py`. Add Run198/Run199 to exact-head Run350 CI and rerun both independent workflows. Keep all failed CI and raw RED evidence. No native/Redmi/ContextOS ACTIVE or acceptance-gate promotion.
