# Run158 registered read-only paired native artifact audit

Base `b4b07b88a5c4753d17568ab60aa3039d6ba9f1cc` (Run155 review). Owner Run158: new CI workflow and proof only. Do not edit frozen Runtime, Run151/153/154/155 source, registered tasks/model/runner or negative gates.

Before CI, pin both immutable GitHub Actions artifacts: first run 40161320601 / artifact 12585869006, ZIP SHA-256 `0f19525d8e8abd62ca328ce752a0e8f8b619ca27ced71a42f3bd5c78d53edbe4`; second serialized unplanned run 40161328126 / artifact 12585869203, ZIP SHA-256 `fb0cc7d8370437a29d49fdbdabe5b8bbc32a5445ee3db55e295f701bfaec30da`. Both bytes were independently downloaded and hashed locally before this workflow. Local Run155 `bind_rows` checked 288 exact status rows on each; no model was executed.

CI plan: download original ZIP bytes using GitHub Actions read permission; assert both exact SHA-256 values; run existing Run155 full source/provenance/log audit on each; run Run154 paired comparison; retain JSON and original failures. Do not infer independent seed or deterministic repeat from serialized duplicate. If artifact access fails, record infrastructure failure rather than rerunning native inference or replacing source artifacts.

Evidence classification: **software audit of two prior Linux-native single-C3 runs**, not new native/Redmi/Body-JEPA or end-to-end V13. Gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight 0, DS2 H2 FAIL, V13 INCOMPLETE.
