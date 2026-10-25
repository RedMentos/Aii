# Run160 local 32 MiB follow-up test correction

After increasing the bounded prefix from 8 to 32 MiB, the original synthetic `test_oversized_metadata_rejected` still used a 9 MiB length. It failed (7 PASS, 1 FAIL) because 9 MiB is now within the allowed declared string bound, but its data is truncated, producing `ValueError: truncated_or_oversize` instead of expected `string_bounds`.

The fixture was updated to 33 MiB to test the **new** 32 MiB maximum. Final local 8/8 PASS, compileall PASS. Source Git blob `c321c58864303f5d44afc1a542d27a65d0d15854`, test blob `5d14e3a41a36cb2c107ad8b4ea14da41b8f5fa32`. Original failed test remains documented; no native inference, no gate promotion.
