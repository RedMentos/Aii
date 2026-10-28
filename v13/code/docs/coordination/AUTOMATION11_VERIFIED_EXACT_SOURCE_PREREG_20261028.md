# Prereg: explicit TTY exact F1/F5 source-value output (2026-10-28)

Owner: independent operator utility lane `assistant/v13-run11-verified-exact-source-20261028`, parent #906 exact source `02cf15583b80c94194b496cc8c3fe5cce6ed3c5c` (**software CI `40674981822` pending at prereg**). Do not implement until #906 independently audited GREEN.

## Locked change
- Extend existing explicit `:verified` operator command with `:verified exact <question>` that returns the **verbatim verified source topic and value**, not a generated sentence. No model call, no native C3, no new source authority, no automatic learning. It is a local deterministic source quote/pointer for user inspection, not a replacement for C3 language.
- Require existing Age0/idle/queue/session and source-bound C3 admission via `scripts.ask_verified_budget.query(...native=False)`. Re-read F1/F5 and SourceRef before output and require the same memory ID, source_ref and exact source value; conflict/revocation/tampering between checks must CLARIFY. Only expose the existing bounded project-budget grammar, not arbitrary memory text.
- Return `status=SOURCE_EXACT`, `topic`, `value`, `source_ref`, `model_called=false`, `native_calls=0`; if unavailable return CLARIFY/NOT_APPLICABLE with no value. Reject `native`/`--native` and oversized/non-TTY input. No modifications to frozen Runtime._turn, SourceConsumer or model weights.
- Deterministic tests: exact authorized source, wrong project, conflicting source, revoked source, simulated post-preflight mutation, out-of-scope, no model calls, no session creation, explicit operator origin. Full software and source-pinned raw evidence; independent audit before claim.
- Preserve every original Stage11/STEP2/B3/Body-JEPA/LP3/Age/Redmi/full-system negative gate, `jepa_weight=0`, Age0 RECORD_ONLY/SHADOW. Native TTY path remains blocked pending independent rule/standstill review.

Next: await #906 source proof, then implement and run focused/full software; continue functional learning/STEP2 work rather than treating source copy as general intelligence.
