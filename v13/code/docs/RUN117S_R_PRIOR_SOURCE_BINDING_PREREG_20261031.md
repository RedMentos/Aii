# Run117S-R — independent causal/source binding adversarial review (preregistered)

Base: Run117S PR #1499, exact HEAD `dc0851db19a9872d580460dd67e650d247b7b6f2`. Separate review-only child branch `assistant/v13-run117s-prior-source-binding-review-20261031-1915`. Owns only the Run117S selector candidate, its adversarial test module, this preregistration, a scoped checkpoint, and a branch-only CI workflow. Do not alter frozen Cognition, Runtime, seed1061 fixture, model/runner pins, or prior original raw evidence. Run117T native branch is independently owned and must not be overwritten.

## Problem and predeclared counterexamples

The exported default-OFF `select(runtime,current,original_context,operator_opt_in=True)` validates the prior offer packet, source SHA and project scope, but currently obtains the prior event's packet directly rather than calling `_bound_user_event` for that prior event, and copies `original_context[0].native_context.hypothesis` without checking it against the persisted offer summary. A caller-supplied context may therefore survive despite a prior USER-message edit or forged hypothesis. These are source/authority integrity risks even though the normal CausalOfferConsumer upstream already filters some cases.

Predeclared tests, run against a real SQLite Store and deliberately synthetic Body only:
1. Original six frozen seed1061 cases still produce exact selected policy and no output/actions/learning.
2. After a prior USER message's text is changed without changing the original SourceRef, direct `select` must refuse; verify the original pre-fix result separately if possible.
3. A caller-supplied `native_context.hypothesis` changed to instruction-like text must refuse before Body is called.
4. An incorrect `native_context.authority` must refuse.
5. The prior event must be bound as an authoritative same-session USER with an earlier durable USER message ID than the current event, and exact generation/source; equal/later IDs fail closed.

## Planned narrow fix

Use the already-existing `_bound_user_event` helper for the prior event and require its generation/source and durable message sequence to match the current bound USER. Bind the supplied prior hypothesis and authority to the persisted OfferPacket's summary and canonical untrusted label. Keep the 240-character exact source window and all other checks. Do not give hypothesis semantic authority. Return a RED status rather than throwing.

Acceptance: targeted real-Store adversarial tests + inherited Run117S model-free preflight and source-envelope tests, compileall, privacy scan and git diff --check on a GitHub Actions pinned checkout. Close original CI logs/hashes before any success claim. No native model calls, STEP2/B3/JEPA/age/Redmi/whole-system promotion; `jepa_weight=0`. Keep PR draft and unmerged.

Next independent work after verified CI: original Run117T seed1061 native three-arm pilot if its owner has not already done it, otherwise review its raw evidence and continue another canonical package. This package is a separate guard, not a replacement for native Body complementarity.
