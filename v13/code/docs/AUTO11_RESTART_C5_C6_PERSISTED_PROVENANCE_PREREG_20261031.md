# Auto11 third package — persisted callback replay and C6 restart preflight (2026-10-31)

Owner GPT-6 automation, isolated review child of PR #1449 exact `328f1a5f6d434ea94bf4d5ccc89b62d367751617`, after verified 65/65 software GREEN and private raw backup. Other owners/native cohorts untouched.

**Problem:** current C5/F3 DRAFT persists dual/JEF/B1B2 prompt digests and callback-output SHA, but does not persist exact bounded C3 callback JSON. A restart verifier cannot independently recompute callback digest or parse the output without re-calling C3. In-memory C6 preflight does not prove durable restart recovery.

**Prospective solution:** wrap the trusted Run84 generator ONCE, capture only its exact strict JSON output (<=1024 UTF-8 bytes, sole action A/B/NONE), independently recheck digest/parser against Run84 verdict, persist it atomically in SHADOW_DRAFT metadata. Add separate default-OFF read-only `resume_preflight` which reconstructs persisted DRAFT by IDs after Store close/reopen, verifies the exact output JSON and digest, dual/JEF/B1B2 source prompt digests, current USER, F1/F5 human lineage, C5/F3 packet binding, one DRAFT/action, no DISPATCHED status, and all metadata keys. No second C3 callback and no native inference, approval, output, tools or learning. A source or metadata change after restart returns RED; callback remains trusted and output JSON digest is NOT a native model proof.

**Acceptance:** real SQLite tests with actual Store close/reopen and restored session/event IDs: valid DRAFT accepted as read-only SHADOW, tampered JSON, recomputed forged action, duplicate JSON key, source forget/new USER, changed C5 status, missing DRAFT and wrong session all rejected. Existing 65 software tests retained. Preserve original failing attempts, pin new blobs, private raw backup, privacy/diff checks. No Canon/runtime/model/seed change or production activation.

**Evidence gates:** historical full-suite RED; Run70/77 RED; Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; World-JEPA SHADOW; jepa_weight0; Redmi UNMEASURED; whole V13 incomplete.
