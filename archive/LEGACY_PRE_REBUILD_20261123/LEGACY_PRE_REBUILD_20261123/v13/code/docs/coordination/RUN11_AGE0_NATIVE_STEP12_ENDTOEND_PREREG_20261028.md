# Age0 current-catalog native end-to-end Linux JEF/C2/C3/B1/B2 — prereg 2026-10-28

Owner: Codex isolated review child of #843 source `e954a86d8aa88d666e5f9dc4309951d8821dd1fe`; no main/owner branch overwrite. This is a **substantive runtime integration** test, not an isolated model CLI smoke. Prior exact separate C2 native `40631873306` GREEN, B1/B2/C3 serial `40631633470` GREEN, full software suite parent `40630928415` 2208 PASS; all original raw ZIPs backed up in private Library with SHA verification. No other heavy native owner active at prereg.

## Protocol

Fresh Ubuntu24.04 x86_64 ephemeral `V13_HOME`, current repository source, pinned immutable `specs/models.json` Git blob `7af05962af41d0bc3f7dd18ef01d4eba55eabf99` and control_tools Git blob `954a3f468f10195fbce12d27f68585ee7edee2c9`. `V13_NO_AUTOSTART=1`, `NEEDLE_TELEMETRY=0`, `DO_NOT_TRACK=1`, `OMP_NUM_THREADS=2`. Install only routine isolated Python dependencies; `python -m v13.bootstrap --home <fresh>` downloads exact pinned public model/runner/Needle files and builds worker. Do not alter models, source, seed, prompts, or release/approval/learning gates. Verify actual model hashes/manifest and `learning_mode=RECORD_ONLY`.

Run **serially** on that installed home: `python -m v13 --home <home> probe jef-modes` (C2_ONLY, C3_ONLY, C2+C3, C1 restart), then `python -m v13 --home <home> probe step12` (C2/C3 without B, restart, then B1/B2 separate roles in one turn), then one public fixed `python -m v13 --home <home> ask 'Budget 120 Euro. Berechne die Hälfte.'`. No user data. Preserve stdout/stderr/exit and exact `exports/jef-modes-proof.json`, `exports/step12-proof.json` and per-turn metadata; hash all, upload **reports only**. If bootstrap or any stage fails, retain RED and raw logs, do not substitute weights or infer PASS. Timeout each stage, no parallel heavy jobs.

## Claims and gates

A PASS proves only these Linux-native Age0 runtime integration fixtures. It does **not** prove semantic STEP2 four-arm utility, model complementarity, learning, B3, Body-JEPA, Redmi, thermal/energy, or full blueprint. `STEP2=UTILITY_FAIL`, `B3 L1=FAIL`, `Body-JEPA=UNAVAILABLE`, `LP3 heldout=FAIL`, `jepa_weight=0`, `Age0 RECORD_ONLY` remain. No automatic human approvals, training commits, external tool execution, cloud inference, or public model redistribution.

Next exact command after source checkout: `PYTHONPATH=v13/code python3 -m v13.bootstrap --home <fresh-home>`; then `PYTHONPATH=v13/code python3 -m v13 --home <fresh-home> probe jef-modes`; then `... probe step12`. If blocked, record exact observed stage and continue other canonical packages. Remaining platform budget UNKNOWN.
