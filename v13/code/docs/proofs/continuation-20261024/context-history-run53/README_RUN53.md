# Run53 — Context OS native_history source-lineage and complete-pair candidate

Preregistered FIRST at `9a5cc374eede13e1d9757869def4201e7591fa3d` from Run52 `30bca0576eec9d0bfb2feb17a1c648accc380b7c`. Only this folder owned. No production/Canon/Run36/45/49/native weights modified.

**Exact production `v13/code/v13/history.py` Git blob `05455f297205b40fe8e0f818c4657f1fedcd9fa3` was copied byte-for-byte and EXECUTED locally** with SQLite Store-shaped fixture and stub `common/inputs/output_policy` modules. Production Store schema independently checked against Git blob `0779d986fb8aee8aa01c5df5f656889d4bd56348`.

Found source-level failures: duplicate user, duplicate assistant and reversed pair accepted; event/session mismatch and truncated 3-message event accepted; after first patch, tampered user message text and user metadata SourceRef accepted despite a valid event source. All reproduced in synthetic SQLite with raw RED logs. **No real-runtime exploit claim.**

`history_run53.patch` is readable, verified Git blob `4163c6c92543082e382b4bb35f884c1edc4435fb`, and applies only to exact original history.py. It requires exactly one ordered FINAL user+assistant pair, checks full SQLite event message count beyond bounded history, event/session ownership, and exact user text/metadata SourceRef against verified event SourceRef. Existing fixed-answer approval and terminal-log exclusion preserved.

Original **13/16 PASS, 3 FAIL**; extended **13/18 PASS, 5 FAIL**; additional lineage review **18/20 PASS, 2 FAIL**; final **21/21 PASS**, optimized Python **21/21 PASS**, compileall PASS. Closed original source, patched source, fixture stubs, tests and all raw logs in `run53-code-raw.part1.txt`…`part3.txt`. Concatenate without separators, base64-decode, Brotli-decompress and untar in disposable directory. Decoded tar.br SHA256 `7e3b125c9cbe8e44fe3f20650a1d9e913e15d183b32dfc7ac7e2c8f7fcabe885`; all parts re-read and verified by Git blob.

No actual Store.blob_bytes, full output-policy rules or live concurrent source-revocation proof. Full checkout, original suite, official privacy scan and Redmi/native model tests pending. STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE unchanged.

Next: in full current checkout, `git apply --check history_run53.patch`, independent review, real Store native_history regression, source revocation and full suite before production integration.