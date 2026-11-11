# Research & Perception handoff — 2026-11-11 04:00 Europe/Berlin

Owner: A3 checkpoint structural audit, read-only candidate. Parent PR #1729, grandparent #1687. Branch `research-perception/a3-checkpoint-adversarial-20261111-0400`.

## Changes
- Reject float16 support_floor (only float32/float64 accepted, consistent with other A3 numeric arrays).
- Add four adversarial synthetic tests: float16 floor, nonfinite support, compressed expanded-member overflow, and truncated archive.
- Existing checkpoint audit still returns STRUCTURE_ONLY and cannot authorize runtime, teacher identity, or device claims.

## Evidence and limitations
Changes are committed to GitHub. No local executable test or exact-head GitHub Actions PASS was established by this handoff. These are regression candidates, not validated runtime hardening. Note that the compressed oversized support fixture has 2049 rows, and therefore also violates the row-count bound; the test asserts rejection, not which bound fired. ZIP truncation may raise BadZipFile or another documented parsing exception.

## Integration and safety
Do not merge without exact-head CI and independent QA review. No A3 inference path changed; no Age-0, SourceHandoff, STEP2 or B3 gates modified. Android/Termux and memory/latency remain unverified. Next: run targeted unittest, check CI and source-bound A3 producer/teacher identity before integration.
