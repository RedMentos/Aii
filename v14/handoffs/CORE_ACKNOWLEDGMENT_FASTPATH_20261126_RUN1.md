# Core & Harness — exact acknowledgment fastpath (2026-11-26)

## Change
- Extended the existing source-bound greeting reflex with a separate exact-text acknowledgment table.
- English/German thanks and explicit receipt acknowledgments can return a short built-in reply without loading B1/B2/C3.
- Bare `yes`, `no`, `ok`, approval verbs, mixed requests, and multimodal inputs deliberately remain on the normal path.
- The existing whole-source text hash, modality exclusion, bounded input, fixed-policy receipt, and audit path are reused. No new authority or persistence is added.

## Verification boundary
- Parent: `core/v14-greeting-fastpath-pin-rebind-20261126-run1` at `b4ca2a37670d084b6edb4cb7eb1cf56e6a3e7ce7`; parent PR #2534 exact-head CI was 7/7 SUCCESS.
- New exact Runtime regression and source-bound matcher tests are included; exact-head GitHub CI is pending.
- LOCAL_LINUX full Aii checkout: BLOCKED / NOT_RUN; this execution environment has no checkout and GitHub DNS resolution fails.
- No Redmi/Termux test, APK, model, weight, permission, user-data, or updater action. REDMI_UNVERIFIED / NOT_RELEASED.
- This is an additive low-latency response path, not a general answer path and not proof of whole-system completion.

## Next
Run the exact PR CI, repair only measured failures, then review the stacked greeting/acknowledgment path against the existing normal-path fallthrough and output-policy gates.


## Exact-head follow-up — 2026-11-26

- LOCAL_LINUX Python 3.13.5: isolated matcher `py_compile` PASS and 14 source-bound allow/deny checks PASS. This is not a full repository or Runtime integration run.
- GitHub CI on initial code head `987bcd22ac77bc1baeb1f302873a8900f0a58364`: runtime deployment integrity PASS; Core fastpath/interrupted-runner retention PASS; staged/integrated regression still IN_PROGRESS at last poll.
- A follow-up commit corrects the module/function docstrings to describe both greetings and acknowledgments; exact CI must be read again on that new head.
- Redmi remains REDMI_UNVERIFIED; PR remains draft and NOT_RELEASED.
