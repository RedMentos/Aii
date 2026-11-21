"""Source-exact optional-context admission before native prefill.

A rough upper-bound estimate is not native tokenizer proof. A refused source
must be handled by the caller, never silently shortened.
"""
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class Envelope:
    admitted: bool
    prompt: str
    estimate: int
    omitted: tuple
    reason: str

def estimate(text):
    if not isinstance(text, str):
        raise TypeError("text")
    return (len(text.encode("utf-8")) + 1) // 2 + 1

def compose(source, context: Mapping[str, str], *, budget, reserve=32, prefix=""):
    """Preserve mandatory source byte-for-byte and admit whole optional fields.

    Caller validates each optional field's source lineage. Returned omitted
    labels must be logged as degraded cognition; this function never invents
    summaries, strips current user content or promotes hypotheses to facts.
    """
    if type(budget) is not int or budget < 1 or type(reserve) is not int or reserve < 1:
        raise ValueError("budget/reserve")
    if not isinstance(source, str) or not isinstance(prefix, str):
        raise TypeError("source/prefix")
    if not isinstance(context, Mapping):
        raise TypeError("context")
    if any(not isinstance(k, str) or not k.isidentifier() or
           not isinstance(v, str) for k, v in context.items()):
        raise ValueError("context field")
    labels = tuple(context)
    mandatory = prefix + source
    cap = budget - reserve
    if estimate(mandatory) > cap:
        return Envelope(False, "", estimate(mandatory), labels, "MANDATORY_TOO_LARGE")
    result = mandatory
    omitted = []
    for label, value in context.items():
        section = "\n[" + label + "]\n" + value
        if estimate(result + section) <= cap:
            result += section
        else:
            omitted.append(label)
    return Envelope(True, result, estimate(result), tuple(omitted),
                    "DEGRADED" if omitted else "FULL")
