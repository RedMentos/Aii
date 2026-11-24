# Approved exact answers in the existing C5/F6 path

The fixed policy helper adds bounded, source-bound operator answers to the existing versioned rule generations. It adds no model or APK. Existing free-text `:rules add ...` entries retain their existing prompt-guidance semantics; they do not become guaranteed semantic rules.

In the local operator UI:

```text
:rules fixed "Wie lautet unsere feste Antwort?" "Genau dieser freigegebene Text."
:requests
:approve req_<the exact returned request ID>
```

The first command creates a pending rule diff, including a readable `fixed_preview` with the exact query and answer. It does not activate the answer. The approval command commits the individual reviewed rule generation. The query is matched as the entire input string, including case, spaces and Unicode composition; aliases, paraphrases and substring matches are not inferred. `:rules remove <Index> [more indices]` creates the corresponding reviewed removal diff. Indices refer to the list shown before removal, start at zero and must be distinct and present. For example, `:rules remove 2 1` proposes removing entries 1 and 2 together; it leaves all other entries unchanged and needs approval. This allows explicit recovery when several active policy sources are corrupted and removing just one would still leave an invalid policy. To replace an answer from the operator UI, approve its removal, then create and approve the new entry. The Store also supports atomic replacement through a complete reviewed diff; no separate UI edit command is provided in this scope.

Queries are limited to 4,096 UTF-8 bytes and answers to 16,384 UTF-8 bytes. At most 32 fixed entries can be active. Terminal controls, bidi overrides, malformed UTF-8 and wholly invisible text are rejected. Ordinary RTL text, newlines, tabs and emoji using ZWJ remain supported. Duplicate exact queries or IDs, conflicting answers for one exact query, unknown typed structures, non-operator authority, partial SourceRefs, stale diffs and unreadable/tampered/revoked sources are rejected.

`v13.output_policy.match(store, text)` atomically reads the current rule generation and revalidates every active typed policy's full source and hash. On a valid match it returns the exact answer plus rule/version/source bindings and `model_generated=false`. An invalid active fixed entry raises `InvalidRule`; callers must fail closed and expose an honest diagnostic instead of silently sending the input to a native model. An explicit operator removal remains available to repair an invalid active entry.

The root Runtime consumes this helper in its existing direct report branch, before memory/routing/observer/model work. Tests for that Runtime wiring are separate from the helper's unit proof. Source-only rule output must not be reported as model intelligence or as a successful neural rule-verification experiment. The policy does not establish whole-answer semantic enforcement on native outputs, a learned rule checker, general intent/paraphrase recognition, future Age authority or external tool permission.

Operator-owned immutable source kinds are `HUMAN_FIXED_RULE_QUERY` and `HUMAN_FIXED_RULE_ANSWER`. The existing rule/generation tables remain authoritative; no new schema migration is needed. Weight rollback preserves the latest approved rules. Telemetry keeps opaque rule IDs, version IDs, source hashes, policy enums and numeric counts; exact query/answer text remains in the provenance store and reviewable rule request, not diagnostic telemetry.

Native history also checks every stored dependency of those two source kinds against the exact SourceRefs in currently approved, valid fixed entries. Removing or replacing an entry excludes both its direct historical answer and later answers whose recorded native context inherited those references. Equal answer bytes under a new source ID do not preserve the old approval. Adding unrelated guidance or another fixed entry preserves history backed by an unchanged approved entry. Chat display remains available; no transcript is deleted. This uses the existing durable source lineage, without new inherited authority labels or learning from revoked responses.

Validation on 2026-10-07:

- `docs/proofs/output-policy-unit-20261007.log`: 14 passing real Store/operator tests covering approval, UTF-8 equality, restart, replacement/removal, model rollback, stale approval, source tampering/revocation, explicit recovery of multiple corrupted policies, conflicts, malformed authority/schema, limits and telemetry privacy.
- `docs/proofs/output-policy-core-regression-20261007.log`: 26 existing Core/Runtime checks pass.
- `docs/proofs/output-policy-unit-initial-20261007.log` preserves three initial test-fixture errors; they were corrected without changing enforcement gates. These tests do not run model inference or assert neural rule quality.
- `docs/proofs/fixed-policy-history-regression-final-20261007.log`: 57 tests pass, including eight new real Store/coordinator transport tests for direct and transitive removal, replacement with equal content under new source IDs, unchanged active entries after unrelated rule changes, active source tampering, finite public telemetry codes and scoped ledger facts. Transport fixtures are explicitly not native model inference.

Runtime integration and measured scope:

- Approved exact matches bypass native A3, learned semantic retrieval, C2, B observers (including background), C3 decode and native world prediction. Typed C1/broadcast, action/corollary/outcome, exact source lineage, durable queue completion and timing observations remain real. No generated output is relabelled as model intelligence.
- An invalid active policy causes a visible source-system diagnostic, including for an unrelated query. Removing or superseding its rule version excludes its old answers from future native history while preserving visible chat.
- Native display removes C0/C1 controls, surrogates and bidi overrides, counts removed characters and accepts multilingual visible text. A wholly invisible native stream becomes a labelled system diagnostic with model_generated=false. This does not judge semantic correctness.
- 7 real coordinator integration tests pass (`docs/proofs/output-policy-runtime-unit-20261007.log`). Mocked native seams only verify transport guards and absence of calls; they are not native model quality proofs.
- 32 actual fixed-policy coordinator turns and a restart pass (`docs/proofs/fixed-policy-runtime-latency-20261007.json`): Linux median 0.006130s, p95 0.008791s. No native model or KV cache ran. Rerun `python3 scripts/benchmark_fixed_policy.py --out fixed-latency.json` on target device; these are not Redmi measurements.

Native tap HTTP reads now use the remaining bounded tap/job deadline rather than the ordinary three-second control/health timeout. Cancellation and the existing watcher retain authority. The actual delayed local-HTTP test proves timeout handling only; native mobile prefill must still be measured.
