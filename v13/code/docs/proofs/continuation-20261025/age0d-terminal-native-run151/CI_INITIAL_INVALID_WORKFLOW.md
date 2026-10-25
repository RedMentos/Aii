# Run151 workflow validation failure (preserved)

GitHub Actions rejected the initial Run151 workflow before creating any jobs: push workflow runs `40161228793`, `40161238788`, `40161255343`, `40161257961` all had zero jobs and displayed the workflow path rather than the declared name. No model was downloaded or run. The initial workflow placed `RUN147_ARTIFACT: ${{ runner.temp }}/RUN147_native.zip` in **job-level** `env`; the `runner` context is not allowed at that scope. This was corrected in commit `446d548ef4baf9f4855f2a3a18e4ffde4e261710` to a fixed per-job Linux /tmp path. Preserve these failed runs as validation evidence, not as native results.

This is a CI configuration failure only; the corrected binding seed 15132 and prereg task/model/runner hashes remain unchanged. Native execution is allowed only after the corrected workflow passes privacy, tests, digest checks and resource preflight.
