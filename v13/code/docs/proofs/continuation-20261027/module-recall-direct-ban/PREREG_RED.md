# Direct module recall typed-ban bypass: independent preregistered RED (2026-10-27)

Parent is review-only PR #675 source head `99c6d4dd82a35d4df54e080e41586ee120353e25`, based on five-way PR #672; no main merge. Scope `module_learn.recall` and operator `:modul frage`, not runtime/frozen model/age gates.

Four tests committed **before** source change: `683182da2e4a5d0adcfa2ab6c38b3d74cc0ced60`; workflow `5bda873ce2e17c82ae8e7d2beb9db957f16f8ea9`. Exact typed `:verbot werkzeug module_recall`, broad READ_LOCAL ban, operator direct reader, and ban inserted after corpus snapshot. Expected: no hit or module content emitted under ban; unbanned positive lookup remains available.

**Observed original RED:** Actions `40466019062`: 51 tests, **4 FAIL** (all four new counterexamples); existing 47 PASS. Compile0, privacy CLEAN. Original raw ZIP artifact `12716174443`, Actions-upload SHA256 `a09b3697b0f1c2c0dd127f5776e193301d2a4bc67983d2ccaa9340ef83b6730f`. CRC/HEAD/exit/private byte verification pending until artifact retrieval. Do not reinterpret as green.

Proposed fix: direct recall must check the same fixed typed `module_recall` gate as the ToolRegistry path before and after corpus read, including Notaus and user rules, without granting new model autonomy. Fail closed to empty hits; do not convert the read into a tool proposal or silently activate it. Retain existing module enable/learn switches and tags.

Evidence level: synthetic SQLite only, no real network, model, native or Redmi. STEP2 UTILITY_FAIL; B3 L1_FAIL; Body-JEPA UNAVAILABLE; `jepa_weight=0`; complete scope false.
