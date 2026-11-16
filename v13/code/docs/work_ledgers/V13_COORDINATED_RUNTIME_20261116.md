# Coordinated V13 runtime continuation — 2026-11-16

This ledger is a handoff, not a release authorization or proof of Redmi behavior.
Coordinator integration PR: https://github.com/RedMentos/Aii/pull/1991
Base release as last checked: `5d9a86176edb45565af482644ee80dbd622d5614`.
Implementation baseline described below: `843fa42d18c4cb4bbaa3b498db0ed07e216fc192`.

## Coordination

One coordinator owns the shared integration branch. Contributors work on separate
branches with scoped ownership and request integration by exact SHA. Read the
latest PR head and existing handoffs before changing files; preserve frozen
SourceHandoff inputs, SHA-bound builders, existing negative gates, and foreign
commits. No force-push. Do not promote a SHADOW candidate as a phone release.

## Verified software evidence

- At baseline `843fa42`, coordinated source contracts passed 129 tests,
  one skipped and 30 subtests; the repository privacy scanner printed CLEAN
  for `5d9a86176..HEAD`.
- The staged-runtime suite passed 157 tests, 10 skipped and 43 subtests at
  prior source head `c493695`; the integrated organ/memory regression passed
  415 tests, three skipped and 58 subtests at the same source head. The next
  commit only added the privacy workflow step, and both suites passed again.
- A real staged-install regression preserved synthetic model/database bytes,
  exercised RECORD_ONLY for OnlineWorld/World-JEPA, solved 2+2, and carried
  synthetic B1/B2 offers through C4 to C3. This does not prove native-model
  quality, latent communication, or device performance.
- Separate branch `work/v13-two-checkout-migration-proof-20261116`,
  `a0d27fd4742a7dcd2b646d2fe335ab457c6260fe`, tested a base-worker
  RAW install followed by a reloaded worker's integrated install using real
  local Git checkouts and stage. Network, CI reply and process stop are
  simulated. Branch is not yet incorporated into the integration PR.

## Release blockers found by independent review

1. **Migration:** The old in-memory worker can install RAW on its first cycle.
   Full dashboard/relay update and restart plus a second permitted update cycle
   are required to activate the new installer. The isolated migration test
   covers two manually driven cycles; automatic reload/timing, runtime-only
   updates and a stopped relay need separate proof. Keep the draft blocked.
2. **RECORD_ONLY and SHADOW:** Existing staged guards cover the tested
   OnlineWorld and World-JEPA paths, not every local head. Review identified
   FastForward, JEFBridge, C5/ActionLearn, Attention, Deliberation, Callosum
   and workspace adaptation as possible automatic numeric updates or feedback
   bypasses. FastForward's SHADOW duration estimate also reaches a timeout
   reflex that can suppress B1/B2. Repair the actual stage, test live mode
   changes and feedback; do not silently disable hard resource protections.
   Grounding frequency tables are a separate contract question. This list is
   not evidence of a complete audit of every adaptation path.
3. **Source identity:** The stage copies files from the working tree, including
   potential untracked or ignored files, before generating its manifest. A
   self-consistent manifest does not prove those files came from the CI-checked
   Git commit. Preserve user files and bind all copied source inputs to the
   trusted commit.
4. **Launcher identity:** Python module resolution can prefer a package in the
   caller's current directory over the staged PYTHONPATH. Prove the launched
   `v13` is the intended snapshot even from a foreign checkout.

Agents were assigned separate branches to address these blockers; verify their
actual branch heads and results before integration. The safe-additive workflow
rejects this 37-file PR because it is outside that workflow's 2–30-file scope.
That is not a passing release check. The baseline status of the larger system,
learned latent utility, Android timing/memory, and the 20-turn device acceptance
remain unverified. `canonical_architecture_complete` and
`user_full_scope_complete` remain false.

## Next integration steps

Review the exact isolated patches and tests, compose SHA-bound builders without
changing frozen sources, merge disjoint commits into the shared branch, and
rerun the source/privacy, two-checkout migration, installed-runtime and full
staged regression checks at the resulting head. Add the new checks to the
existing release workflow so future release SHA checks actually run them.
Only then seek the existing independent/release review. Real Redmi evidence is
separate and must not be inferred from these simulations.
