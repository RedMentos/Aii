# P2X schema ON/OFF training16 handoff — 2026-10-29

## Exact lineage and ownership
- Base: PR #1105 head `9e22b688c124ed2435d191d81e7a8bb512c127af`; child PR #1106, review-only. Production main unchanged.
- Prereg commit: `cbd8d4865fa064ba2f651033b40b41c2a5b9c845`, before script/tests/workflows. No frozen cohort, seed, model, runtime or adapter edits.
- Branch owns only `docs/coordination/P2X_SCHEMA_TOGGLE_TRAIN16_PREREG_20261029.md`, `scripts/p2x_schema_toggle_train16.py`, `tests/test_p2x_schema_toggle_train16_20261029.py`, and two dedicated workflows, plus this handoff.
- Source blob SHA: `457aa932ffe3235034ef51da84b9ac9015d5ddb8`; test blob SHA: `172ce69b45e202dd92d2fe20777c0d2632c10341`. These are Git object IDs, not SHA256 of model assets.

## Experiment and proof limits
- Same pinned JSON-target LoRA adapter SHA256 `7a9e04377607045e86ce8d45260caa762648745260ffacad853626353c408ca6`; same QAD C3 model, llama.cpp b10964 runtime, same 16 frozen original training examples (4 each A/B/NONE/UNKNOWN).
- Two serial arms: `on` sends the original `json_schema` in completion request, `off` removes that key only. Exactly 32 planned native calls. Compare strict JSON output and separately count bare-label unparseable text. Raw request payload included for independent one-factor check.
- Neither arm uses heldout/CAL36 rows, updates weights, or receives authority. No generalization or STEP2 utility claim is permitted.
- Source-only CI run `40897675368` at `620fc23d95b520f38ac33afe06102214cdb4ccf8` launched; native CI run `40897914652` at `e76a41f8f98a3da08b5644a785a3d44e9f965f6b` launched. **Outcomes not yet reviewed** at initial handoff. Never call these GREEN before reading exit files and exact-head artifacts.

## Next exact commands
1. Read both Actions runs and all stage exit codes. For source: `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_p2x_schema_toggle_train16_20261029 tests.test_p2x_json_train16_eval_20261029`; full `python -m unittest discover -s tests`; privacy scan `python v13/code/scripts/public_repo_privacy_scan.py --base 9e22b688c124ed2435d191d81e7a8bb512c127af --head HEAD --no-worktree`.
2. For native, use exact workflow artifact, verify SHA256SUMS and `python -m scripts.p2x_schema_toggle_train16 --verify <evidence>` against the pinned exact-head source. Preserve failed rows and any RED exit, independent review before model-quality claim.
3. If schema OFF remains constant NONE, investigate first-token logits, adapter application and training signal as new separately preregistered candidates. If OFF changes actions, verify parsing and whether labels are actually correct; never promote heldout or production gates.
4. After each verified result update this handoff and PR, continue the next independent canonical package. No Redmi available in this cloud run; no paid provisioning or Drive retry.

## Negative gates
Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; AG6 not approved; Redmi not measured; canonical_architecture_complete=false; user_full_scope_complete=false.

## Native closure (2026-10-29, exact source head `e76a41f8f98a3da08b5644a785a3d44e9f965f6b`)
- GitHub Actions run `40897914652`: **SUCCESS for execution/replay, not model quality**. Original artifact `12908680190` ZIP SHA256 `941ae87d591f06fa46c6c2b64f4b84198bdebcbd3a056d8e9e0a1bea4523b013`; ZIP CRC clean, 46/46 internal SHA256SUMS, 18/18 stage exits 0, 32/32 pinned FINAL native calls, two serial servers reaped. Independent stdlib replay checked source/adapter/model/runtime hashes, all row identities, 16 exact prompt/request pairs and only the schema-key difference.
- **Measured result:** schema ON: all 16 `{"action":"NONE"}`; strict correct 4/16 (only NONE), A/B/UNKNOWN 0/4. Schema OFF: 16/16 outputs **not valid JSON**, strict correct 0/16. 12/16 exact bare `NONE`; remaining 4 outputs `Option B`, `B1`, `B1`, `B1 is the correct choice.` (none equal a valid required action). This shows a **format/decoding effect**, but does not establish why NONE dominates or prove semantic learning. Off outputs are not promoted as correct actions.
- Private Library backup: `/V13-Checkpoints/2026-10-29/P2X_SCHEMA_TOGGLE_NATIVE_RAW_40897914652_SHA941ae87d.zip` re-materialized and byte-compared SHA256 equal to original; independent audit JSON saved alongside as `P2X_SCHEMA_TOGGLE_INDEPENDENT_AUDIT_40897914652.json`. GitHub raw artifact retention is 30 days; private backup is separate.
- Source-only full CI `40897675368` remains pending at this update; do not claim full GREEN yet. Next substantive candidate: independently preregister first-token/action-token probability or adapter scale ablation on the *same training-only examples* to determine whether the model learned any label-specific signal. Avoid tuning heldout/CAL36. All original negative gates unchanged.
