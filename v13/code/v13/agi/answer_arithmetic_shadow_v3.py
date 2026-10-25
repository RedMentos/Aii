"""Run149: bounded terminal-format tolerance for source-bound AGE0d SHADOW.

Isolated candidate. Never delivers, edits, trains or promotes a gate. A final
blank line and a bold numeric result are formatting, not new evidence; text
inside the answer or calculator scratch chains still requires abstention.
"""
import re

AUTHORITY='SHADOW_ONLY'
QUESTION=re.compile(r'\s*(?:what\s+is|calculate|compute)\s+(?P<a>-?\d{1,6})\s+(?P<op>plus|minus|times|divided\s+by|[+\-*×÷/])\s+(?P<b>-?\d{1,6})\s*[?.]?\s*',re.I)
NUMBER=r'-?\d{1,12}'
BARE=re.compile(rf'\s*(?:the\s+answer\s+is\s+|result:\s*)?(?P<result>{NUMBER})\.?\s*',re.I)
ECHO=re.compile(rf'\s*(?P<a>-?\d{{1,6}})\s*(?P<op>[+\-*×÷/])\s*(?P<b>-?\d{{1,6}})\s*=\s*(?P<result>{NUMBER})\.?\s*')
BOLD_BARE=re.compile(rf'\s*\*\*(?P<result>{NUMBER})\*\*\s*')
BOLD_ECHO=re.compile(rf'\s*(?P<a>-?\d{{1,6}})\s*(?P<op>[+\-*×÷/])\s*(?P<b>-?\d{{1,6}})\s*=\s*\*\*(?P<result>{NUMBER})\*\*\s*')


def op_code(s):
    x=' '.join(s.lower().split())
    if x in ('plus','+'):return '+'
    if x in ('minus','-'):return '-'
    if x in ('times','*','×'):return '*'
    if x in ('divided by','/','÷'):return '/'
    return None


def evaluate(question,answer):
    base={'status':'ABSTAIN','reason':'unsupported_or_ambiguous',
          'authority':AUTHORITY,'may_deliver':False,'may_update':False}
    if not isinstance(question,str) or not isinstance(answer,str):return base
    if len(question)>2000 or len(answer)>256 or any(c in question+answer for c in '\x00\r\x0b\x0c\x85\u2028\u2029'):
        return base
    if '\n' in question:return base
    m=QUESTION.fullmatch(question)
    if m is None:return base
    a,b=int(m['a']),int(m['b']);op=op_code(m['op'])
    if op=='+':expected=a+b
    elif op=='-':expected=a-b
    elif op=='*':expected=a*b
    elif op=='/':
        if b==0 or a%b:return base
        expected=a//b
    else:return base
    if abs(expected)>10**12:return base
    # Only trailing/leading blank whitespace may contain newlines; never
    # normalize a multi-line narrative, chain-of-thought or conflicting claim.
    cleaned=answer.strip()
    if '\n' in cleaned:return base
    offset=len(answer)-len(answer.lstrip())
    n=BARE.fullmatch(cleaned) or BOLD_BARE.fullmatch(cleaned)
    kind='bare_or_sentence'
    if n is None:
        n=ECHO.fullmatch(cleaned) or BOLD_ECHO.fullmatch(cleaned)
        kind='exact_echo'
        if n is None or (int(n['a']),op_code(n['op']),int(n['b']))!=(a,op,b):return base
    claimed=int(n['result'])
    return {'status':'CORRECT' if claimed==expected else 'MISMATCH',
            'reason':'source_bound_integer_arithmetic', 'authority':AUTHORITY,
            'may_deliver':False,'may_update':False,
            'expected':str(expected),'claimed':str(claimed),'answer_kind':kind,
            'source_span':question[m.start('a'):m.end('b')],
            'answer_span':answer[offset+n.start('result'):offset+n.end('result')],
            'answer_offsets':[offset+n.start('result'),offset+n.end('result')],
            'terminal_blank_normalized':cleaned!=answer}
