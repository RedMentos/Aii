# Run155 preregistered independent raw-log binding review

Base: `50e86580bea78a13a9c2aceb97ea3c1970c16796` (Run154). Owner: Codex Run155; owns only new `run155` script, tests, proof and CI. Do not edit frozen Runtime, Run151/153/154 code, original native artifacts or source hashes.

## Failure hypothesis
Run154 checks the count of lines prefixed `RUN151_ROW` but does not bind their row IDs, order, status or label to the report. A 288-line repeated or reordered log could pass that local log-count guard when its caller supplies the corresponding ZIP SHA. Original pinned native artifacts remain unchanged and are not alleged to be corrupted.

## Tests (software/synthetic, no native run)
Construct 288 synthetic report rows and logs; verify exact binding, reversed/repeated lines, status forgery, malformed statuses, missing rows, wrong report order, wrong ZIP digest, promoted STEP2 and unavailable provenance verifier. The review must call the existing Run154 `load` to retain all registered task/model/runner/response checks. Never accept self-hashed synthetic evidence as native proof.

## Claim boundary
No model inference, no Linux-native/Redmi proof, no human adjudication. Gates remain STEP2 UTILITY_FAIL; B3_L1 FAIL; Body_JEPA UNAVAILABLE; jepa_weight 0; DS2_H2 FAIL; V13 INCOMPLETE. The review is an optional read-only audit, not a change to Run154.
