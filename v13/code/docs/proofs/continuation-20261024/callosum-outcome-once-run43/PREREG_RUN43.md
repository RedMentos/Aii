# Run43 preregistration — Callosum B3-H9 outcome exactly-once credit (isolated)

Base Run42 `9615e55e2450f02aa92e152769fb63ed66a4a204`; independent file ownership only `v13/code/docs/proofs/continuation-20261024/callosum-outcome-once-run43/`. Do not modify Run41 JEF, Run42 Sleep, frozen production Callosum, or original gates.

Read-only source review: `v13/code/v13/callosum.py:Callosum.outcome` scores all pending messages each call, then marks every pending record `scored=True` without first checking that flag. A repeated/restarted completion may count identical channel utility twice; messages without a receiver offer are also prematurely marked. `test_callosum.py` checks one call only. This is a code-path risk, not yet a native reproduced exploit.

Implement a separate pure state-transition candidate that credits only unique, still-unscored message IDs with a verified receiver outcome. Mark only actually credited entries, atomically in the same state mutation. Reject mismatched direction/channel/receiver identity. Tests predeclared: first credit once; same evidence replay zero; stale snapshot zero; duplicate msg IDs zero; unobserved message remains unscored and can be credited later; no pending state no-op; unrelated event isolated; mismatched metadata no-op; no Age/action/latent authority. Preserve initial failures. Software/synthetic only, full runtime integration and independent review required.

Original gates: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, V13 INCOMPLETE.
