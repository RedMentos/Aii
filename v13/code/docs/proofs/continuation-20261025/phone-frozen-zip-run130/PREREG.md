# Run130 — exact frozen-Runtime-safe phone source ZIP and extracted CLI proof

2026-10-25 UTC. Based on verified Run128 PR #159 commit ad3183796f9a06c7bea9c2e956a43c623e042dcb. Run129 full-suite audit owns separate workflow/proofs; Run127 owns installer quoting. Run130 owns ONLY new workflow/proofs and packaged source-only artifact. No source/Runtime/UI/model/Canon changes, no production merge.

Motivation: Run125 phone ZIP was built with Run124 frozen Runtime mutation; Run126 full suite found source-bound FAIL. Rebuild exact Run128 source ZIP preserving Runtime blob a691d27bd0772a4fa1f03d57ec90663237bf6825. Assert exact HEAD, canonical blueprint present, STOP preflight source + test present, no model/private data. Run 33 model-free phone/CLI/standstill tests both before and AFTER extracting the actual ZIP; check CRC, manifest and frozen runtime hash from extracted bytes. Publish SHA256/size, retain 30-day Actions artifact; independent download/readback. Do not claim Redmi, native, complete V13, or gate promotion.

STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; jepa_weight=0; DS2 H2 FAIL; V13 INCOMPLETE.