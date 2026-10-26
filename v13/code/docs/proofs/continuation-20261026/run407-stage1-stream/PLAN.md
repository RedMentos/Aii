# Run407 — bounded streaming SHA/CRC audit and atomic stage1 restore (2026-10-26)

Owner: GPT scheduled continuation. Base: Run406/PR401 `a9482aa1c408a3680a47aa5e8d6c0fd7028e7083`, stacked review, not main. Files owned: new `run407_stream_stage1.py`, `test_run407_stream_stage1.py`, `run407-stage1-stream/**` and own workflow only. Frozen Run394/Run397/Run402/Run404 files untouched.

Observed Run401 SUCCESS, artifact 12620379581 SHA256 `65ac00a8cd2013ebab76828ed3bc25dee5433d1d55a995573387f19de29b530a`, compressed size 1,461,613,972. Run402's 90MB in-memory cap cannot accept this. Run406 is independently inventorying exact actual ZIP; adjust hard bounds only after its observed report.

Implement bounded streaming verification of all ZIP members (SHA256 manifest, Zip CRC, no traversal/links/duplicates/model-weight filenames, size caps), extract the original complete `run401-full` tree into fresh private staging only, invoke unchanged Run402 native report/receipt validator, atomically rename after verification, retain original ZIP and raw failures. Never start inference, never claim Redmi or whole-system completion. Include adversarial synthetic tests; run real archive only after Run406 inventory confirms bounds. A failure is RED and preserves original ZIP; no automatic gate promotion.

Acceptance: focused source tests and compile/privacy exact-head PASS; independent actual Run401 ZIP streaming SHA/CRC/receipt verification with no native inference; real native stage2 remains a separately authorized serial job. All STEP2/B3/Body-JEPA/jepa_weight/Age/Redmi/V13 negative gates unchanged.
