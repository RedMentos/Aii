# Run125 — startup STOP notification + exact source-only phone ZIP

2026-10-25 UTC. Base Run124 PR #155 exact head `80c22155f24651bb1dd26dfb9d3e22e202ea182b`. Owner: narrow `v13/code/v13/ui.py` startup notice display, new `tests/test_phone_startup_notice_run125.py`, new workflow/proofs only. Runtime preworker gate, Claude Widget module, operator, Canon, model/training/learning and registered cohorts read-only. No native jobs.

**Observed gap:** Run124 applies pending STOP before worker, stores fixed user notice texts in `Runtime._startup_phone_halt`, but both chat UIs set `r.notify` only later and never display those startup texts. A user returning to Termux may not know why V13 is stopped. Preregister real Runtime with preexisting STILLSTAND and a noninteractive plain UI (EOF) to require exactly one visible STOP notice. Second test requires idempotent consumer, so fallback/re-entry cannot spam or reapply a stop. Test-first RED; preserve raw.

Narrow fix: one `show_startup_stop(r,emit)` consumer clears only the pending **display list**, never the actual persisted stop. Call it after `r.notify` is set in both plain and prompt-toolkit paths. No auto-release or changed safety gates.

After GREEN (2 new + 28 inherited), build source-only Termux ZIP from exact PR head via existing packager, check CRC/manifest/canon/Widget installer/preworker tests/no models or databases, extract, run the same Linux software suites from extracted bytes and publish 30-day artifact. Hash artifact wrapper and inner source ZIP separately; download remote bytes independently. No Android/Redmi proof or full V13 promotion. Original STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE.
