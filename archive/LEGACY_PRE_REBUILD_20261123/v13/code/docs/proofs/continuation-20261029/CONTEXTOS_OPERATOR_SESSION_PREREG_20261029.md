# Context OS operator session boundary — preregistration 2026-10-29

Parent review chain `cf4f69caefce2dfbc179e58e68bfa88f14084342`,
full unfiltered software review PR #1163 still independently running.
This is a separate small N7 Context OS package.

## Observed bug
`:ctxos last` currently queries the globally latest `ContextPlan`
packet with **no session filter**. A plan from another chat can therefore
be displayed as the current chat's plan. `:ctxos outcome <Event-ID> <score>`
also accepts an event ID without checking the current chat and can update
the learned Context OS prior using a foreign chat's plan. These are operator
cross-session information and policy boundaries, not a request to change
N7 learning semantics.

## Predeclared tests
- With a foreign session ContextPlan newer than a current-session plan,
  `:ctxos last` returns only the current-session plan.
- If the only ContextPlan belongs to a foreign session, `:ctxos last`
  returns JSON null rather than the foreign packet.
- `:ctxos outcome <foreign-event> <score>` and unknown IDs refuse before
  `ContextOS.outcome` is called or any policy state changes.
- A valid current-session `:ctxos outcome` still works as before, with
  existing explicit operator authority and no autonomous activation.
- Existing Context OS compression/cache/source-lineage tests remain passing.
- Focused software CI, Canon hash, compile, privacy/diff checks, original
  raw SHA256SUMS. No STEP2/B3/Body-JEPA/LP3/World-JEPA/Redmi promotion.
