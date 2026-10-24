# Run72 prereg — bounded public CI focused proofs

2026-10-24. Base Run71 PR104 8af0ac96765b84829eea6995d4ca5cc700ba12e5. Owner only `.github/workflows/v13-focused-proof.yml`, new Run72 docs/evidence. No production runtime or blueprint changes.

Goal: run actual full-checkout V13 imports/tests on a standard GitHub-hosted Linux runner because this local scratch environment cannot resolve GitHub DNS. Public repo standard runners are free per GitHub docs; never provision paid/larger runners. Workflow uses read-only contents, no secrets, no model download, bounded 10-minute timeout, concurrency cancellation, sparse checkout and pinned public Python dependencies. It does NOT promote any original gate.

Preregister test command: `cd v13/code && python -m unittest -v tests.test_jef_human_precedence_run68 tests.test_jef_outcome_lineage_run69 tests.test_world_action_chronology_run70 tests.test_world_observed_role_run71 tests.test_world_model_integration_run64 tests.test_world_align_finite_run65`. Optional official privacy scan only if base revision available; failure must remain visible. Save remote workflow run ID/conclusion if launched; if disabled, mark NOT RUN and continue local code packages.

Official references: https://docs.github.com/en/actions/concepts/billing-and-usage and https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
