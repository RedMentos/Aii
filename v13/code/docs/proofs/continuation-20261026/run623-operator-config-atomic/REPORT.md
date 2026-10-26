# Run623 — four operator settings now idle-atomic

2026-10-26. Review-only child of Run622 PR617 exact base `4dd297e74ddd218848e05578a9834ea152d6bb90`. Frozen acceptance `PREREG.md` committed before code. Existing operator previously let `:semantic`, `:sampling`, `:duplex`, and `:effort` **mutate state while a native turn was running**, bypassing the later common idle gate. The patch puts each mutation inside `r.lock` and `r.require_idle()`, before any validated config save or effort state write. Status forms remain readable during busy turns. No new authority, Age, model or learning capability.

## Executed evidence

Actual Linux SQLite Runtime on original Run601 phone source base with the **same four code changes** and source-identical new test blob `540b566d9d10edd41ef7c4e4de84561986a0a08f`:
- Original operator (before fix): **observed RED**, busy-turn mutation tests fail because `:semantic off` and `:sampling legacy` do not raise; raw SHA256 `d53bd0e691ead122ef51c96864b70b74dd55863d2d7c416e52322efa8f595f5f`. Failure retained.
- Patched operator: new tests **5/5 PASS** (busy turn and shadow refusal, status while busy, restart, invalid values, unchanged Age/learning).
- Combined new atomicity + Run620 language + original prompts + Run616 gist + Gist readout: **36/36 PASS**, raw SHA256 `13284f7cc46863232dec69f668042994ba75501b646289399e0622042d68205d`. No model inference.
- Remote exact-current operator blob `9b928d1cce3dfc1466b564cf20130cb9e7af8706`, test blob `540b566d9d10edd41ef7c4e4de84561986a0a08f`. Source-only hash-bound Actions workflow added; **CI status UNVERIFIED**.

**Limit:** local executed Runtime base is historical Run601 with same patch, not full current remote checkout; no native/Redmi run. Canon unchanged, no STEP2/B3/Body-JEPA gate promotion; jepa_weight=0, Redmi UNMEASURED, V13 INCOMPLETE.

Next: verify exact Run623 Actions PR head and raw tests/privacy; independent review of other live-config changes only if a concrete source inconsistency is found, otherwise move to substantive Canon learning/utility. No main integration.
