# Run106 exact frozen-baseline positive/current-source negative audit follow-up — prereg before remote tests, 2026-10-31

Original Run105 terminal raw independently audited: 4,893 tests in 266.285s, **5 FAIL, 64 ERROR, 28 skipped**, exact HEAD `4a668e1c3905b4206db99c1ab791e1b059b1a464`. Original RED Actions artifact `13045368441` SHA256 `e72eaa90363e3d605e239b6c8d6478be570b352d79bc257ba33ffee46f29453d`, CRC PASS and 23/23 hashes, private Library backup byte-identical. Original native prerequisite ZIPs 53/53 and 39/39 hashes pass. No unfiltered GREEN.

Fixed new software audit tests (separate from original failing suites, not an exclusion or replacement):
1. `test_original_frozen_baselines_still_accept_exact_source`: reconstruct exact frozen baseline from manifest for source-handoff and native-firing adapters in isolated temporary root, verify all original bytes and that reviewed candidate differs; no model.
2. `test_frozen_manifest_tampering_refuses_before_candidate`: changed snapshot byte must fail SHA check.
3. `test_current_live_source_refuses_historical_candidate`: current source must reject with exact source-handoff `Runtime is neither exact frozen baseline nor complete reviewed candidate` and native-firing `Live sources differ from complete baseline/candidate` errors.
4. `test_no_model_or_authority_is_needed_to_check_scope`: original STEP2_EXIT remains `EVIDENCE_NOT_PASSING`.

Run the four tests on full current checkout and **actual extracted current phone ZIP**, plus unchanged Run104 21-case bounded smoke; verify ZIP CRC and all source manifest hashes, privacy/diff, raw stage exits and hashes. Preserve original RED unchanged. This audit does **not** make the old unfiltered tests pass and does not claim native/model/Redmi utility.

Independent local extracted source preflight 4/4 PASS, Python 3.13.5, no model; not substitute for Actions raw.
