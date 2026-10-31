# Run80 B1/B2 → C3 source envelope post-render QueryPacket and retained-state binding

Date 2026-10-31 UTC. Owner GPT-6, isolated child of Run77 forensic PR #1438 exact parent `8da75d9396760c7907726d71d783c236527cefa7`; sibling of independent Run77 B2 quote audit PR #1439. The original Run56 `build_c3_source_envelope` is default OFF, prompt-only and never output-authoritative. Canon v10.16.1, model/seed/cohort hashes, original negative evidence, original native code and production Runtime are unchanged.

## Observed static gap / preregistered counterexamples
The Run56 adapter snapshots OfferPacket payloads, renders `Cognition.analyst_context`, then rechecks current USER and OfferPacket payloads. It **does not recheck QueryPacket payloads or topic-partitioned retained-state version** after rendering. A QueryPacket or retained state can mutate between successful render and returned C3 prompt, while current USER and OfferPacket bytes remain unchanged. A post-render test can inject a real SQLite mutation in a controlled callback to reproduce this. This is a read-only prompt-construction race, not an assertion of observed malicious action.

## Locked work plan
1. Capture the exact persisted QueryPacket bytes, its ID, and the topic-partitioned retained-state payload/version for each B1/B2 OfferPacket before rendering. Keep existing strict role/event/generation/model checks.
2. After `analyst_context`, re-read both QueryPackets and retained-state payloads/versions; refuse if missing or different. Also refuse active generation/model revision drift. Preserve existing current USER/Offer checks. No writes, no output, no model call, no auto-merge.
3. Add real temporary SQLite tests for an unmodified success control, QueryPacket mutation during render, retained-state mutation during render, and missing QueryPacket. All fail-closed with distinct status; test that the candidate never writes an action/assistant output.
4. Run focused tests plus legacy source-envelope suite and privacy/diff/compile in isolated Actions; close raw receipts and SHA256SUMS. If a focused test fails, retain RED and correct without hiding original attempt.

Claim ceiling: **software/real SQLite SHADOW only**. Not a guarantee of atomicity after return; C3 native dispatch still needs source/packet recheck at dispatch time. No C3 semantic utility, TTY, learning, STEP2/B3/JEPA/Redmi or whole-system promotion. Historical full-suite 4 FAIL/66 ERROR/28 SKIP and Run70 3/6 C3 source-only RED remain.

Exact next command: implement `v13/code/v13/b1b2_c3_source_envelope_candidate.py` and `v13/code/tests/test_run80_b1b2_c3_postrender_bindings.py`; run focused CI. Remaining platform budget UNKNOWN.
