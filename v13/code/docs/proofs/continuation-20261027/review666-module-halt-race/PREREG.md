# Independent PR666 review: module-fetch safety revocation during download (2026-10-27)

Review-only child of Claude PR #666 exact head `ed5010708bdb3d11c5e495f01cc07d99d359ba39`; no main merge or changes to Claude's branch. Scope owned here: `v13/code/v13/modules_gate.py`, new `tests/test_review666_module_halt_race.py`, this proof folder and isolated CI. Source/model/cohort/age gates unchanged. This is Linux synthetic/mock-network evidence only.

## Hypothesis and preregistered RED

`modules_gate.fetch` checks Notaus/typed prohibitions/user rules before invoking a potentially 20-second network fetch, but does not recheck after the fetcher returns and before the local quarantine file write. If the operator activates Notaus or adds a prohibition while the fetch is in progress, the function may still write bytes and promote the proposal. This is a deterministic race to reproduce using an injected fetcher that changes the fixed safety table before returning bytes. No actual network request is permitted in this review.

## Acceptance

- A Notaus or typed NETWORK prohibition installed *during* fetch must refuse before writing a quarantine file or promoting the proposal; the original PROPOSED record remains intact and the synthetic downloaded bytes are not persisted.
- A user-rule FORBID installed during fetch has the same effect.
- An unaffected, human-authorized fetch still reaches SANDBOX_OK and existing module/guard tests pass.
- Revoke and all negative gates remain unchanged; no claim of full concurrent linearizability, real network, native/Redmi or complete V13.
- Commit preregistration before tests and implementation, preserve RED and GREEN CI outcomes, compile/privacy check, verify remote bytes.

Open: full concurrency/TOCTOU between the final recheck and filesystem write requires an explicit serialization policy; this patch narrows the deterministic in-flight revocation window but cannot claim a global transaction across network/filesystem/SQLite.
