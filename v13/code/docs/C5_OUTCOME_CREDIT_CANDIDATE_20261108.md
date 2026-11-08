# C5: unverified completion and absent outcome (candidate only)

Base: `codex/resume-20261106` commit `5e964146579deb22c5ba89a2a03a52a9e4d8aab8`.
This is an isolated software candidate, not integrated into the runtime, a
change in Age permissions, a measured model gain, or a Redmi result. Original
source files, registrations and negative gates remain untouched.

## Observation

The existing `runtime.py` passes `task_success=1` for `status == FINAL` to
`C5Learning.learn`. FINAL says the turn finished; it does not say its answer
was correct. The actual Runtime regression yields the deliberately incorrect
`2 + 2 = 5`, receives FINAL, and records `task_success=1`.

`Neuromod.signal` must populate numeric legacy `ModulatorPacket` fields. It
fills an omitted `task_success` with 0 while separately recording the channels
actually supplied. `channels_from` currently falls back to that mandatory 0
even for an explicitly typed cost-only packet. `_modulator` then updates
`r_hat` and produces a negative outcome delta despite no outcome being given.

## Bounded candidate

`scripts/c5_outcome_credit_candidate.py` checks the SHA-256 hashes of both
edited sources and the two legacy producers, plus exact single anchors,
returning changed bytes only for a separate copy. It does not replace imports
or modify the source files. In the copy:

1. C5 receives measured cost, action prediction error, rule violation and world
   mismatch, but no inferred semantic `task_success` merely from FINAL. FINAL,
   action status and ExperienceRecord remain as before.
2. Typed channels take precedence; an explicit typed `task_success=0` remains
   a negative outcome. For current N10 packets, mirrored legacy defaults with
   no typed field are not treated as outcomes. Other mixed packets retain the
   legacy fallback. Three source-bound legacy producers with known no-reward
   placeholders are handled separately, including their documented cost fields.

The actual Runtime test uses only a fake generation/route seam. It exercises
the actual submit, persistence, action selection, C5, Neuromod and human-rating
paths. It verifies the current failure and the candidate on identical inputs,
negative and positive explicit feedback, explicit positive/negative outcome,
legacy compatibility, unchanged technical status and source mismatch refusal.

## Producer/consumer audit and limitations

- Runtime is the completion-derived C5 producer. Explicit user ratings follow
  `inputs.record_rating` → `actionlearn.on_rating` and remain separate positive
  `human_approval` or negative `human_correction` values.
- `attention`, `context_os`, `callosum`, `deliberation`, and `jefbridge` send
  explicit utility values to `Neuromod.signal`; JEF and attention may use
  internal estimates, not verified semantic truth. The candidate does not
  promote those signals to human evidence. `ablation99` is synthetic.
- `world.py` and two calls in `learning.py` create old-format packets with a
  required zero and explicit `values_status` saying it is not a reward. The
  candidate recognizes those exact existing formats; unknown legacy producers
  retain original interpretation and require individual audit.
- C5 consumes `task_success` as an action-score input; Neuromod consumes it as
  an instrumental channel, confirming signal, and reward-prediction delta.
  Detailed use also feeds gate/modulator reports. No schema field is removed.
- This does **not** clean existing C5 aggregates: historical unverified
  `task_success` remains stored and can still affect a C5 shift. The test
  explicitly reproduces this. Source-aware state migration or quarantine and
  an ACTIVE-mode guard are prerequisites before any integration.
- A path's most recent delta can belong to an earlier event. A subsequent
  cost-only event no longer fabricates a delta but does not erase the old one;
  any future worker must bind deltas to the matching event and valid outcome.
- Independent review reproduced two additional pre-existing hazards: repeated
  ratings replace the stored latest rating but are each applied to the C5
  moving averages, so a corrected rating can leave stale credit and a single
  turn can reach `MIN_N`. Also, a `dream`-sourced `task_success` currently
  changes `r_hat` and stores a delta even though its combined gate is zero;
  a later real outcome can inherit that altered expectation. Neither is fixed
  by this candidate. Audit sources, deduplication and reward-state provenance
  before attaching any worker or enabling the candidate.
- The hash guard now also binds the inspected `world.py` and `learning.py`
  producers. It does not prove that every historical packet was created by
  those exact versions. An old N10 legacy zero without an explicit typed field
  can remain ambiguous; raw historical records must not be silently rewritten.
- The candidate removes the inferred `task_success` for every completion
  status, including `ERROR`, `DEADLINE` and `CANCELLED`. Technical failures
  need a separate, typed outcome and must not be presented as a semantic
  correctness label. Other telemetry remains, but this candidate does not
  yet add the corresponding technical-failure learning path.
- Existing `Neuromod` persisted state may already contain misleading `r_hat`
  or delta values. Reprocessing history needs an independently reviewed,
  restart-safe migration that preserves original records and avoids double
  counting. The candidate changes neither persisted state nor provenance.
- This is no substitute for an independently sourced correctness label, a
  verified native learning path, regression/retention testing, or a phone run.

Local verification from `v13/code`:

```
PYTHONPATH=.:tests python -m unittest -v test_c5_outcome_credit_candidate
```

Additionally run the adjacent C5, Neuromod, local-update and homeostasis suites
against a separate materialized candidate copy, with the copy ahead of the
original on `PYTHONPATH`. Keep the frozen-original results and candidate results
distinct. The baseline unmodified Runtime and source bindings must stay intact.
