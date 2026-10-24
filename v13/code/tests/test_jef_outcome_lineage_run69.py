"""Run69 SQLite adversarial JEF outcome lineage.

Uses actual v13.jefoutcome.training_rows in full checkout. Scratch replay
is separate synthetic evidence; no native optimizer is exercised.
"""
import hashlib
import json
import sqlite3
import unittest
from v13.jefoutcome import training_rows
from v13.jef_human_veto import blocked_human_contexts


class Store:
    def __init__(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""
          CREATE TABLE packets(id TEXT,kind TEXT,event_id TEXT,payload TEXT);
          CREATE TABLE feedback(event_id TEXT,source_id TEXT,kind TEXT,value TEXT,permission TEXT,created REAL);
          CREATE TABLE sources(id TEXT,deleted INTEGER,hash TEXT,chars INTEGER,kind TEXT);
          CREATE INDEX packet_event ON packets(event_id,kind);
        """)
        self.labels=[]
        self.blobs={}
    def state(self,key):return {'mode':'learn','labels':self.labels},1
    def rows(self,sql,args=()):return [dict(x) for x in self.db.execute(sql,args).fetchall()]
    def one(self,sql,args=()):
        row=self.db.execute(sql,args).fetchone()
        return dict(row) if row else None
    def add_source(self,sid,deleted=0,text='detail',kind='OUTCOME_SELF_LABEL'):
        self.blobs[sid]=text
        self.db.execute('INSERT INTO sources VALUES (?,?,?,?,?)',
                        (sid,deleted,hashlib.sha256(text.encode()).hexdigest(),len(text),kind))
    def read_source(self,ref):
        row=self.one('SELECT * FROM sources WHERE id=?',(ref['source_id'],))
        if not row or row['deleted'] or row['hash']!=ref['sha256']:
            raise ValueError('Invalid SourceRef')
        text=self.blobs[ref['source_id']]
        if hashlib.sha256(text.encode()).hexdigest()!=row['hash']:
            raise ValueError('Corrupt source')
        if not 0<=ref['char_start']<=ref['char_end']<=len(text):
            raise ValueError('Invalid source extent')
        return text[ref['char_start']:ref['char_end']]
    def add_self(self,context='ctx1',event='e1',component='wake',revision='rev',source='self1',decision='d1',packet_context=None,packet_event=None,packet_component=None,packet_revision=None):
        self.add_source(source)
        self.labels.append({'component':component,'context_revision':revision,'context_sha256':context,
                            'decision_packet_id':decision,'source_id':source,'event_id':event,'value':'detail'})
        payload={'packet_id':decision,'event_id':packet_event or event,'component':packet_component or component,
                 'context_revision':packet_revision or revision,'context_ref':{'sha256':packet_context or context}}
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',(decision,'ExecutiveDecision',packet_event or event,json.dumps(payload)))
    def add_human(self,context='ctx1',event='e1',source='human1',decision='hd1',deleted=0):
        self.add_source(source,deleted)
        self.db.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?)',(event,source,'wake','detail','record',1.))
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',(decision,'ExecutiveDecision',event,json.dumps({'packet_id':decision,'event_id':event,'component':'wake','context_revision':'rev','context_ref':{'sha256':context}})))
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',('p-'+source,'HumanDecision',event,json.dumps({'source_ref':{'source_id':source},'decision_packet_id':decision})))
    def close(self):self.db.close()


class JefOutcomeLineage(unittest.TestCase):
    def setUp(self):self.s=Store()
    def tearDown(self):self.s.close()
    def rows(self):return training_rows(self.s,'wake','rev',set())

    def test_old_human_record_outside_512_window_vetoes(self):
        self.s.add_self();self.s.add_human()
        for i in range(600):
            sid='noise'+str(i)
            self.s.add_source(sid)
            self.s.db.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?)',('noise',sid,'wake','none','record',2.+i))
        self.assertEqual(self.rows(),[])

    def test_no_human_allows_bound_self_label(self):
        self.s.add_self()
        self.assertEqual(len(self.rows()),1)

    def test_human_unrelated_context_does_not_veto(self):
        self.s.add_self();self.s.add_human(context='ctx2')
        self.assertEqual(len(self.rows()),1)

    def test_deleted_human_source_does_not_claim_current_veto(self):
        self.s.add_self();self.s.add_human(deleted=1)
        self.assertEqual(len(self.rows()),1)

    def test_forged_cross_event_human_decision_does_not_veto(self):
        self.s.add_self();self.s.add_human(event='e2')
        self.s.db.execute("UPDATE packets SET event_id='e1' WHERE id='hd1'")
        self.assertEqual(len(self.rows()),1)

    def test_forged_self_context_link_is_rejected(self):
        self.s.add_self(packet_context='other')
        self.assertEqual(self.rows(),[])

    def test_forged_self_component_is_rejected(self):
        self.s.add_self(packet_component='skill')
        self.assertEqual(self.rows(),[])

    def test_forged_self_event_is_rejected(self):
        self.s.add_self(packet_event='other')
        self.assertEqual(self.rows(),[])

    def test_forged_self_revision_is_rejected(self):
        self.s.add_self(packet_revision='other')
        self.assertEqual(self.rows(),[])

    def test_deleted_self_label_source_is_rejected(self):
        self.s.add_self();self.s.db.execute("UPDATE sources SET deleted=1 WHERE id='self1'")
        self.assertEqual(self.rows(),[])

    def test_record_mode_never_trains(self):
        self.s.add_self();self.s.state=lambda key:({'mode':'record','labels':self.s.labels},1)
        self.assertEqual(self.rows(),[])

    def test_chunked_exact_human_lookup(self):
        self.s.add_human()
        keys=['ctx'+str(i) for i in range(500)]+['ctx1']
        self.assertEqual(blocked_human_contexts(self.s,'wake','rev',keys),{'ctx1'})


if __name__=='__main__':unittest.main()
