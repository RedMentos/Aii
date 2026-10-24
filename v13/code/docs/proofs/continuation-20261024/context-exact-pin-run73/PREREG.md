# Run73 prereg — Context OS exact recent pin under budget pressure

2026-10-24. Base Run72 PR105 1ddcb357358d94632e806a2e303fa58f82a1544b. Owner only `v13/code/v13/context_os.py` plan budget loop, `tests/test_context_exact_pin_run73.py`, Run73 docs/evidence. No changes to models, original context layers, Age, approval, action or memory lineage.

Canonical Context OS §8.3-8.5: recent exact-pinned turns are RAW, verbatim, never silently compressed or dropped. Current budget loop explicitly compresses and POINTERs pinned turns except newest. With 5 long turns and exact_recent_pin=.8, budget 256, it may silently drop 3 of 4 pinned turns while claiming ACTIVE plan applied. RED real full-checkout SQLite/software tests: pinned forms remain RAW even when budget impossible; ACTIVE per-plan fail-closed to legacy (applied=false, reason); generous budget still applies; SHADOW remains legacy; exact numeric/code spans preserved.

Fix: only unpinned turns are compression/pointer candidates. If planned message characters exceed declared budget, record `budget_unmet_fallback`, do not apply Context OS ACTIVE plan, retain legacy behavior without claiming token-fit proof. Runner's exact token trim remains a separate gate. Preserve all original negative gates.

CI Run72 public standard read-only runner available; capture RED and GREEN raw logs. No native/Redmi claims.
