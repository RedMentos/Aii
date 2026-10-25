# Run153 — independent cross-host Run151 native audit

**Source:** Linux-native C3 Run151 workflow `40161320601`, artifact ID `12585869006`, ZIP SHA-256 `0f19525d8e8abd62ca328ce752a0e8f8b619ca27ced71a42f3bd5c78d53edbe4`; original JSON `0e9d8bc03a74c066ef311618ec80312c3229a784275be16f563cf8e6b172b249`, raw log `50968f11cfd5586b65f6357ef970f2e74d0df587690821084a511a6f34113dc2`. This audit did not run a model.

**Independent result:** 288/288 registered source truths, row IDs, response SHA-256, native model/runner hashes, raw log rows, balanced strata, unload and all original negative gates verified. v2 244/288 supported (84.72%); v3 276/288 (95.83%): +32/288, **11.11 percentage points**. v3 statuses 245 CORRECT / 31 MISMATCH / 12 ABSTAIN by independent source-bound arithmetic grammar. Run151 original automated K1/K2/K3 all PASS; **overall UNVERIFIED**.

**Discovered label issue:** Run151's original broad strict numeric labeler marks row 243 `55 ÷ 22 = 2` as a wrong answer to `Calculate 550 divided by 22.` even though the echoed operands differ. The source-bound checker correctly abstains. Grounded strict wrong denominator is 27, not 28; all 27 were detected. Do not rewrite original report or retrospectively promote a gate.

**Limits:** 32 v3-only responses lacked original strict labels, are not human adjudicated. Linux single C3 is not Redmi, B1/B2, JEPA, learning, live delivery or whole-system utility. Original STEP2/B3/Body-JEPA/DS2/V13 gates unchanged. Nine local adversarial tests PASS.

**Next:** Verify digest-bound CI, compare separately archived Run151 second native replication (unplanned, serialized) when complete, and prioritize A3/Body-JEPA work rather than more arithmetic format tweaks.
