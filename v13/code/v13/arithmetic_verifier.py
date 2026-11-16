"""Read-only arithmetic answer checks for V13 C5 shadow evidence.

No tool activation, model authority or user-output rewrite. Only evaluate an
already computed trusted result against the final text. Exact equation checks
take precedence over incidental matching digits elsewhere in an answer.
"""
import re
from decimal import Decimal, InvalidOperation

_NUMBER = r"(?<![\\w.])[-+]?(?:\\d+(?:,\\d{3})*|\\d+)(?:\\.\\d+)?(?![\\w.])"

def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        x = Decimal(str(value).replace(",", ""))
        return x if x.is_finite() else None
    except (InvalidOperation, ValueError):
        return None

def arithmetic_agreement(expression, expected, answer):
    """Return True/False/None (ambiguous), never assert a factual answer.

    For an explicit equation repeating the exact source expression, its RHS
    controls agreement. A bare occurrence of the expected number is weaker
    evidence; contradictory equations prevent a positive shadow score.
    """
    if not isinstance(expression, str) or len(expression) > 120:
        return None
    target = _decimal(expected)
    if target is None:
        return None
    text = str(answer)[:4000]
    compact = re.sub(r"\\s+", "", expression)
    if not re.fullmatch(r"[0-9.,+*/()% -]+", compact):
        return None
    normalized = re.sub(r"\\s+", "", text).replace("×", "*").replace("÷", "/")
    # The LHS is source-bound, not arbitrary generated arithmetic.
    eq = re.compile(re.escape(compact) + r"=(?P<rhs>[-+]?(?:\\d+(?:,\\d{3})*|\\d+)(?:\\.\\d+)?)")
    values = [_decimal(m.group("rhs")) for m in eq.finditer(normalized)]
    if values:
        return all(v == target for v in values)
    # A different explicit arithmetic equation is not a reliable agreement
    # signal, even if the right number happens to appear in the response.
    if re.search(r"\\d\\s*[+*/-]\\s*\\d\\s*=", text):
        return None
    matches = [_decimal(m.group()) for m in re.finditer(_NUMBER, text)]
    if target in matches and not any(v is not None and v != target for v in matches):
        return True
    return False if matches else None
