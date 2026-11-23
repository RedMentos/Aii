# Run115H prereg — C3 untrusted USER source role boundary (2026-10-31)

Owner: GPT-6 hourly continuation, isolated review child of Run115F PR #1489 at exact `4fcb4378bb39dabdfa8131c163daebf967397003`. Other owners' branches unchanged. This package is **software SHADOW only** and default OFF. No change to Canon, production Runtime, model catalog, frozen native cohorts or source/model/seed hashes.

## Threat and scope
Run115F `plan_c3_two_source` writes an authentic Context OS ContextPlan with exact USER source text embedded in the legacy *system* message as a volatile JSON payload. This is a valid internal SHADOW record but must **not** be treated as a native C3 execution prompt: USER-supplied text can contain instructions, role delimiters or malicious-looking JSON. For future C3 evaluation, an explicit role-separated prompt boundary must keep the trusted formatter contract in the system role and source data only in the user role, without losing exact SourceRefs or text. This does not prove semantic obedience to the system prompt or prevent all prompt injection.

## Registered change
New `v13/code/v13/two_source_c3_role_boundary_candidate.py` consumes Run115F real Store/Context OS SHADOW plan; validates exact source pointers a second time, returns an immutable fixed system contract and a JSON user-data envelope containing prior/current exact USER SourceRefs and text. It never forwards Run115F's legacy system message to a model. It fails closed on ACTIVE mode, absent opt-in, stale/deleted/cross-scope source, malformed plan or authority discrepancy, and exposes no delivery, tool, model, approval or learning authority. An orphaned ContextPlan may remain on a post-plan failure; report packet id explicitly.

## Frozen verification plan (before implementation)
New real SQLite/Runtime tests: (1) OFF does not create ContextPlan, (2) exact two-source refs and bytes survive user-role JSON while system contains no source data, (3) hostile source instructions/role delimiters never enter the system message, (4) correction injected after ContextPlan refuses without output, (5) ACTIVE Context OS refuses before plan, (6) tampered plan authority/ref refuses. Run inherited Run115F six tests and Run115E nine tests, py_compile, privacy scan. Run isolated source-only GitHub Actions on review branch; preserve raw result, hashes and negative gates. If CI cannot execute, report unverified rather than pass.

## Locked negative gates
Run115C original six-case native structural RED and frozen seed971 unchanged. No native body quotation, no native C3, no JEF model, no Redmi. Age0 RECORD_ONLY; STEP2 EVIDENCE_NOT_PASSING/UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA not proven; jepa_weight=0; canonical_architecture_complete=false; user_full_scope_complete=false. No PR merge pending independent review.
