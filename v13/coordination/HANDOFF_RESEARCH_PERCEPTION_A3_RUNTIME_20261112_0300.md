# Perception handoff — 2026-11-12 03:00 Europe/Berlin

## Scope and verified base
Branch based on research-perception/a3-provenance-20261112-0200 (PR #1813). Read A3Projector, A3EvidenceBridge and its tests from that branch. Team-plan and Android capability ledger are in coordination PR #1668 but were not available at this base ref; do not claim reviewed full Canon. Previous Audio CI #1806 reported success in earlier run, not rerun here.

## New code
- v13/code/v13/a3_runtime_adapter.py: independent source verifier, feature-only inference, A5-like synthetic percept and B1/B2/JEF non-authoritative observation views. No teacher target required for inference; digest, modality, finality, revocation gate.
- v13/code/tests/test_a3_runtime_adapter.py: checkpoint restart, no target leakage, revoked source, provisional/tampered/invalid data, mandatory verifier.

## Honest verification
GitHub create-file commits succeeded. Local checkout could not resolve github.com DNS; no test run and no CI PASS claimed for this new branch. New module does NOT implement canonical A5 schema or production B/C model invocations; do not merge as full runtime integration. Android microphone, native screen/UI observation, permissioned actions, full duplex, trained vocoder, A3 quantized export and Redmi hardware validation remain OFF/UNVERIFIED.

## Next
1. Run PYTHONPATH=v13/code python -m unittest discover -s v13/code/tests -p 'test_a3_runtime_adapter.py' -v on checkout/CI.
2. Reconcile canonical A5 schema and B/C consumer contracts with Core; replace synthetic views with actual runtime calls.
3. Test teacher-source provenance and consent against persistent source registry and revoke-on-replay.
4. Preserve user-directed active learning and Android OS permission boundary; never promote observation to action authorization.
