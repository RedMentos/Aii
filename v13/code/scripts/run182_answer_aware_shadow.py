"""WP-AGE0d candidate: answer-aware exact-source contradiction, SHADOW ONLY.

This intentionally narrow recognizer checks explicit budgets and revised dates.
It never sends a message, edits an answer, learns or grants an Age right.
"""
from decimal import Decimal, InvalidOperation
import re

BUDGET_SOURCE = re.compile(r'\bapproved budget\b[^.!?\n]{0,120}?\bis\s+(\d+(?:[.,]\d+)?)\s+euros\b',re.I)
BUDGET_ANSWER = re.compile(r'\bbudget\b[^.!?\n]{0,60}?\b(?:is|:)\s*€?\s*(\d+(?:[.,]\d+)?)\s*(?:euros|€)?\b',re.I)
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'
DATE = r'((?:'+MONTHS+r')\s+\d{1,2})'
DEADLINE_SOURCE = re.compile(r'\bdeadline is moved from\s+'+DATE+r'\s+to\s+'+DATE+r'\b',re.I)
DEADLINE_ANSWER = re.compile(r'\b(?:current\s+)?deadline\b[^.!?\n]{0,40}?\b(?:is|:)\s*'+DATE+r'\b',re.I)


def _normal(kind,value):
    if kind=='budget':
        try:return format(Decimal(value.replace(',','.')).normalize(),'f')
        except InvalidOperation:return None
    return ' '.join(value.lower().split())


def check(question,answer,source,source_id='source'):
    """Return shadow evidence; abstain on ambiguous/missing/unsupported claims.

    Source offsets refer to the exact provided source string. No guessed quote.
    """
    base={'schema':'V13_AGE0D_ANSWER_AWARE_SHADOW_V1','status':'ABSTAIN',
          'shadow_only':True,'delivery_authorized':False,'learning_authorized':False,
          'age_reopen_authorized':False,'source_id':source_id}
    if not all(isinstance(x,str) for x in (question,answer,source,source_id)):
        return base|{'reason':'INVALID_INPUT'}
    q=question.lower()
    if 'budget' in q:
        kind='budget';sources=list(BUDGET_SOURCE.finditer(source));answers=list(BUDGET_ANSWER.finditer(answer))
        source_value=lambda m:m.group(1)
        answer_value=lambda m:m.group(1)
    elif 'deadline' in q:
        kind='deadline';sources=list(DEADLINE_SOURCE.finditer(source));answers=list(DEADLINE_ANSWER.finditer(answer))
        source_value=lambda m:m.group(2)
        answer_value=lambda m:m.group(1)
    else:return base|{'reason':'UNSUPPORTED_QUESTION'}
    if len(sources)!=1:return base|{'reason':'SOURCE_MISSING_OR_AMBIGUOUS','kind':kind}
    if len(answers)!=1:return base|{'reason':'ANSWER_MISSING_OR_AMBIGUOUS','kind':kind}
    src,ans=sources[0],answers[0]
    expected=_normal(kind,source_value(src));actual=_normal(kind,answer_value(ans))
    if expected is None or actual is None:return base|{'reason':'UNPARSABLE_VALUE','kind':kind}
    if expected==actual:return base|{'reason':'AGREES_WITH_SOURCE','kind':kind}
    return base|{'status':'SHADOW_MISMATCH','reason':'EXPLICIT_VALUE_CONTRADICTION','kind':kind,
                 'expected':expected,'answer_claim':actual,
                 'source_ref':{'source_id':source_id,'char_start':src.start(),'char_end':src.end()},
                 'exact_source_quote':source[src.start():src.end()],
                 'claim_limit':'Candidate contradiction on one exact explicit fact; not general truth or user-facing correction'}
