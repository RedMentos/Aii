# Run627 prereg — operator-visible query digest and exact-current phone source ZIP

2026-10-27 UTC. Parent Run626 PR621 head `86463deff919bae5867ed5ea4d83c9058fcbf467`. Exclusive files: `v13/code/v13/operator.py` HELP string, `v13/code/docs/BEFEHLE.md`, Run627 workflow/proof. Runtime Context OS/Sleep A implementation from Run626 is frozen and **not** to be edited here.

## Functional delivery and gates

1. Expose `:ctxos digest select recent|query` and `:ctxos digest on|off` in normal `:help` and command guide, clearly labeling query mode opt-in, lexical/source-validated, default recent and no model learning.
2. Package exact checkout via unchanged pinned `scripts/package_source.py` `06167e0bcb82b36cb08841cd31b9618c4ba0926e`, independently verify all source ZIP members using pinned `verify_phone_zip_current_run268.py` `880dbd2cebb0aac5c7b37e25a5ca8487b796cfa1`, no weights/private payloads.
3. Extract ZIP and execute real SQLite Runtime Run626 query-digest 6-case suite, Run624 multi-session fairness 4-case suite, Run623 operator config 5-case suite, source revocation/context and prompt tests; check launcher Bash syntax and command help. Existing packaging negative controls pass. Exact source hashes, raw logs, manifest and ZIP SHA preserved.
4. Preserve frozen Canon SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`, unchanged model/cohort/seed hashes and all negative gates. No Redmi/Termux native installation proof or trained JEPA claim.
5. Private Library byte-verified source artifact backup; review-only PR, no main merge.

After verified save, move to distinct native Body learning/utility work rather than iterating Context OS helpers without new evidence.
