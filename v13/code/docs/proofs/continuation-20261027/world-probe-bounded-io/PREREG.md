# World-JEPA SHADOW bounded local file reads — preregistration (2026-10-27)

Base: PR #654 exact `d466aa121810041ad5bcee3034eee17f1d676cf4` (review-only child, not main). Ownership: `v13/code/v13/world_jepa_shadow_probe.py`, `v13/code/v13/world_jepa_slots.py`, a new isolated regression test and workflow. No other runtime, learned weights, source cohorts, model/seed hashes, age or permissions are changed.

## Defect and proposed behavior
`_json_file` and `SlotWorldJEPA.load` currently call `Path.read_bytes()` **before** enforcing their existing 2 MiB/8 KiB/32 MiB limits. A caller-supplied oversized local file can therefore allocate unbounded bytes on the 6 GB-class Redmi even though the later size guard rejects it. This is a mobile resource integrity bug, not World-JEPA utility.

Require bounded reads of at most `max_bytes+1` bytes per file, then reject empty/oversized inputs before JSON decoding or checkpoint ZIP parsing. Keep all existing caps and digest/provenance checks unchanged; no streaming ZIP implementation and no authority promotion. Both explicit operator and offline CLI paths benefit from the same loader.

## RED/GREEN acceptance
1. Oversized JSON request (2 MiB+1), oversized provenance (8 KiB+1), and oversized checkpoint (32 MiB+1) reject with ValueError **without calling Path.read_bytes**.
2. Small valid JSON and small malformed checkpoint still use the same semantics; existing operator and checkpoint tests remain passing.
3. CI records exact source HEAD, source SHA256, original raw unit/compile/privacy outputs, exit codes and an immutable artifact. Preserve failing RED before source change, then run GREEN on the same branch.
4. Explicitly no claims of native/Redmi measurements, model quality, automatic World-JEPA observer, STEP2/B3/Body-JEPA/age/approval changes. No original Z12c cohort rerun.

Exact test: `cd v13/code && PYTHONPATH="$PWD:$PWD/scripts" python -m unittest -v tests.test_world_probe_bounded_io tests.test_world_console_shadow tests.test_world_jepa_shadow_probe tests.test_world_jepa_slots_checkpoint`.
