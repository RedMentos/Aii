# Run112 — integrate independent Run107 with verified Run108–111 review chain (preregistered)

Date 2026-10-25 UTC. Base Run111 PR #142 `7ad451af9787183f929e02818a3cf2930315fdbc`, which already contains Run108/109 World and Run110/111 lab code. Source Run107 PR #138 `cb2d6b8b67da830bdd74235d20d2f4041646834f`, separately verified 26/26 real SQLite and CLEAN privacy. Run106 `codex/episode-vector-finite-run106-20261025` remains a separate active owner of `episodes.py`; DO NOT import/edit it. No force push, no production merge.

## File ownership and exact imports

Integrate only `v13/code/v13/episodic_route.py` blob `90e452f46daec9b8872924b354e0ce977a77d0b6`, `v13/code/tests/test_episodic_route_source_run107.py` blob `452be5bb2ac28c0178b5535c422cfa204dd94236`, and its isolated workflow blob `2e062985854df14258bf2e7945a1c21e9df0fe0e` byte-exact. Preserve original raw RED/GREEN logs, BUILD_STATE and hashes on PR #138; reference rather than duplicate them. No edits to `world.py`, `sandbox.py`, `sandbox_composition.py`, `episodes.py`, model sources, user rules, blueprint or gate ledgers.

## Tests and independent review

Run real SQLite fast route + episodes, World forecast/recovery, DS1/DS2 lab semantics and composition; official privacy scan. The inherited broad source-bound CI additionally runs JEF, Context OS, Callosum, World, Age, rules, phone source ZIP manifest/hash and extracted Runtime smoke. Distinguish GitHub Linux/synthetic/phone source packaging from real Redmi execution.

Acceptance for this integration package: byte-exact source import, no shared-file conflict, focused test GREEN, inherited broad CI GREEN, privacy CLEAN, source ZIP verified. No native/Redmi claims or promotion of STEP2/B3/Body-JEPA.

## Gates

STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE. Run110 DS2 H2_new_word FAIL remains. Run111 synthetic composition PASS remains lab-only.
