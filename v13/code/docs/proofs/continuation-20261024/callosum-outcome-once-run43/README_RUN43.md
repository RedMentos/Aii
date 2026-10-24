# Run43 — Callosum B3-H9 exactly-once outcome credit (isolated)

**Source review:** At base `9615e55e2450f02aa92e152769fb63ed66a4a204`, `v13/code/v13/callosum.py:Callosum.outcome` reads `pending[event_id]`, computes utility for available receiver offers, applies `_update` to all scored messages, and marks **all** pending messages `scored=True`. It does not check this flag on repeat calls. A repeated completion can double-credit the same message, and a message without a receiver offer is marked despite no credit. Existing `tests/test_callosum.py` checks one outcome call only. This is a source-level risk with synthetic demonstration, not a native runtime reproduction.

**Candidate:** Pure `credit_once(state,event_id,observations,update)` must run **inside** the existing `Callosum._mutate` optimistic state update, so checking and marking are one CAS-protected transition. It binds event/message ID, direction, channel, receiver, finite utility and component parts; refuses duplicate pending IDs and repeated/stale observations. Only credited entries receive `scored=True`. An unobserved message remains eligible for later scoring. The actual `Callosum.outcome` must compute and pass verified OfferPacket observations, use the **applied** count for return and neuromod.touch, and preserve the original utility formula and `on_rating` behavior. No Age/latent/action authority.

**Tests:** First synthetic suite: 13/14 PASS, one test-harness error (observation constructed after corrupting pending state); original log preserved. After correcting the test, **14/14 PASS** and compileall PASS. The source-shaped legacy double-credit simulation produced two updates from two identical calls. No full checkout, native model, Redmi, or production integration was performed.

**Raw evidence:** `evidence/run43-raw-evidence.tar.xz.b64`, SHA256 of decoded tar.xz `1fd2f44f275d8ecf32144482d3e4bafb2e7043c34d1f856952dbb113c6ba1d72`. Source Git blob `9518a7127af5928b39a3fbab2d58b71597eaa737`; test blob `d231c7962d311c4a2409773c7302494903241b52`.

**Open:** Independent full-checkout review; real Store/CAS/restart integration and concurrent completion tests; official privacy scanner; retained existing Callosum utility and rating tests. Original gates unchanged: STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.

**Next exact command:** `python -m unittest discover -s v13/code/docs/proofs/continuation-20261024/callosum-outcome-once-run43/tests -v`, then add `Runtime` test calling `Callosum.outcome` twice on the same MessagePacket/OfferPacket and verifying utility `n` increments exactly once; integrate only after independent review.

**Ownership:** Codex Run43 only this new folder. Production `callosum.py`, JEF Run41, Sleep Run42, all canonical and preregistered files untouched.
