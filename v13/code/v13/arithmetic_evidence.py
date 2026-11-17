"""Source-exact arithmetic evidence for C3; no tool execution or answer authority.

Only standalone, unambiguous small integer expressions are admitted. The
source remains the user's message; this is not a TOOL_CALL or Age permission.
"""
import re
from fractions import Fraction

QUESTION = re.compile(r"^\s*(?:(?:what is|what's|calculate|compute|solve)\s+)?([+-]?\d{1,6})\s*([+*×/-])\s*([+-]?\d{1,6})\s*(?:=|\?|\.)?\s*$", re.I)

def evidence(text):
    if not isinstance(text, str) or len(text)>80:
        return None
    m=QUESTION.fullmatch(text)
    if not m:
        return None
    a,op,b=int(m[1]),m[2],int(m[3])
    if op=='+': value=Fraction(a+b)
    elif op=='-': value=Fraction(a-b)
    elif op in ('*','×'): value=Fraction(a*b)
    elif b: value=Fraction(a,b)
    else: return None
    answer=str(value.numerator) if value.denominator==1 else str(value.numerator)+'/'+str(value.denominator)
    return {'source_expression':m[1]+' '+op+' '+m[3], 'exact_result':answer,
            'source':'CURRENT_USER_EXACT', 'authority':'DETERMINISTIC_EVIDENCE_NOT_TOOL',
            'scope':'standalone_integer_arithmetic_only'}
