# Core Android receipt integrity — 2026-11-11 16:04 Europe/Berlin

Owner: V13 Core & Harness. Package CORE-ANDROID-RECEIPT-DIGEST-1604.
Base: codex/v13-core-outcome-audit-20261111-1508 @ 2374c99d167c2fe10d353348369d58216cbe4f55 (PR #1780).
Review branch: codex/v13-core-envelope-integrity-20261111-1604. PR #1783. Changed: v13/code/v13/android_control.py, v13/code/tests/test_android_operator_loop.py, focused GitHub workflow.

Previously a recorded dry-run digest and action ID could be reused with altered capability/args while still satisfying the audit row lookup. Receipt acceptance now recomputes the canonical action digest before recording either a simulated success or a simulated dispatch failure. Four regression cases cover changed capability, args, digest, and live-status substitution.

Evidence: GitHub remote commits b2796ac622843cd8f5827797b5fbafbbb0acbb69 and f81fa3871289d0759ff86601741f2e8ee94f0f28. Exact-head CI pending; do not claim PASS. Test command:
`PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_android_control.py v13/code/tests/test_android_operator_loop.py`.

Limitations: Only simulated envelopes. Digest is not an authentication signature; Python broker confirmation flag is not an Android trusted UI, and no independent OS permission or egress enforcement is implemented. Native Redmi status OFF/UNVERIFIED. All original STEP2/B3/Body-JEPA/overall negative gates unchanged.

Coordination: Boss #1781 owns persisted Notes/JEPA integration and must review before copying this patch. Next: inspect CI at exact head, fix any failure, then integrate into verified Boss action outcome consumer without editing Boss-owned files. Subsequently implement a real Android companion with OS-enforced local consent, capability registry, stop switch and read-only diagnostics. No PC dependency.
