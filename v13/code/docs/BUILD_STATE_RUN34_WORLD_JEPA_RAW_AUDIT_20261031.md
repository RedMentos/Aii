# Run34 closed checkpoint — independent Run32 original raw audit GREEN; W7/World-JEPA FAIL

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Review-only child of Run33 #1360 at `5370b56d5ca6e5f057d0c884aee68ec308769548`. Prereg `WORLD_JEPA_RUN32_RAW_AUDIT_PREREG_RUN34_20261031.md` blob `c679c0d8243ceb7d465cbcf33670ad99cda5d410` committed first at `9b3110b31c187691e68fa6dad09974e90be193f7`, before new auditor/tests. Original Run32 source `550185a74e9daddaea27860f6244c1209d376af2`, Actions `41146711268`, artifact `13021771958`, ZIP SHA256 `adda55e8d4d4fd5aabd328b8f79d03c08d2b6804fb2c48daea4043f1052faecb` untouched.

## Closed original evidence

Independently downloaded original Run32 ZIP: CRC PASS, **130/130** inner SHA256SUMS exact, **9/9** stage exits zero, six exact per-seed original/slot checkpoint identities, all registered seeds 201–203 and train4000/cf150/attr300/steps3000 pinned. Real-file Linux SHADOW, not native GGUF or Redmi. Private original ZIP backup `/V13-Checkpoints/2026-10-31/Run32-WorldJepa-Disjoint/run32-realfile-41146711268-shaadda55e8.zip` independently materialized and byte-identical readback.

Original Z12b 16D arm: W1/W4/W5/**W6 FAIL**. Slot-shared 96D candidate: W1–W5 PASS, **W6 FAIL**. Fresh disjoint W7: W7a PASS (both-world action gain mean **+0.315067**), W7b FAIL (none-self action gain **−0.052600**), W7c FAIL (four-class macro gain **+0.062217** vs prereg >=+.08). All three seeds individually retained; no exclusions. Overall **SHADOW_CANDIDATE_FAIL**. 96D versus 16D capacity confound and non-exact scheduler-timed transitions remain.

## Independent audit implementation and checks

New stdlib-only `scripts/run34_world_jepa_disjoint_raw_audit.py` blob `6aa0e84f51302c1939547f283dae6af05894cce8` checks original outer ZIP hash, CRC, complete manifest, stage/source/seed/schema, per-seed raw checkpoint binding, finite values, negative gates, and independently recomputes W7 thresholds. New `tests/test_run34_world_jepa_disjoint_raw_audit.py` blob `5084006bcf14c29714f733dc3cfc951848ec40a0` includes tamper/negative controls.

Actions `41147936642` at exact source `ec5a73678ebd361cf76db649c1bf5a8e034fb79f` SUCCESS. Original audit artifact `13021484177`, ZIP SHA256 `313d4fb7cc91413b7ed97f34745e6f444f800dc38922c0dbe99bc438b47ebcd6`, CRC PASS, **19/19** inner SHA256SUMS, **11/11** tests PASS, PINS/FETCH/TEST/ANALYSIS/REPORT_CHECK/COMPILE/PRIVACY/DIFF all zero, privacy CLEAN. Original ZIP was read only, not republished. Private audit backup `/V13-Checkpoints/2026-10-31/Run34-WorldJepa-RawAudit/run34-audit-41147936642-sha313d4fb7.zip` independently materialized byte-identical.

## Next command and open work

Independent reviewer: `cd v13/code && RUN34_ORIGINAL_ZIP=/path/to/verified-run32-original.zip PYTHONPATH=.:scripts python3 -m unittest -v tests.test_run34_world_jepa_disjoint_raw_audit && PYTHONPATH=.:scripts python3 scripts/run34_world_jepa_disjoint_raw_audit.py --original-zip /path/to/verified-run32-original.zip --out /fresh/run34-audit.json`. Prerequisites: exact original ZIP SHA above, Python3 standard library, fresh output. Next substantive World-JEPA work: preregister and execute a **matched-capacity** no-action/JEPA control and a stronger non-ceiling attribution intervention; do not reinterpret W6 or W7. Other organs remain in scope.

Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no Redmi, no learned German transfer, no whole-system completion. No production merge/auto-merge.
