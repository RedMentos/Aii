# Run593 prospective registration — Callosum rating replay after a duplicate note (2026-10-26)

Owner: GPT automation11; review-only candidate stacked on PR587 exact head `2b48b202d116151fb106a32269069c91b90ff7f0`. Branch `codex/automation11-run593-callosum-rating-replay-20261026`. Exclusive edit scope: `v13/code/v13/callosum.py`, new Run593 tests, workflow and this proof directory. PR592 JEF branch belongs to a separate owner/package and is untouched.

**Observed read-only defect in PR587:** `on_rating` skips individually `rated` entries, but not all pending references to the same MessagePacket when one is already rated. `Callosum.note(event, existing_packet_id, ...)` can append a fresh unrated duplicate *after* the first successful rating; a second rating updates channel policy again. An old partially-rated pending state has the same problem. The original Run591 test only covers duplicates present before the first rating.

**Prospective change:** Derive the already-rated packet-ID set from the current CAS state, skip *all* entries for those IDs, and mark matching duplicates rated in the winning transaction. Preserve one rating per distinct valid packet, existing outcome scoring, source checks, Age 0, and negative gates. Avoid changing any model/native/source cohort.

**Tests:** Real SQLite/Runtime message: rate, append same ID, rerate -> no utility increment; seed partially-rated state and retry -> no increment, duplicate repaired; valid different packet still gets a rating; restart persists idempotence; existing Run591 and Callosum/outcome/lineage regressions. Exact-head GitHub Actions model-free run, source SHA manifest, privacy scan, raw artifact and strict exit checks. A red unrelated legacy test is not promoted or silently hidden.

**Claim limits:** source-only B3 policy integrity; B3 latent L1 FAIL, STEP2 UTILITY_FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, Redmi unmeasured, full V13 incomplete. Independent review before merge.