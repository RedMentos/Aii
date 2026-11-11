# Research/Perception handoff — 2026-11-11 03:00 Europe/Berlin

Owner: Research & Perception, A3 teacher/student checkpoint structure.
Parent review-only PR #1687; candidate PR #1729, branch research-perception/a3-checkpoint-audit-20261111-0300, exact head 0b8ce685f29e584c365fc1b71eb11ea0d1628c54.

Verified repository sources: current main A3 student_worker.py, aplane.py and tests; #1668 team ownership; #1687 source-bound candidate; #1719 footprint audit; #1723 JEPA cohort hardening. No production integration or changed gates.

Candidate: bounded NPZ read-only structural audit, rejects nonfinite arrays, wrong dimensions, unexpected/duplicate ZIP entries, bad support/floor/stem, symlink path, oversized archive/members. Returns STRUCTURE_ONLY, runtime_admission_authorized=false, teacher_truth_authority=false, device_verified=false. Nine synthetic unittest cases and a dedicated CI workflow.

**Proof:** Files committed to GitHub; exact-head CI query returned no runs or statuses at authoring time. No PASS asserted. No Redmi/Android inference or measured memory result.

**Risks:** ZIP structural audit does not prove trusted producer, model identity, teacher truth, source binding, path stability against malicious directory swaps or cryptographic provenance. Do not wire into inference or relax any gates. On Android, O_NOFOLLOW behavior and filesystem conditions need targeted QA.

**Next:** run `cd v13/code && PYTHONPATH=. python -B -m unittest -v tests.test_a3_checkpoint_audit_candidate_20261111`; inspect Actions on exact head; add tamper/race and oversized decompression tests; QA review with #1687 A3 source-bound candidate; only then consider a trusted producer/source-binding integration proposal. Existing Age0 RECORD_ONLY, SourceHandoff freeze, STEP2 and B3 gates remain untouched.
