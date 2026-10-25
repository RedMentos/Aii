"""Run150: read-only, source-verified AGE0d SHADOW audit of persisted V13 turns.

No Runtime import, no mutation, no background process, no model authority.
Emits aggregate counts only; user messages, answers and session IDs stay local.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat

from v13.agi.answer_arithmetic_shadow_v3 import evaluate

GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
       'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}


def source_bytes(home,digest):
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('bad_source_digest')
    blobs=home/'data/blobs'
    if blobs.is_symlink() or not blobs.resolve().is_relative_to(home):
        raise ValueError('unsafe_blob_directory')
    path=blobs/digest
    fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_CLOEXEC',0))
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size>65536:raise ValueError('unsafe_source_file')
        with os.fdopen(fd,'rb',closefd=False) as f: data=f.read(65537)
        if len(data)>65536 or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('source_hash_mismatch')
        return data
    finally:os.close(fd)


def audit(home,session,limit=100):
    home=Path(home).resolve()
    if not isinstance(session,str) or not 1<=len(session)<=160:raise ValueError('session_required')
    if type(limit) is not int or not 1<=limit<=1000:raise ValueError('limit_out_of_range')
    db=home/'data/db/brain.sqlite3'
    if db.is_symlink() or not db.is_file():raise ValueError('database_missing_or_symlink')
    con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,isolation_level=None,timeout=5)
    con.row_factory=sqlite3.Row
    reasons=Counter();status=Counter();considered=0
    try:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        rows=con.execute('''SELECT e.id,e.session_id,e.source_id,e.packet,
                            s.hash AS source_hash,s.deleted AS source_deleted,
                            q.state AS queue_state
                            FROM events e LEFT JOIN sources s ON s.id=e.source_id
                            LEFT JOIN accepted_turns q ON q.event_id=e.id
                            WHERE e.session_id=? ORDER BY e.created DESC,e.id DESC LIMIT ?''',(session,limit)).fetchall()
        for row in rows:
            considered+=1
            if row['queue_state']!='DONE':reasons['not_done']+=1;continue
            if row['source_hash'] is None or row['source_deleted']!=0:reasons['missing_or_deleted_source']+=1;continue
            messages=con.execute('SELECT session_id,role,text,status,metadata FROM messages WHERE event_id=? ORDER BY id',(row['id'],)).fetchall()
            user=[m for m in messages if m['role']=='user' and m['status']=='FINAL']
            assistant=[m for m in messages if m['role']=='assistant' and m['status']=='FINAL']
            if len(user)!=1 or len(assistant)!=1:reasons['missing_or_ambiguous_final']+=1;continue
            if any(m['session_id']!=session for m in messages):reasons['cross_session_message']+=1;continue
            try:
                packet=json.loads(row['packet']);meta=json.loads(user[0]['metadata'])
                ref=packet['source_ref']
                if ref!=meta['source_ref'] or ref['source_id']!=row['source_id'] or ref['sha256']!=row['source_hash']:
                    raise ValueError('ref_mismatch')
                raw=source_bytes(home,row['source_hash']);text=raw.decode('utf-8')
                if (ref['char_start'],ref['char_end'])!=(0,len(text)) or user[0]['text']!=text:
                    raise ValueError('source_text_mismatch')
            except (ValueError,KeyError,TypeError,UnicodeError,OSError):
                reasons['source_integrity_fail']+=1;continue
            verdict=evaluate(text,assistant[0]['text'])
            status[verdict['status']]+=1
        con.execute('ROLLBACK')
    finally:con.close()
    return {'schema':'V13_RUN150_PERSISTED_AGE0D_SHADOW_V1',
            'evidence_class':'LOCAL_READ_ONLY_SOURCE_VERIFIED_HISTORY_SOFTWARE',
            'session_scoped':True,'considered':considered,'source_verified':sum(status.values()),
            'verdicts':{k:status[k] for k in ('CORRECT','MISMATCH','ABSTAIN')},
            'skips':dict(sorted(reasons.items())),'authority':'SHADOW_ONLY',
            'may_deliver':False,'may_update':False,'gate':'UNVERIFIED','gates':GATES,
            'limitations':['FINAL text is not proof that C3 generated it',
                           'only explicit single-operation arithmetic supported',
                           'no raw user content, answers or session identifiers in output',
                           'no learning, no phone or full-system proof']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--home',required=True,type=Path)
    p.add_argument('--session',required=True);p.add_argument('--limit',type=int,default=100)
    a=p.parse_args();print(json.dumps(audit(a.home,a.session,a.limit),sort_keys=True,indent=2))

if __name__=='__main__':main()
