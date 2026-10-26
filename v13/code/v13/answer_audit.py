"""WP-AGE0d: strict source-bound explicit arithmetic in a committed answer.

No inference, no source truth extrapolation, no delivery. A source-ref is
validated by Store.read_source before its text reaches audit(). A successful
calculation check is not a semantic truth or native-model proof.
"""
from decimal import Decimal
import re

NUMBER = r"-?(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,6})?"
EXPLICIT = re.compile(
    rf"(?m)^CALC:[ \t]*({NUMBER})[ \t]+([+*\-])[ \t]+"
    rf"({NUMBER})[ \t]*=[ \t]*({NUMBER})[ \t]*$"
)
MAX_ANSWER_CHARS = 8192
MAX_SOURCE_CHARS = 16384
MAX_EQUATIONS = 3


def numeric_token(source, value):
    return bool(re.search(r"(?<![A-Za-z0-9.])" + re.escape(value) +
                          r"(?![A-Za-z0-9.])", source))


def audit(answer, sources):
    """Return an abstaining structured diagnostic, never a correction message."""
    if type(answer) is not str or type(sources) is not list or not all(
            type(s) is str for s in sources):
        return {"status": "ABSTAIN_INVALID_INPUT", "equations_checked": 0,
                "mismatches": []}
    if len(answer) > MAX_ANSWER_CHARS or any(
            len(s) > MAX_SOURCE_CHARS for s in sources):
        return {"status": "ABSTAIN_LIMIT", "equations_checked": 0,
                "mismatches": []}
    matches = list(EXPLICIT.finditer(answer))
    if not matches:
        return {"status": "ABSTAIN_NO_EXPLICIT_CALC", "equations_checked": 0,
                "mismatches": []}
    if len(matches) > MAX_EQUATIONS:
        return {"status": "ABSTAIN_LIMIT", "equations_checked": 0,
                "mismatches": []}
    if not sources:
        return {"status": "ABSTAIN_NO_VERIFIED_SOURCE", "equations_checked": 0,
                "mismatches": []}
    mismatches = []
    for match in matches:
        left, op, right, claimed = match.groups()
        if not any(numeric_token(source, left) for source in sources) or not any(
                numeric_token(source, right) for source in sources):
            return {"status": "ABSTAIN_UNBOUND_OPERANDS",
                    "equations_checked": 0, "mismatches": []}
        a, b, c = Decimal(left), Decimal(right), Decimal(claimed)
        expected = a + b if op == "+" else a - b if op == "-" else a * b
        if expected != c:
            mismatches.append({
                "left": left, "operator": op, "right": right,
                "claimed": claimed, "expected": format(expected, "f"),
            })
    return {"status": "CONTRADICTION" if mismatches else "PASS",
            "equations_checked": len(matches), "mismatches": mismatches}
