# Research & Perception handoff — RAW EAR duplex ordering and target-turn idempotency

**Date:** 2026-11-23
**Owner:** Research & Perception
**PR:** #2448 (new branch is a stacked follow-up; do not merge independently)
**Base:** b8ea0bea308270ac12690de62139f96a8823409d
**Scope:** A-plane RAW EAR temporal receipt → active-turn duplex decision; no microphone/provider or release claim.

## Defect addressed

Boss review identified two races in the previous bridge:

1. Distinct valid audio packets could target the same still-active turn. The replay guard keyed only by audio event/packet/receipt, while duplex.record overwrote pending and interrupted by target.
2. The bridge set cancel_event before persisting the handoff. A worker could finish and the next turn could attempt duplex.handoff before the pending relation was durable.

## Planned implementation

- duplex.record will use Store compare-and-swap and first-writer-wins for each interrupted target turn.
- A per-Runtime re-entrant handoff lock will serialize audio publication/rollback with the next-turn handoff reader.
- The bridge will perform Store I/O outside Runtime.lock, commit the handoff first, then signal cancellation.
- If the target turn changes during the Store write, the exact unconsumed relation will be rolled back before the handoff reader proceeds.

## Verification boundary

- Full local Aii checkout is unavailable in this runner; full repository pytest is NOT_RUN.
- Exact-head GitHub Actions and local isolated checks are pending.
- No Android AudioRecord/Oboe provider, APK, microphone permission, audible playback, native model, Redmi chat or device deployment is claimed.

## Next

Independent QA/Boss review of the two regressions; then Core/QA can reconcile the signed AudioRecord provider contract against this lease/bridge. Keep microphone capture OFF until a user-started OS-permissioned provider and lifecycle/revocation tests exist.