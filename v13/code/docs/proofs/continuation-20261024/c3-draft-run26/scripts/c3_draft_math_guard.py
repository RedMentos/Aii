#!/usr/bin/env python3
"""V13 WP-Z6b: independent C3 draft arithmetic-consistency signal (SHADOW).

This is NOT a correctness judge or a wake policy. It only detects a small
closed family of contradictions in *actual generated text*. A no-signal
result must never be interpreted as evidence that an answer is correct.
No tools, writes to V13 state, learning or authority are performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

_EXPR = re.compile(r'(?<![\d.])(\d{1,6}(?:\s*[+\-]\s*\d{1,6}){1,3})\s*=\s*(\d{1,8})(?!\d)')
_TOTAL = re.compile(r'\bcorrect\s+total\s+is\s+\*{0,2}(\d{1,8})\s*(?:\*{0,2}\s*(?:euros?|dollars?|mm))?[^\n()]{0,60}\((\d{1,6}(?:\s*\+\s*\d{1,6}){1,3})\)',re.I)
_DIFF = re.compile(r'\bdifference\s+is\s+(\d{1,8})\s*(?:mm|units?)?\s*\((\d{1,6})\s*-\s*(\d{1,6})\)',re.I)
_RANK = re.compile(r'\b(?:most|highest)\b[^.\n]{0,120}?(\d{1,6})\s*mm[^.\n]{0,120}?\b(?:least|lowest)\b[^.\n]{0,60}?(\d{1,6})\s*mm',re.I)
_MAX_TEXT = 8192


def _value(expr):
    terms = re.findall(r'\d+|[+\-]',expr)
    value=int(terms[0])
    for i in range(1,len(terms),2):
        value += int(terms[i+1]) if terms[i]=='+' else -int(terms[i+1])
    return value


def assess(text):
    """Pure bounded evidence-only signal; false negatives expected by design."""
    if type(text) is not str or len(text)>_MAX_TEXT:
        raise ValueError('bounded string draft required')
    findings=[];seen=set()
    def add(kind,span,observed,expected):
        key=(kind,span,observed,expected)
        if key not in seen:
            seen.add(key)
            findings.append({'kind':kind,'span':[span[0],span[1]],
                             'claimed':observed,'calculated':expected})
    for m in _EXPR.finditer(text):
        actual=_value(m.group(1));claim=int(m.group(2))
        if actual!=claim:add('EXPLICIT_ARITHMETIC',m.span(),claim,actual)
    for m in _TOTAL.finditer(text):
        actual=_value(m.group(2));claim=int(m.group(1))
        if actual!=claim:add('TOTAL_SUM_CONTRADICTION',m.span(),claim,actual)
    for m in _DIFF.finditer(text):
        actual=int(m.group(2))-int(m.group(3));claim=int(m.group(1))
        if actual!=claim:add('DIFFERENCE_CONTRADICTION',m.span(),claim,actual)
    for m in _RANK.finditer(text):
        high,low=int(m.group(1)),int(m.group(2))
        if high<low:add('ORDER_INVERSION',m.span(),high,low)
    return {'schema':'V13_C3_DRAFT_MATH_SHADOW_V1',
            'status':'NEEDS_VERIFICATION' if findings else 'NO_ARITHMETIC_CONTRADICTION_FOUND',
            'findings':findings,'authority':'SHADOW_NO_ACTION','correctness_proven':False}


def audit_records(records):
    """Read-only inputs; return independent per-record signals, not verdicts."""
    if type(records) is not list or len(records)>10000:
        raise ValueError('bounded list required')
    ids=set();out=[]
    for row in records:
        if type(row) is not dict or set(row)!={'fixture','draft'}:
            raise ValueError('closed input schema required')
        fid=row['fixture']
        if type(fid) is not str or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',fid) or fid in ids:
            raise ValueError('invalid or duplicate fixture')
        ids.add(fid)
        out.append({'fixture':fid,**assess(row['draft'])})
    return out


def write_closed_report(input_path,output_path):
    """Atomic, durable, non-overwriting output; caller controls both paths."""
    source=Path(input_path)
    with source.open('rb') as f:
        raw=f.read(16*1024*1024+1)
    if len(raw)>16*1024*1024:raise ValueError('input too large')
    def unique_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate input JSON key')
            result[key]=value
        return result
    records=json.loads(raw,object_pairs_hook=unique_pairs)
    rows=audit_records(records)
    report={'schema':'V13_C3_DRAFT_MATH_AUDIT_V1','input_sha256':hashlib.sha256(raw).hexdigest(),
            'source_claim':'SHADOW_SOFTWARE_ONLY','rows':rows}
    data=(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode()
    dest=Path(output_path)
    if dest.exists():raise FileExistsError('refuse overwrite of evidence')
    fd,tmp=tempfile.mkstemp(prefix='.c3-draft-',dir=dest.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        # No clobber even if another owner publishes during this run.
        os.link(tmp,dest)
        dirfd=os.open(dest.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dirfd)
        finally:os.close(dirfd)
    finally:
        os.unlink(tmp)
    return hashlib.sha256(data).hexdigest()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('input_json');parser.add_argument('output_json')
    args=parser.parse_args()
    print(write_closed_report(args.input_json,args.output_json))
