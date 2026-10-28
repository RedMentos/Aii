# Run11 paired bilingual native evidence audit prereg — 2026-10-28

Owner: GPT-6, review-only child of #855 at `5239ca62ea359d752eff2602f7462e6c6c0833dc`. No source/model/fixture/scorer/prompt/seed edits. Separate artifact-audit package, no heavy native job.

**Frozen paired inputs before implementation:**
- Candidate native Actions `40637244491`, source `1cd099d0aa856dbca3205460affa613bd3780813`, artifact `12794815033`, ZIP SHA256 `b64235b1adf9d1cf90139123790c887b4308d7ea6538aafc99fceab690fbc173`.
- Baseline native Actions `40637658538`, source `f7eb46206bf2f80fe6c81008095d376021a34920`, artifact `12794187079`, ZIP SHA256 `2efe9bd177f8366626873da452041bd15ffcdc71ee96eb9567fed6d93fdf42ce`.
- Frozen 16-item corpus Git blob `ceda0a5cb506cf09885652b24893cf7d8fdff63b`; frozen scorer `0348b17dedc0e4142a73a8ad8c93a57a2c7d6491`; collector `a0a94ce08983b0621990c5b9c2f4712463e146bb`.
- Candidate prompt `646c6f31b52ca2664c1952af7c7e842fc3e20885`; baseline prompt `a74d7517a7ab70e801e177b58da057e57fd3460c`; catalog `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`.

**Predeclared integrity checks:** SHA256 ZIP, CRC, every internal SHA256SUMS entry, all eight stage exit codes, HEAD/source/prompt/catalog/fixture, raw 16 ordered IDs, raw answer SHA256, row/manifest equality for prompt/answer/status/role/model, per-row error absent, tool call absent, Age0 RECORD_ONLY/jepa_weight0, CAPTURE_RESULT raw+manifest SHA256, original SCORE per-item/aggregate recomputation via frozen scorer. Paired route-change list must be independently computed. Reject all mismatches; no overwrite of outputs.

**Primary quality readouts:** frozen lexical numeric match out of 12 and unsupported uncertainty-marker out of 4; paired per-item wins/losses and route changes. Human review of unsupported-note abstention and arithmetic contradictions is explicitly *separate posthoc interpretation*, not a new frozen gate or a semantic reliability proof. Preserve all failures and missing claims. Record nonmatching language variants as scorer coverage limits, never silently alter the frozen scorer.

**Expected result (observed before prereg, not hidden):** candidate 12/12 numeric and 1/4 unsupported markers; baseline 10/12 and 1/4. Candidate two numeric gains, no numeric losses; all 16 final per workflow. These are known observations, so this audit is integrity/reproducibility, not a blinded discovery or causal inference.

Acceptance: standalone stdlib audit script + negative tamper tests; focused and full Linux software CI; aggregate-only GitHub report; original native ZIPs kept unchanged and privately backed up only to a permitted private location. All gates remain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, LP3 heldout FAIL, jepa_weight0, Age0 RECORD_ONLY; no Redmi/whole-system claim.
