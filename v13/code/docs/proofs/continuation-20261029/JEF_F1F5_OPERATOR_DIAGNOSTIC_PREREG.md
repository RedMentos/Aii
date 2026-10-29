# JEF F1/F5 explicit operator SHADOW diagnostic — prospective prereg (2026-10-29)

Owner: GPT-6 isolated child of #1082 exact head `86043068fda99efca34db252745cf275c96bd9bb`. This prereg precedes operator changes and tests. #1082 proved real F1/F5 source admission with zero model calls but is not operator-usable.

## Narrow authorized operator-only integration

Add one **explicit, local-TTY-only** read-only operator command `:jefsource <Event-ID> <PolicyMemory-ID> <SheetMemory-ID>`. It must not be invoked by a model, tool result, network request, implicit chat turn, or background loop. `Operator.run` already rejects non-`OPERATOR_TTY` origins; additionally require Age0 `system_stage=0`, `learning_mode=RECORD_ONLY`, `latents_enabled=false`, `jepa_weight=0` and `r.require_idle()` before any source access. Validate exact ID grammar and argument count; fetch the named authoritative event from the active session and its original packet SourceRef; call the previously verified `jef_f1f5_source_admission.decide` on the two explicit active memory IDs.

Return a structured diagnostic **SHADOW_NO_AUTHORITY** JSON with `suggested_action`, provenance hashes and `no_live_answer=true`, `operator_diagnostic=true`, `native_calls=0`, `model_called=false`, `weight_updates=false`. Do not call `Runtime.submit`, model runners, tools, Store mutation, Memory.feedback, AG6 or any output broker. Do not change ordinary chat routing, existing commands, or implicit response behavior. Update `:help` with one line making the diagnostic-only scope clear.

## Tests and proof limits

Test actual fresh Runtime/Store, real explicit F1/F5 feedback, full source and negative cases, restart, revoked memory, foreign session, invalid IDs, non-TTY origin, nonidle and non-Age0 refusal. Assert no model calls, no new source/feedback/event/packet rows from the command, and unchanged weight/age/approval gates. Source-only CI with raw, source hashes, privacy scan and full V13 software regression. No 72 frozen P2X validation IDs or P0X holdout for tuning.

This command is a **user-requested diagnostic readout**, not live C3/JEF answer authority and not proof of native receiver utility. No automatic execution or permission escalation. Age0 RECORD_ONLY; STEP2 UTILITY_FAIL; B3 L1 FAIL; Body-JEPA UNAVAILABLE; LP3 FAIL; jepa_weight0; AG6 unapproved; Redmi unmeasured; V13 INCOMPLETE. Remaining platform budget UNKNOWN.
