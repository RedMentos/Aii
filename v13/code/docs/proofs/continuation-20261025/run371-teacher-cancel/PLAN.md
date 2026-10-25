# Run371 — teacher fulfil must honor late cancellation and terminal request ownership (preregistered)

Parent: Run370 review checkpoint `3f8747aa25994751058a26c58fcce1fd352a5bc8`, stacked on Run368/PR363; Run369 native owner is independent and untouched. This is a separate learning/teacher functional package, not a whole-system gate.

Owned: `v13/code/v13/agi/teacher.py`, new `v13/code/tests/test_teacher_fulfil_cancel_run371.py`, isolated `.github/workflows/run371-teacher-fulfil-cancel.yml`, this proof directory. Do not edit registered generality suite, source/model hashes, original teacher records, Age defaults or cloud permission settings.

Observed source hazard: `TeacherDistillation.fulfil` checks cancellation and cloud permission only before calling a backend. A backend can run for seconds, during which :stillstand/cancel or cloud revocation can occur. It then unconditionally appends the returned trace and marks DONE. Another actor can also mark the request terminal while the backend runs, yet the stale worker appends another trace. These are concrete request-state integrity and user-consent hazards.

RED-first actual SQLite/Runtime tests: (a) backend sets cancellation event before returning, no trace should be persisted; (b) backend transitions request to terminal before returning, stale worker must not overwrite/append; (c) cloud permission revoked while backend runs must not commit returned reference; (d) normal local teacher still returns reference trace with authority REFERENCE_NOT_FACT; (e) already-cancelled request must not invoke backend.

GREEN: add post-backend cancellation check and final mutation-time checks for current request status, cancellation and cloud permission. Fail closed without promoting a teacher answer to truth; do not create new backend/network calls. The tiny final state-commit race relative to an asynchronous cancel is not an atomic cancellation guarantee; no external backend-call undo is claimed.

Evidence: source-bound RED/GREEN Actions with actual SQLite, inherited AG12 teacher/holdout tests, privacy scan, compileall, closed raw artifacts/hashes and private Library byte comparison. Negative gates remain: STEP2_EXIT FAIL, B3/Body-JEPA/jepa_weight not promoted, no Redmi/native evidence, whole V13 incomplete.
