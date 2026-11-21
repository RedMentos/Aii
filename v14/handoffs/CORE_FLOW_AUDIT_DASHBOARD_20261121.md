# Core flow-audit dashboard handoff — 2026-11-21

## Ownership and dependency

- Core & Harness owns the dashboard consumer.
- Stacked on the read-only per-turn auditor in PR #2183.
- Base checkpoint: 12fd5edd3fa2ab2e9dc96c209079962af6d98707.
- This PR changes the existing local-only dashboard handler/template; it is intentionally DRAFT and requires independent Boss review. No additive gate is bypassed.

## Executable user-facing behavior

The existing localhost WebView gains an explicit Organdurchlauf prüfen action and a token-scoped read-only GET /flow-audit endpoint. It selects the latest persisted assistant event together with that event's session ID, then calls the hardened per-event reader. The browser receives only bounded role/status/count/token/timing metadata; event IDs, session IDs, source IDs, hashes, prompts, chat text, raw audio and source bytes are omitted. The browser writes output with textContent, not HTML.

The projection preserves claim boundaries:
- B1/B2 query-role binding and per-offer token/model-source evidence
- C4 consumed roles only after the hardened current-role/current-cycle audit
- C3 source-bound context versus unverified semantic use
- B3 TAP/SYMBOLIC/receiver counts, with native injection explicitly false
- C5 action/outcome counts
- source integrity counts and warning codes
- REDMI_UNVERIFIED; runtime metadata is not a device attestation

## Tests and evidence

- Exact local full checkout: BLOCKED by container GitHub DNS failure; no local repository suite is claimed.
- Dedicated CI workflow runs the flow-audit tests and dashboard target test on Python 3.11 and 3.13, plus py_compile and Node syntax check.
- Synthetic Store fixtures are labeled SYNTHETIC_FIXTURE; they do not prove native model attention, trained latent receiver effect, microphone capture, or Redmi installation.
- Deployment: NOT_RELEASED. Existing updater is not invoked by this PR.

## Next action

Boss independently reviews the existing dashboard handler/template change and the safe-additive boundary. After PR #2183 is accepted and this stacked PR is reviewed, the Integrator can include it in a normal pinned release/update. A fresh private device receipt is still required before any Redmi claim.