"""Run23/Run27 actual Store EventEnvelope -> German typed STEP2 SHADOW bridge.

The source reader verifies existing persisted user event refs. The fixed
German recipe sees only source text, never the oracle, model output or answer.
This is read-only deterministic software; it has no Runtime/learning authority.
"""
import re

from scripts import run17_german_typed_shadow as german
from scripts import run21_event_source_adapter_shadow as adapter

REVISION = "run27-real-store-german-typed-bridge-shadow-v1"
VERIFICATION_SCOPE = "EVENT_SOURCE_INTEGRITY_ONLY"


class Refusal(ValueError):
    pass


def evaluate(store, session, project, refs, temporal_mode, option_role):
    """Return an untrusted candidate from three existing Store user event IDs.

    The caller must independently authorize any eventual use; neither an
    EventEnvelope nor a content hash is a HumanDecision/F5 rule authority.
    """
    if (not isinstance(project, str) or
            re.fullmatch(r"[A-Za-z]+", project) is None or
            not isinstance(session, str) or not session or
            not isinstance(refs, dict) or set(refs) != {"old", "sheet", "current"} or
            any(not isinstance(x, str) or not x for x in refs.values()) or
            len(set(refs.values())) != 3 or
            temporal_mode not in {"RETAIN_PRIOR_RULES", "REVISED_CURRENT_RULES"} or
            option_role not in {"sheet", "current"}):
        raise Refusal("invalid_store_source_contract")
    if temporal_mode == "REVISED_CURRENT_RULES" and option_role != "sheet":
        raise Refusal("revised_options_must_be_historical_sheet")
    try:
        reader = adapter.EventSourceReader(store, session, project, refs)
        # The option source is either the latest supplier sheet or the current
        # exact text. Even when not used for options, the sheet remains a
        # registered, live, temporally ordered input and is revalidated.
        before = {role: reader(ref)["sha256"] for role, ref in refs.items()}
        options_ref = refs[option_role]
        result = german.evaluate(
            project, refs["current"], refs["old"], options_ref,
            temporal_mode, reader)
        if (result.get("authority") is not False or
                result.get("status") != "SHADOW_ONLY" or
                result.get("action") not in {"A", "B", "NONE"} or
                result.get("source_hashes") != {
                    "current": before["current"],
                    "old": before["old"],
                    "options": before[option_role]}):
            raise Refusal("typed_candidate_source_contract")
        for role in ("old", "sheet", "current"):
            reader.revalidate(refs[role], before[role])
    except Refusal:
        raise
    except (adapter.Refusal, german.Refusal) as exc:
        raise Refusal("source_or_typed_reader_refused") from exc
    return {"revision": REVISION, "status": "SHADOW_ONLY",
            "authority": False, "verification_scope": VERIFICATION_SCOPE,
            "action": result["action"], "options": result["options"],
            "rules": result["rules"], "project": project,
            "temporal_mode": temporal_mode, "option_role": option_role,
            "source_refs": dict(refs),
            "source_hashes": dict(result["source_hashes"]),
            "all_three_source_hashes": before,
            "native_executed": False, "model_output_used": False,
            "f5_decision_authority": False, "jepa_weight": 0,
            "canonical_gate_pass": False}
