# Run132 — integrate preserved Claude WP-HX1/HX3/HX4 shadow modules, test-first

2026-10-25 UTC. Active Run128 source base `ad3183796f9a06c7bea9c2e956a43c623e042dcb`. The binding ROADMAP records WP-HX1/HX3/HX4 as DONE on Claude branch `claude/project-thread-4iqpro` (2026-10-22), but these exact modules are ABSENT from active Run128/Run130 source tree. This is a canonical integration gap, not permission to redesign. Read original Claude files and import **exact source bytes** where possible, with provenance hashes:
- `agi/harness.py` `002d2d981314f3ffcbd8c02d7ec835a99abb0599`
- `agi/experience.py` `8908adb75ff859356bf0f4fb9ae62c8282581519`
- `agi/blind_select.py` `2ff30cb68ecded2a1853b39e07b1d9a2a8f571f2`
- `tests/test_harness_hx.py` `aa39a8c5d0d5a4ffda1416738e84e364365e4963`
- Claude `agi/self_improve.py` `f18ec4494bbe17a92793aca081fdebfe897349f7` vs active `04e266e3030b598ced5eb8d1174e8f767559f218`; Claude `agi/__init__.py` `27a5f57885a2836d0a3fbd4cf1829c0a1ab4edce` vs active `d6a7c7d22aeee6800dd97d556d508f2035409c72`. Review these two existing files line-by-line; only integrate the narrow HX additions, do not replace unrelated newer code.

File ownership: ONLY 3 new modules, `agi/self_improve.py`, `agi/__init__.py`, new tests/workflow/proofs. Runtime, models, Canon, user decisions, installer and other agents read-only. Test-first RED import failure, then GREEN Claude's original 10 tests + inherited AG8/Growth/AGI tests + privacy + source-bound frozen Runtime hash. No live consumer of overrides; HX2 and user approval remain required for activation. No model/native/Redmi/AGI claims. STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE.
