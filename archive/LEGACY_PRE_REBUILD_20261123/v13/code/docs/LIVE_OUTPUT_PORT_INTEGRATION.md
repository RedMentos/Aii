# Existing C3 BodyPort integration handoff

The adjacent `scripts/live_output_adapter_port.py` implements the Python owner
of the existing compiled `native-prefill-session`. No production source was
changed. Ten focused tests use real child processes with explicitly nonnative
software fixtures; these are protocol/software tests, not model proofs.

Prepare the native worker using the existing `TESTEN_NATIVE_SESSION.sh` workflow
(or its existing preparation helper). `bind_installed(home)` then verifies the
pinned C3 model/revision and the prepared binary, worker sources, installation,
and every shared-library byte identity. It does no inference or compilation.

The future existing C3 runner supplies its already measured untrimmed context:

```python
from scripts.live_output_adapter_port import (
    bind_installed, PausedOutputSession, infer_live_head,
)

# Existing runner template/tokenize calls: no causal decode here. Token IDs
# must be the exact measured native template IDs; context must be <=512 tokens.
context = {
    'messages': messages, 'prompt': prompt, 'token_ids': exact_token_ids,
    'history_trimmed': False,
}
binding = bind_installed(home)
# Existing RunnerPool must unload its template/server body before this call.
with PausedOutputSession(binding, context, unique_work_folder, cancel,
                         absolute_turn_deadline) as session:
    observed = session.pause()
    # Artifact path/hash/ABI must come from the existing approved manifest.
    prediction = infer_live_head(observed, artifact_path, artifact_sha256,
                                 manifest_feature_abi)
    result = session.resume(prediction['first_token_bias'])
```

The port binds one READY handle to the same PID, source context, exact tokens,
model, library pins, and actual feature-file hash. It verifies the complete
65536-way finite native distribution and its relation to measured logits,
exposes the actual causal 1024D final normalized state, then consumes that one
handle exactly once. Final checks include the exact float32 first-position
delta, decoded sequence, loaded libraries, and zero additional prefill calls.
Cancel, absolute deadline, and actual sampled RSS remain enforced; termination
reaps the process group. Unknown memory stays unknown. A failed pause/resume
must not invoke another prefill as a fallback.

`c3-native-first-token-delta-v2` artifacts are intentionally incompatible with
this causal batch128 feature ABI. New heads must explicitly use
`c3-live-prefill-first-token-delta-v1`, contain a scalar canonical JSON
`feature_abi`, and retain the existing token_ids/weights/anchors/temperature/
max_bias/support_cosine/feature_offset/feature_scale arrays. The delta math is
the existing normalization/support/first-token external-row calculation. No
old checkpoint conversion, approval, activation, or model parameter update is
performed. Matching hashes/ABI alone is not human approval.

After the frozen STEP2 run, root may integrate this into the existing C3 runner
and learner boundary while preserving existing source capture, C5 output
ownership, artifact lineage, review, rollback, and one-body residency. The
new output-context revision must include the live feature ABI and executable
identity; existing separate-prefill head context revisions cannot be reused.

The current native worker deliberately emits four decoded tokens: one resumed
first token plus three unbiased continuations. Consequently this prepared port
does not yet replace the production streaming decoder or its full answer-token
budget. That worker extension and actual target-device/native integration tests
remain necessary before promotion. No speed, semantic quality, full-runner,
or phone proof is claimed by these software tests.
