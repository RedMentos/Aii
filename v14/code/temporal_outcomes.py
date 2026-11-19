"""V14 source-bound temporal outcomes; SQLite, standard library, no learning authority."""
import json
import math
import sqlite3
from pathlib import Path

SCHEMA = """CREATE TABLE IF NOT EXISTS expectations (
 id TEXT PRIMARY KEY, source TEXT NOT NULL, owner TEXT NOT NULL,
 outcome TEXT NOT NULL, earliest REAL NOT NULL, deadline REAL NOT NULL,
 probability REAL NOT NULL, status TEXT NOT NULL,
 evidence TEXT NOT NULL DEFAULT '[]', error REAL,
 created REAL NOT NULL);"""
TERMINAL = {'OBSERVED', 'OMITTED', 'DELAYED', 'DIFFERENT', 'CENSORED', 'CANCELLED'}

class TemporalOutcomes:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute(SCHEMA)
        self.db.commit()

    def expect(self, *, id, source, owner, outcome, earliest, deadline, probability, created):
        if not all(isinstance(s, str) and 0 < len(s) <= 256 for s in (id, source, owner, outcome)):
            raise ValueError('source-bound nonempty strings required')
        if not all(isinstance(n, (int,float)) and math.isfinite(n) for n in (earliest, deadline, probability, created)):
            raise ValueError('nonfinite timing/probability')
        if not (created <= earliest <= deadline and 0 <= probability <= 1):
            raise ValueError('invalid expectation window')
        with self.db:
            self.db.execute('INSERT INTO expectations (id,source,owner,outcome,earliest,deadline,probability,status,created) VALUES (?,?,?,?,?,?,?,?,?)',
                            (id,source,owner,outcome,earliest,deadline,probability,'PENDING',created))

    def resolve(self, id, *, status, observed_at, evidence, observation_complete=False):
        if status not in TERMINAL:
            raise ValueError('invalid terminal status')
        if not isinstance(observed_at,(int,float)) or not math.isfinite(observed_at):
            raise ValueError('invalid observation time')
        if not isinstance(evidence,list) or any(not isinstance(x,str) or not x for x in evidence):
            raise ValueError('invalid evidence')
        with self.db:
            row=self.db.execute('SELECT earliest,deadline,probability,status FROM expectations WHERE id=?',(id,)).fetchone()
            if row is None: raise KeyError(id)
            earliest,deadline,p,old=row
            if old!='PENDING': raise ValueError('already resolved')
            if observed_at < earliest: raise ValueError('outcome before expectation window')
            if status == 'OMITTED' and (not observation_complete or observed_at < deadline or not evidence):
                raise ValueError('omission requires complete monitored interval and evidence')
            if status in {'OBSERVED','DELAYED','DIFFERENT'} and not evidence:
                raise ValueError('positive outcome requires evidence')
            if status == 'DELAYED' and observed_at <= deadline:
                raise ValueError('delayed requires later observation')
            if status == 'OBSERVED' and observed_at > deadline:
                raise ValueError('late observation must be DELAYED')
            error = -p if status=='OMITTED' else (1-p if status in {'OBSERVED','DELAYED'} else None)
            self.db.execute('UPDATE expectations SET status=?, evidence=?, error=? WHERE id=?',
                            (status,json.dumps(evidence),error,id))
            return {'status':status,'prediction_error':error,'learning_authorized':False}

    def pending_due(self, now):
        if not isinstance(now,(int,float)) or not math.isfinite(now): raise ValueError('invalid time')
        return [dict(id=r[0],deadline=r[1],source=r[2]) for r in self.db.execute(
            "SELECT id,deadline,source FROM expectations WHERE status='PENDING' AND deadline<=? ORDER BY deadline",(now,))]

    def read(self,id):
        row=self.db.execute('SELECT id,source,owner,outcome,earliest,deadline,probability,status,evidence,error FROM expectations WHERE id=?',(id,)).fetchone()
        if row is None: return None
        return dict(zip(('id','source','owner','outcome','earliest','deadline','probability','status','evidence','error'),row))
