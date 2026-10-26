# Run620 — persistent operator-only model answer language

2026-10-26. Review-only child of Run619 PR614 at `18a749dc6ad210ca39ef2a56eb4c618354dbb1bd`. User English-first decision already implemented in `prompts.py` and `config.py`; this adds **only** a local explicit operator control `:language [status|en|de]` with help in `:help` and scrollable `:befehle`. English remains the default. German is an existing prompt template, **not learned language transfer**.

`:language de` / `:language en` require idle under Runtime's lock, atomically persist validated `answer_language`, update in-memory config and log `answer_language_change`. Status is read-only; same-language set is idempotent; invalid args, non-local origin and busy turns refuse without mutation. Existing prompt templates, model weights, approvals, Age and learning modes unchanged. A new answer picks the chosen prompt language only after idle change; no active answer is switched.

## Executed evidence

Source-identical new test blob `8e5a187a82db318997ff4619ac7665453375b91c` over original Run601 phone ZIP (head `fdcbefc129b28b085fcfa84a4bc3ee44cce74b62`) with the same operator patch applied to that older operator: **5/5 actual SQLite Runtime tests PASS** (default EN, status no mutation, DE switch/restart/EN revert, telemetry, invalid/nonlocal refusal, busy refusal, idempotence). Raw SHA256 `cd359ab694fb7c21995018bec6d93537c0bd8b1e9eb4bb15c3e3f433ba588457`. Combined existing `tests.test_prompts`: **10/10 PASS**, raw SHA256 `581c98f44ce119c8db07bc103683d308d8059c49a3a9f39a6b3bd7940cb6116a`. Python compilation PASS. **This is a local Linux Run601-base overlay, not an exact-current-head checkout nor native/Redmi execution.**

Remote source `v13/code/v13/operator.py` Git blob `7ba517f8f9853983ac2b61bb8dfb1dfa9587c38b`; new test `8e5a187a82db318997ff4619ac7665453375b91c`; unchanged prompt catalog `a74d7517a7ab70e801e177b58da057e57fd3460c`; unchanged config `9bbc5b6e1bc35b7d0b9be4fb925100bce97fd0cd`. New CI `.github/workflows/run620-language-operator.yml` verifies exact blobs, original Canon, actual SQLite tests, privacy, raw exits and hashes; **GitHub Actions push run status UNVERIFIED** until accessible.

No whole-system, Body-JEPA, C3 language-learning or native quality claim. Negative gates STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; Redmi UNMEASURED; V13 INCOMPLETE. No main integration, independent review requested.

Next: verify GitHub Actions exact head and artifact; independently review whether prompt selection remains source-bound in current runtime; proceed to the next substantive Canon learning/utility package. Do not edit concurrent Run618 native owner.
