# Candidate CI harness amendment 2026-10-27

First candidate Actions `40452087562` at `98502f737bb2cd9fa524a1035698cc27f6add073`: exact two-file conflict resolution succeeded and source SHA pins matched. Job then failed **before tests or commit** because global `git diff --cached --check` scanned thousands of inherited AG5 historical raw evidence logs with trailing whitespace. This is pre-existing immutable evidence, not a new conflict or reason to alter original raw logs. Original failure artifact preserved.

Narrow correction: run `git diff --cached --check -- v13/code/scripts/handy_pflicht.py v13/code/v13/operator.py` on the only manually resolved source files. Keep all historical raw logs byte-exact, and keep JSON/compile/privacy/focused/broad checks unchanged. Do not falsely label the first attempt a passing integration.
