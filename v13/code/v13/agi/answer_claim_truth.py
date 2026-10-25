"""Run143 independent source-bound numeric claim extraction for OFFLINE audit.

Unlike AGE0d checker this module does not calculate the expected answer; it
only extracts what the model explicitly claimed. Secondary post-hoc use only.
"""
import re
from decimal import Decimal, InvalidOperation

IN_NUM=r'[+-]?\d{1,9}(?:\.\d{1,4})?'
OUT_NUM=r'[+-]?\d{1,18}(?:\.\d{1,4})?'
OP=r'(?:\+|\-|−|plus|minus|times|\*|multiplied\s+by|divided\s+by|/)'
QUESTION=re.compile(rf'\s*(?:what\s+is|calculate|compute)\s+(?P<a>{IN_NUM})\s+(?P<op>{OP})\s+(?P<b>{IN_NUM})\s*[?.]?\s*',re.I)
# A separate operator regex accepts adjacent math symbols such as 24+48=72.
EQUATION=re.compile(rf'\s*(?P<a>{IN_NUM})\s*(?P<op>{OP})\s*(?P<b>{IN_NUM})\s*=\s*(?P<n>{OUT_NUM})\.?\s*',re.I)
BARE=re.compile(rf'\s*(?P<n>{OUT_NUM})\.?\s*',re.I)
SENTENCE=re.compile(rf'\s*(?:the\s+answer\s+is|it\s+is|result\s*:)\s*(?P<n>{OUT_NUM})\.?\s*',re.I)


def _op(s):
    t=' '.join(s.lower().split())
    if t in ('+','plus'):return '+'
    if t in ('-','−','minus'):return '-'
    if t in ('*','times','multiplied by'):return '*'
    if t in ('/','divided by'):return '/'
    return None


def _canonical(s):
    d=Decimal(s)
    return '0' if d==0 else format(d.normalize(),'f')


def claim_number(question,response):
    """Strict independent extraction, never evaluate truth or authorize output."""
    if not isinstance(question,str) or not isinstance(response,str):return None
    if len(question)>2000 or len(response)>256 or '\n' in question or '\n' in response or '\r' in question or '\r' in response:return None
    q=QUESTION.fullmatch(question)
    if q is None:return None
    m=BARE.fullmatch(response) or SENTENCE.fullmatch(response)
    if m is None:
        m=EQUATION.fullmatch(response)
        if m is None:return None
        try:
            if (_canonical(q.group('a')),_op(q.group('op')),_canonical(q.group('b'))) != (
                    _canonical(m.group('a')),_op(m.group('op')),_canonical(m.group('b'))):return None
        except InvalidOperation:return None
    try:return _canonical(m.group('n'))
    except InvalidOperation:return None


def rescore(rows):
    """POSTHOC only: original preregistered evaluation remains unchanged."""
    correct=wrong=unknown=supported=false_alarm=wrong_detected=0
    for row in rows:
        parsed=claim_number(row.get('question'),row.get('response'))
        if row.get('check') in ('CORRECT','MISMATCH'):supported+=1
        if parsed is None:unknown+=1
        elif parsed==row.get('truth'):
            correct+=1
            if row.get('check')=='MISMATCH':false_alarm+=1
        else:
            wrong+=1
            if row.get('check')=='MISMATCH':wrong_detected+=1
    return {'n':len(rows),'correct':correct,'wrong':wrong,'unknown':unknown,
            'supported':supported,'false_alarms':false_alarm,'wrong_detected':wrong_detected,
            'false_alarm_rate':None if not correct else false_alarm/correct,
            'wrong_detection_rate':None if not wrong else wrong_detected/wrong,
            'gate':'UNVERIFIED','claim_limit':'POSTHOC_SECONDARY_DIAGNOSTIC_ONLY'}
