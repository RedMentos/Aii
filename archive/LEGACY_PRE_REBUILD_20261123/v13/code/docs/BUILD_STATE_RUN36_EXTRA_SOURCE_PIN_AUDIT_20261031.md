# Run36 extra frozen-source audit — independent of in-flight native job

Owner GPT-6 scheduled continuation, 2026-10-31 UTC. Checked exact native launch source HEAD `d421badbc5adde9707ad37ea8f219fa0483bf01a` against original Run27 native workflow's full source pins. Besides the Run36 native workflow's explicit prereg/collector/finite-helper/original-solver/Canon pins, the following original Run27 dependency blobs were independently fetched from **that exact launch HEAD** and matched byte-for-byte to the original Run27 registered pins:

- `scripts/run25_ag12_bodies_native.py` `cec8b7ec36066ee74c2ff1a3684c7517160cef3a`
- `scripts/run24_ag12_german_c3_native.py` `b781461e8fae5de9a519a0216d4d9a6a773eb498`
- `specs/models.json` `7af05962af41d0bc3f7dd18ef01d4eba55eabf99`
- `v13/models.py` `bd035cf8029850cce00b179edf533e53bf24358a`
- `v13/bootstrap.py` `dc23e192bcd01589475692666ebb6568c80d078b`
- `v13/agi/generality.py` `a1cab60363814cb86472a42defb5089d4cdbd432`

All six **MATCH**; no changed source/model/seed specification was silently substituted. This is an independent GitHub remote byte/hash inspection, **not** a native result or a substitute for terminal raw. The in-flight Actions `41149111278` source HEAD remains frozen; this note does not trigger/restart the native workflow. Do not promote any gate. Original Run27 artifact `13019429115` inspected read-only: DE/EN final rows contain only `id,correct,confidence`, confirming original absence of per-role token-confidence metrics. Its native status was DONE, 528 role calls, 176 rows, runtime/process reaped, no events/messages; this is historical evidence, not Run36.

Next: wait for Run36 terminal, independently verify original raw and source pins, private byte-verified backup, report invalid/missing confidence incidence and same-output changes without learning claim. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 NO_PROMOTION; Body-JEPA UNAVAILABLE; jepa_weight=0; World-JEPA SHADOW; no Redmi or whole V13 completion.
