# Run14A independent prior-chain CI raw audit (2026-10-30)

Read-only original GitHub Actions artifacts, not a rerun and not a native claim. Owner: GPT-6 hourly continuation. Source chain: Run13X #1315 and Run13Z #1317; original frozen Canon blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`.

| Scope | Original Actions run | Artifact | Original ZIP SHA256 | Inner SHA256SUMS | CRC | Exact stages |
|---|---:|---:|---|---|---|---|
| Run13X native-output **replay** (software verification of prior native rows) | 41100648167 | 12998542171 | `fcf3bbd80f27f901c1a864b1c8eaed2ec9868ea90a136d73771d6a020499ddab` | 21/21 PASS | PASS | PINS/FETCH/VENV/DEPS/TEST/REPORT/COMPILE/PRIVACY/DIFF all 0 |
| Run13Z AG9 synthetic heldout | 41101997334 | 12998232808 | `1b660a70c57b1d1fe9462c68da78ef2364341bed0a58797d30392c990dc1900e` | 12/12 PASS | PASS | PINS/TEST/COMPILE/PRIVACY/DIFF all 0 |

Original `TEST_RAW.log` confirms Run13X 26/26 software tests and Run13Z 11/11 software tests. Run13X report remains **conditional on missing original Store snapshot**: 16 original native rows are verified structurally, but 3/16 counterfactual C3 facts candidates, 13/16 JEF fallback candidates, synthetic receipt fields, and `native_receipt_attested=false`. Historical original `FIDELITY_HURT` is unchanged. Run13Z is synthetic source-ID disjoint only; it does not authenticate underlying source identity and grants no Age authority.

Private Library backup (not public GitHub): `/V13-Checkpoints/2026-10-30/Run14A-Independent-Review/`. Both original ZIPs were re-materialized and their SHA256 matched the downloaded original byte-for-byte. Independent JSON report local SHA256 `b9e0a49bef3cb5b5b9dd4d4c0a2d6de8a38757999d2b91f8001baa9c4a29e89e`, uploaded to same private folder (JSON readback not separately established).

This is **not** a full-suite, model inference, native rerun, Redmi or learning proof. STEP2 `UTILITY_FAIL`, B3 no promotion, Body-JEPA unavailable, `jepa_weight=0`, `learning_mode=RECORD_ONLY` and whole-system incomplete remain. Exact next: continue Run14A/14B independent review and new cross-organ full-suite without waiving historical RED.
