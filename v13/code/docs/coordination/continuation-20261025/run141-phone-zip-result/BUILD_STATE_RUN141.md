# Run141 — exact phone ZIP and independent extracted proof (PASS)

2026-10-25 UTC. PR #172 source-under-test exact commit `fe902a560ea8bff171ff3b8c4b134bb9b0366211`. GitHub Actions run `40156332906` **SUCCESS**, official privacy clean, source and extracted tests green. Original Run138 independent Linux guide fallback FAIL remains preserved and was fixed test-first in Run140; this Run141 ZIP contains that fix.

GitHub Actions source-only artifact ID `12584274811`, expires 2026-11-24. Wrapper `V13_RUN141_PHONE_SOURCE_WRAPPER.zip` SHA256 `5e95a4a9d2aade9ae213d0f3843148f1f16b181f3805ab0783c82f6e2610d720`; inner `V13-Phone-Run141.zip` SHA256 `11ea4b19c2be82a219582e877bc671bf6936f8794398dfff4cc92682714c18cd`. ZIP CRC PASS, source manifest schema1 **867 files**, Canon present, no model/private payload. Extracted frozen Runtime Git blob `a691d27bd0772a4fa1f03d57ec90663237bf6825`, Widget installer `9f9fed1f0fa22f5a2168cc4e41257a2adabd3abd`, new fallback test `cfe112912f7cc7d17c308c488eaad036f861f482`, byte-exact.

**Independent Linux extraction (different host from Actions): 37/37 PASS in 3.926s**, including forced successful/failed `more` fallback, Run127 quote/stop tests, phone prestart/halt, AGE0d/HX2 and Run136/139 fixture tests. The earlier Run138 no-less failure is no longer reproduced. Raw independent log local `/mnt/data/v13_run141_verified/RAW_INDEPENDENT_EXTRACTED.log`.

Private Library backup `/V13_Run141_20261025/V13_RUN141_PHONE_SOURCE_WRAPPER.zip` uploaded and independently materialized; SHA256 byte-identical. Rejected anyone-writable Drive destination untouched.

**BUILD_STATE:** source ZIP Linux/software PASS, Termux/Redmi **NOT RUN**, native full-system **NOT RUN**, complete V13 **INCOMPLETE**. STEP2 `UTILITY_FAIL`, B3 L1 `FAIL`, Body-JEPA `UNAVAILABLE`, `jepa_weight=0`, DS2 H2 `FAIL`. Run129 full-suite inherited 4 FAIL/1 ERROR. No gate promotion.

**Next:** actual Redmi Termux installation and operator acceptance from this exact source ZIP, after device is available; meanwhile continue other independent canonical packages. Do not conflate successful ZIP extraction with functional end-to-end V13 utility.
