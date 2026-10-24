# Run97 — JEF broadcast cache source lineage before ACTIVE Body bridge

Base Run96 PR #128 `cbccef71864a4b3dbfdc7ec52e1910b679688733`. Run94 World Model remains separately owned and untouched.

Owner: `v13/code/v13/jefbridge.py` only `JEFBridge.bridge_view`; new `tests/test_jef_cache_lineage_run97.py`, isolated workflow `.github/workflows/v13-run97-jef.yml`, this proof. No shared handoff/canon edits.

Hypothesis: ACTIVE JEF→B1/B2 extra fields are selected from the latest `JEFBroadcastCache` packet using only `state_version`; deleted source refs, missing/changed parent `JEFBroadcastPacket`, forged generation/provenance or malformed JSON may be used or raise instead of failing closed.

Preregistered RED: six real SQLite mutations after explicitly human-authorized ACTIVE and a verified positive intact cache: deleted source, removed parent, wrong cache generation, forged source hash, wrong parent state version, malformed cache JSON. Every mutated view must return `({},[])` without exceptions. Existing SHADOW mode and learned field gating unchanged.

Narrow candidate after RED: verify packet event/generation/version, source refs by `read_source`, parent packet lineage and same exact refs/version, structural shape; refuse malformed payloads. This is local integrity against stale/corrupt data, not a cryptographic signature against a malicious DB writer. No native/Redmi/learning authority promotion.

Original gates STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, Z6a/Z8 FAIL, full V13 INCOMPLETE.
