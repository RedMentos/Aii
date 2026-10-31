# Run74 — F1/F5 authenticated mixed-range JEF SourceRef decision (2026-10-31)

**Owner:** GPT-6; isolated child `assistant/v13-run74-f1f5-range-source-lineage-20261031-auto11` of Run73 software candidate at `c40eef97b3da14c1165e485b91bdafd0d036d031`. Canon, original `jef_f1f5_source_admission.py`, `jef_typed_source_shadow.py`, all frozen model/seed/cohort sources unchanged.

**Functional gap:** Run73's deterministic mixed Minimum/Maximum rule reader validates Store SourceRefs but explicitly does not verify F1/F5 human lineage. Without lineage, the parser's correct decision cannot be used as an authenticated current-human policy. This package adds an independent default-OFF human-source admission wrapper for Run73, not a production authority.

**Fixed checks before code:** require explicit operator opt-in; authoritative latest USER event, exact source ref, same session and generation, two distinct active session-scoped `fact` memories with materialized exact human key refs, source text verification, `permission=record`, verified feedback lineage, and conflict veto against additional active same-topic global/session memories. Only then call the new fixed range parser on authenticated policy/sheet refs. Recheck current USER before returning. Six registered mixed-bound cases A/B/NONE/A/B/NONE; negative cases off, newer USER, revoked source, hidden conflict, wrong memory, foreign session, duplicate IDs, wrong project. All source decisions stay `SHADOW_NO_AUTHORITY`; no model, tools, live output, learning or Age promotion.

**Acceptance:** real SQLite Store test suite passes; legacy F1/F5 max-only source admission and Run73 parser regressions pass; independent CI raw and privacy checks. No native model/Redmi, STEP2, B3, Body-JEPA, World-JEPA, jepa_weight or whole-system claim. Run70 SOURCE_SCHEMA 3/6 scientific RED and full-suite 4 FAIL/66 ERROR/28 SKIP preserved.

**Next:** implement wrapper and real Store tests, run focused CI, preserve raw evidence and private byte-identical backup, independent review before integration. **Remaining platform budget:** UNKNOWN.

## Terminal verified software evidence

Original Actions **41183538795**, executed HEAD `919964613b86fd001005d9599112afd52007478c`: terminal **SUCCESS**. **38/38** real Store tests: 8 new authenticated F1/F5 mixed-range, 8 Run73 fixed parser, 8 legacy max-only human source, 14 C3 schema recheck. All **10/10** stage exits zero, Canon/new source pins exact, privacy CLEAN, compile/diff PASS. Original artifact **13035703804**, ZIP SHA256 **`b0bcbcb1f30eb49b5d37022df8e966900fbad35b223f80b9d19083f7867a0f4b`**, CRC PASS, **22/22** inner hashes. Private Library `/V13-Checkpoints/2026-10-31/Run74-F1F5-Range-Lineage/ORIGINAL_ACTIONS_41183538795_SHA_B0BCBCB1.zip`, rematerialized and `cmp` byte-identical. Remote source blob `5449e4f4481174b17433ae3e5af035e90a90dce0`, test blob `89c6893f0d9d9252b2b776d172610d17e47db9e7`.

**Limit:** verified human source lineage is not human approval for visible output, tool use or learning. This isolated source-reader is not wired into production C5/C6. Run75 native typed C3 formatter pilot separately preregistered; its evidence cannot be borrowed until native execution and independent raw verification. Original Run70 3/6 scientific RED, STEP2/B3/JEPA/Redmi/full-suite negative gates unchanged.

**Next:** independent review of Run74 versus original max-only F1/F5 and Run73; execute separate Run75 software preflight and serialized pinned Linux-native C3 six-call formatter if eligible. **Remaining platform budget:** UNKNOWN.
