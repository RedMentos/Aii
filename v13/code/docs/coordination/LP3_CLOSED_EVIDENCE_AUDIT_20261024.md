# V13 WP-LP3 independent closed-evidence audit — 2026-10-24

**Owner:** GPT/Codex, new isolated `scripts/lp3_closed_evidence_audit.py` and `tests/test_lp3_closed_evidence_audit.py`. Parent PR #44 `3834d062a7ea9ba25bc1240e1407317d80587fc9`; no changes to the PR #44 runner, production runtime, Claude-owned packages, Canon, preregistration or any existing evidence. No heavy native job started.

## Finding

PR #44 fixed preflight asset/fixture binding. Its existing `audit_rows` checks the reported aggregates against the reported predictions, but cannot detect a consistent rewrite of `seed-31.json` and `report.json`, and does not authenticate the set of seed files against an independent external digest. It also does not independently check the original source-fixture expected-answer order. **No native LP3 evidence exists yet**, so this is a pre-execution proof-integrity improvement, not an accusation of a forged result.

## New isolated read-only verifier

- Validates the registered four seeds, five arms, 48 held-out answers, 13 near misses, pinned HF weight/revision, fixed protocol, zero-intervention abstention, nonfinite losses, source/fixture hashes when supplied, and unmodified STEP2/B3/phone flags.
- Checks the original 32 paired LP2 paraphrases followed by 16 HARDER prompts. With `--source`, `--lp2`, `--lora`, parses literal fixture definitions without executing source modules, then compares the exact expected answer order against the actual fixture values. Local hash consistency does **not** independently authenticate GitHub/upstream provenance.
- Requires byte-equivalence between every seed file and its embedded report row; independently recomputes counts and the original fixed LP3 verdict. Rejects missing seeds, failed markers, duplicate JSON keys, symlinked evidence files, extra/out-of-bank answers, zero-arm leaks, and forged verdicts.
- Can create a deterministic SHA256 receipt **outside** the attempt directory (`--make-receipt`). To check that receipt later, pass both `--receipt` and `--receipt-sha256` from an independently persisted trusted Git blob or equivalent record. A caller-supplied hash alone is **not** proof that it was independently published; a coordinated attacker can still rewrite both the evidence and a mutable anchor.
- Reports `UNANCHORED_STRUCTURAL_ONLY` without a receipt and `RECEIPT_SHA_MATCHES_SUPPLIED_ANCHOR` with one. Neither is a model-quality, native-reproduction, Redmi or JEPA PASS.

Example after a native cohort is **closed** (do not alter original run):

```bash
python scripts/lp3_closed_evidence_audit.py --run /path/to/closed-attempt \
  --source scripts/lp3_memory_key_candidate.py \
  --lp2 scripts/lp2_assignment_objective.py --lora scripts/lora_bench.py \
  --make-receipt /separate/immutable-location/lp3-receipt.json
# Publish the printed receipt SHA to an independently verified remote commit.
python scripts/lp3_closed_evidence_audit.py --run /path/to/closed-attempt \
  --source scripts/lp3_memory_key_candidate.py \
  --lp2 scripts/lp2_assignment_objective.py --lora scripts/lora_bench.py \
  --receipt /separate/immutable-location/lp3-receipt.json \
  --receipt-sha256 <previously-published-sha256>
```

## Verification and limits

- 32/32 focused Python software tests PASS: 17 inherited PR #43/#44 tests plus 15 new adversarial audit tests. `compileall` PASS. First new test run had 1 **test-fixture reference aliasing** failure; fixed via `deepcopy`, preserved in this handoff. No native model/Redmi execution.
- Full repository suite and `public_repo_privacy_scan.py` **NOT RUN**: container has candidate delta ZIPs but no full Git checkout, and outbound `git ls-remote` fails DNS. The GitHub connector was used to inspect remote PR heads, current handoff/AGENTS/ROADMAP/user decisions and candidate files.
- Current 4 GiB cgroup; pinned seven-file HF master absent here. This does not establish the state of another native host. No overlapping heavy jobs started.
- This package is a new independent auditor; it does not change or retroactively repair historical evidence. Existing negative results remain: STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, LP1 `NO_ATTRIBUTABLE_GAIN`, LP2 `ALIGNS_NO_GAIN`, `jepa_weight=0`, Body-JEPA `UNAVAILABLE`, canonical/full scope incomplete.

## Next

1. Independent full checkout review, full regression and public privacy scanner on the integrated candidate; resolve any findings without rewriting old evidence.
2. Verify pinned model/tokenizer/config/license bytes and exclusive native job ownership on the actual native host; only then run the registered four-seed LP3 memory-key cohort serially.
3. Audit and externally anchor immutable raw evidence. Even if LP3 memory-key control passes, separately preregister an equal-budget **generated-answer** JEPA consumer comparison before runtime integration or any gate promotion.

**USER_DECISION_REQUIRED:** none. **Drive:** previously rejected anyone-writable folder was not retried.