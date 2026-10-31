# Run74 — F1/F5 authenticated mixed-range JEF SourceRef decision (2026-10-31)

**Owner:** GPT-6; isolated child `assistant/v13-run74-f1f5-range-source-lineage-20261031-auto11` of Run73 software candidate at `c40eef97b3da14c1165e485b91bdafd0d036d031`. Canon, original `jef_f1f5_source_admission.py`, `jef_typed_source_shadow.py`, all frozen model/seed/cohort sources unchanged.

**Functional gap:** Run73's deterministic mixed Minimum/Maximum rule reader validates Store SourceRefs but explicitly does not verify F1/F5 human lineage. Without lineage, the parser's correct decision cannot be used as an authenticated current-human policy. This package adds an independent default-OFF human-source admission wrapper for Run73, not a production authority.

**Fixed checks before code:** require explicit operator opt-in; authoritative latest USER event, exact source ref, same session and generation, two distinct active session-scoped `fact` memories with materialized exact human key refs, source text verification, `permission=record`, verified feedback lineage, and conflict veto against additional active same-topic global/session memories. Only then call the new fixed range parser on authenticated policy/sheet refs. Recheck current USER before returning. Six registered mixed-bound cases A/B/NONE/A/B/NONE; negative cases off, newer USER, revoked source, hidden conflict, wrong memory, foreign session, duplicate IDs, wrong project. All source decisions stay `SHADOW_NO_AUTHORITY`; no model, tools, live output, learning or Age promotion.

**Acceptance:** real SQLite Store test suite passes; legacy F1/F5 max-only source admission and Run73 parser regressions pass; independent CI raw and privacy checks. No native model/Redmi, STEP2, B3, Body-JEPA, World-JEPA, jepa_weight or whole-system claim. Run70 SOURCE_SCHEMA 3/6 scientific RED and full-suite 4 FAIL/66 ERROR/28 SKIP preserved.

**Next:** implement wrapper and real Store tests, run focused CI, preserve raw evidence and private byte-identical backup, independent review before integration. **Remaining platform budget:** UNKNOWN.
