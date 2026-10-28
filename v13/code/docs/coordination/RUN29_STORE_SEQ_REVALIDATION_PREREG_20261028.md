# Run29 independent Store event order revalidation — prereg (2026-10-28)

**Base:** Run27 review-only PR #933 exact `a42e924c56b306a95c9b0972b7c3b372867d4812`; this is a separate child, no mutation to Run27/Run28 owners or main. Run28's stronger Run24 user-message adapter import is separately owned and not a prerequisite for this order-integrity finding. The original Run27 bridge blob is `7f711ce8f5b580949e4b9eb924bc45a6ab7d4ac7`.

**Problem / expected RED:** `EventSourceReader.__init__` checks `old.seq < sheet.seq < current.seq` once. Run27's bridge then captures only SHA256 and `revalidate(ref, expected_sha256)` checks the same hash, not event sequence. With real Store rows, changing the `events.rowid` of `old` after the deterministic German evaluation (without changing any source text, packet, message or SHA) reverses the historical order but currently returns a SHADOW candidate. This is a lineage-integrity issue, not an F5 rule-authority bypass.

**Acceptance:** Add a real ephemeral SQLite Store adversarial test that mutates event rowid after typed evaluation and requires `bridge.Refusal`. Preserve clean German A/B/NONE cases. Fix only the Run27 bridge to compare all three verified pre/post event sequence numbers and order, as well as existing SHA checks, with fail-closed refusal. No changes to frozen Store/Runtime, Run24 donor, original fixtures, model, seed, age or native proof. Keep the post-return revocation limitation explicit.

**Evidence:** Record original RED and GREEN CI job IDs, exact source and test blobs, stage exit codes, closed raw hashes and privacy result. A passing source-only test is NOT native model or Redmi evidence. Never promote STEP2/B3/Body-JEPA/LP3 or learning authority. Next command: `cd v13/code && PYTHONPATH=.:tests python3 -m unittest -v tests.test_run29_store_seq_revalidation tests.test_run23_store_typed_bridge_shadow tests.test_run27_store_typed_bridge_review`.

**Gates:** Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight=0; Redmi unmeasured; whole V13 incomplete. Remaining platform budget UNKNOWN.
