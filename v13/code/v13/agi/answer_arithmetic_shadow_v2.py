"""Opt-in source-bound arithmetic answer-visible SHADOW candidate (Run146).

No runtime consumer, no delivery or learning authority. Strict single-operation
integer scope; no model-based parsing, no silent extraction from free text.
"""
import re

AUTHORITY = 'SHADOW_ONLY'
QUESTION = re.compile(r'\s*(?:what\s+is|calculate|compute)\s+(?P<a>-?\d{1,6})\s+(?P<op>plus|minus|times|divided\s+by|[+\-*×÷/])\s+(?P<b>-?\d{1,6})\s*[?.]?\s*',re.I)
BARE = re.compile(r'\s*(?P<result>-?\d{1,12})\.?\s*')
SENTENCE = re.compile(r'\s*(?:the\s+answer\s+is|result\s*:)\s*(?P<result>-?\d{1,12})\.?\s*',re.I)
ECHO = re.compile(r'\s*(?P<a>-?\d{1,6})\s*(?P<op>[+\-*×÷/])\s*(?P<b>-?\d{1,6})\s*=\s*(?P<result>-?\d{1,12})\.?\s*')


def operator(text):
    t=' '.join(text.lower().split())
    if t in ('plus','+'):return '+'
    if t in ('minus','-'):return '-'
    if t in ('times','*','×'):return '*'
    if t in ('divided by','/','÷'):return '/'
    return None


def evaluate(question,answer):
    base={'status':'ABSTAIN','reason':'unsupported_or_ambiguous',
          'authority':AUTHORITY,'may_deliver':False,'may_update':False}
    if not isinstance(question,str) or not isinstance(answer,str):return base
    if len(question)>2000 or len(answer)>256 or any(c in question+answer for c in '\n\r\x00'):
        return base
    m=QUESTION.fullmatch(question)
    if not m:return base
    a,b=int(m['a']),int(m['b']);op=operator(m['op'])
    if op=='+':truth=a+b
    elif op=='-':truth=a-b
    elif op=='*':truth=a*b
    elif op=='/':
        if b==0 or a%b:return base
        truth=a//b
    else:return base
    if abs(truth)>10**12:return base
    n=BARE.fullmatch(answer) or SENTENCE.fullmatch(answer)
    kind='bare_or_sentence'
    if n is None:
        n=ECHO.fullmatch(answer)
        kind='exact_echo'
        if n is None or (int(n['a']),operator(n['op']),int(n['b']))!=(a,op,b):
            return base
    claimed=int(n['result'])
    return {'status':'CORRECT' if claimed==truth else 'MISMATCH',
            'reason':'source_bound_integer_arithmetic','authority':AUTHORITY,
            'may_deliver':False,'may_update':False,'expected':str(truth),
            'claimed':str(claimed),'answer_kind':kind,
            'source_span':question[m.start('a'):m.end('b')],
            'answer_span':answer[n.start('result'):n.end('result')]}
