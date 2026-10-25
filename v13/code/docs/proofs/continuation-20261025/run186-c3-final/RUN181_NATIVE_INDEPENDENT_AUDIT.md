# Run181 native B2 offer result — independent Run185 replay (2026-10-25)

**Evidence level:** verified Linux x86_64 native B2, synthetic 36 memos × 3 views; **NOT** C3 final-answer, B1+B2 complementarity, JEPA learning or Redmi. Frozen Run181 source and acceptance untouched.

- Original Run181 GitHub Actions run `40168581804`: SUCCESS; immutable artifact `12589259384`.
- Downloaded ZIP SHA256 `cb0786ec15734efe4b3dda2607218dccf98cb96015d2852349a44b8c689982fb`; `report/report.json` SHA256 `ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880`.
- Independently reconstructed the exact 36-row corpus from the frozen generator; SHA256 `1872a3adf6e51e05e604053539d50ae05c955b221f78f1951d1f68e2a12f926c`, matches report binding.
- Recomputed all 108 original raw B2 `hit`, `stale`, `quotes_valid` and `quote_has_key` fields. No mismatches. Three parse-failed rows lack `n_quotes`, as original scorer does not return that field on parse failure; preserved as evidence, not silently imputed.
- Original frozen decision: **`GIST_NO_GAIN`**. Gist vs fixed960 paired hits wins **2**, losses **3**; gist prompt tokens mean **1950.8** vs fixed960 **914.9**, violating <=110% token criterion. Original hits fixed960 **33/36**, gist **32/36**, event960 **25/36**.
- Separate **posthoc diagnostic**, not a changed preregistered verdict: exact source-supported hits fixed960 **24/36**, event960 **17/36**, gist **25/36**; gist vs fixed960 supported wins **5**, losses **4**, but token cost still fails. Result: **`NO_SUPPORTED_GIST_GAIN`**.
- Original report contains one fixed960 and two event960 empty quote lists; original `quotes_valid` can be vacuously true on empty lists. Run185 diagnostic requires nonempty exact quotes. This is a measurement caveat, not proof of malicious behavior.
- Full closed original ZIP is backed up to private Library `/V13/Run181-native-B2-gist-raw-20261025.zip` and verified byte-identical after re-materialization. Full Run185 posthoc raw 108-row audit is backed up to private Library `/V13/Run185-source-support-native-replay-20261025.json`, SHA256 `8d2ce6bc11d9886d64ced495ef0ba55fc9a7ac3733e169ee0c8c63b7a33824a4`, independently re-materialized and verified.
- **No gate promotion:** STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE. No Gist activation. Native C3 final-answer Run186 remains a distinct preregistered experiment and must be evaluated independently.
