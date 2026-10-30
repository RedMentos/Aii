# Run11U — source-key/value identity shadow, disjoint software proof (2026-10-30)

**Review-only, not wired into Runtime or FocalLoop.** Independent child of Run11S PR #1248 exact parent `65585cd7518b98dd09562a1d083347435b2f8d0b`. New source `scripts/focal_source_identity_guard_run11u.py` wraps the frozen Run11S selector without modifying its source blob `bf9c7d8ee75bbe82a82c0c2d3dc4cefed4036bce`, seed167 results, WP-Z5b original generator `9d61acdd8f8aa47435ed682ac4b7013fd3e02df8`, models, Canon or learning gates.

## Concrete defect and correction

Run11S parses the note value but returns its key without checking project/month/kind agreement. It can admit a key whose body belongs to a different project or revision. If a newest note becomes syntactically malformed, Run11S can silently select an older budget note, falsely presenting it as the latest. Run11U performs a separate **syntactic key/value consistency check** for selected sources, scans all relevant keyed revision notes to reject malformed newest/older notes before fallback, rejects queries naming multiple distinct projects, and returns **zero admitted source keys on abstention**. The old first-four fallback is retained only as diagnostic metadata, never source authority.

Scope remains narrow: source text grammar, not fact verification, model utility, semantic paraphrase handling, or F5 live-source provenance. This is not an autonomous memory policy or a learned head.

## Closed raw and measured results

- Preregistered seed **173** (not historical seed11 or frozen Run11S seed167), 60 new synthetic cases, four kinds ×15, capacity4. Original frozen `tasks` and `required_keys` oracle reused without modification.
- Original software Actions **41038410680 RED**, exact HEAD `a28c4dc564961cf4ea7f022d130390302ca1e230`, artifact **12969575928**, ZIP SHA256 `8436a0a828ad037d83048ebb6b3e776d1ec74cd47f5a6394ea9e4e94f64a5797`, **8915 bytes**, 20 entries, CRC clean, **19/19 inner hashes**, privacy CLEAN. **21/22 tests PASS**, one real failure: injected latest note was ignored and older note selected without abstention. Failure preserved, not waived.
- Fixed only the new Run11U guard to inspect relevant keyed notes before source admission; added older-revision and unrelated-note controls. Final software Actions **41038525401 GREEN**, exact tested HEAD `85a6289c2088548f33825638e43cedc9ca6c0452`, artifact **12968937319**, ZIP SHA256 `9967ab363d1d134b11bb6da829f72773715cfdf6d00872f22b29bfef7b82c10a`, **8776 bytes**, 20 entries, CRC clean, **19/19 inner hashes**, **24/24 tests PASS** (10 frozen Run11S + 14 new), 8/8 stages0, privacy CLEAN.
- Fresh unaltered seed173 **60/60 exact required keys**, same as frozen selector on this new fixture family; no abstentions. Key/value mismatch, month/project/kind mismatch, malformed latest/older source, duplicate keys, unsupported query and multiple query projects abstain or reject as tested. These are **synthetic controls**, not model-answer success.
- Original GREEN and RED ZIPs uploaded to private Library `/V13-Checkpoints/2026-10-30/Run11U-Focal-Keybound/` and independently **byte-reverified after materialization** against the SHA256 values above. No private data in public GitHub.

## Gates and next work

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight0; Redmi UNMEASURED; G-FOCAL-CAPACITY-003 remains PARTIAL; whole V13 incomplete. No Runtime/FocalLoop integration or model inference; no authority from this source-only shadow. Existing historical full-suite Run34/Run37 RED not waived.

Owner GPT-6 Run11U branch `assistant/v13-run11u-focal-keybound-shadow-20261030`; only new Run11U source/test/workflow/scoped docs touched. Next highest-priority work: independent disjoint model-output paired focal capacity/recency study with frozen baseline, full/retrieval and coalition controls; only after measured utility and real Store/SourceRef validity should a read-only runtime SHADOW consumer be considered. Do not tune or rescore historical WP-Z5b or Run11S cohorts.

Exact next command: on a checkout of Run11U HEAD, `cd v13/code && PYTHONPATH=.:tests:scripts python -m unittest -v tests.test_focal_replacement_shadow_run11s tests.test_focal_source_identity_guard_run11u && PYTHONPATH=.:scripts python scripts/focal_source_identity_guard_run11u.py`. Verify source hashes, original Actions 41038410680 and GREEN Actions 41038525401 artifacts before using the result.
