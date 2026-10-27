# BP1 QAD GGUF server ownership preflight — scoped prospective counterexample

2026-10-27; reviewer branch `codex/automation11-bp1-qad-review-20261027`, parent PR #682, same source/model/seed/prompt cohort.

Risk found by source review: `gguf()` launches a server on fixed localhost port 8834 and polls `/health`, but does not first prove the port was free. If another server already owns that port, a response from the unrelated process could be accepted as the pinned QAD server, giving false model-source attribution.

Test plan before fix: bind an owned test socket to an ephemeral local loopback port; calling a new `assert_loopback_port_available(port)` must reject it. Release the test socket; the check must accept the now-free port. No external networking. Then add the preflight immediately before `Popen`. This closes the pre-existing-listener case, not the remaining release-to-bind race; do not claim strict process ownership or native execution. No changes to native heavy runner, port 8834, model hashes, inference protocol or registered cohort.

Evidence level software-only. Negative gates and production state unchanged.