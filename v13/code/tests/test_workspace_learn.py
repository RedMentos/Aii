"""WP-U8 L3-B4: the workspace learns per source kind how long slots are worth holding (SHADOW by default)."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13 import workspace_learn as WL

def it(ref,kind,active,turns):return {'payload_ref':ref,'source_kind':kind,'state_type':'ACTIVE' if active else 'REACTIVATABLE','turns_retained':turns}
def slot(ref,kind):return {'payload_ref':ref,'source_kind':kind}

class Base(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.s=self.r.store
    def tearDown(self):self.r.close();self.tmp.cleanup()

class Loop(Base):
    def test_useful_holds_raise_wasted_holds_lower_the_multiplier(self):
        for i in range(12):
            WL.observe(self.s,[it('m%d'%i,'MEMORY',True,1)],[it('b%d'%i,'B2_GIST',False,1)],[],[])
        k=WL.report(self.s)['kinds']
        self.assertGreater(k['MEMORY']['multiplier'],1.);self.assertLess(k['B2_GIST']['multiplier'],1.)
        self.assertGreaterEqual(k['B2_GIST']['multiplier'],WL.MULT_MIN)
        self.assertEqual(WL.decay_factor(self.s,'MEMORY'),1.)  # SHADOW
        with self.assertRaises(PermissionError):WL.set_mode(self.s,'ACTIVE')
        WL.operator_command(self.r,['active']);self.assertGreater(WL.decay_factor(self.s,'MEMORY'),1.)
    def test_restore_of_a_dropped_slot_counts_as_loss(self):
        WL.observe(self.s,[],[],[],[slot('x','MEMORY')])  # x dropped from the workspace
        WL.observe(self.s,[it('x','MEMORY',True,0),it('y','MEMORY',True,0)],[],[slot('x','MEMORY')],[])
        q=WL.report(self.s)['kinds']['MEMORY'];self.assertEqual((q['restored'],q['n_fresh']),(1,2));self.assertGreater(q['r_restore'],0.)
        self.assertEqual(WL.report(self.s)['dropped_tracked'],0)  # kept again -> no longer dropped
    def test_too_few_observations_stay_neutral(self):
        WL.observe(self.s,[it('m','MEMORY',True,1)],[],[],[]);WL.set_mode(self.s,'ACTIVE','EXPLICIT_HUMAN')
        self.assertEqual(WL.decay_factor(self.s,'MEMORY'),1.)

class WorkspaceHook(Base):
    def test_save_feeds_the_loop_and_load_applies_hold_only_when_active(self):
        from v13.focal import Workspace,item,BOOT
        e=self.s.event(self.r.session,'Projekt Aurora Budget?');self.r.memory.feedback(e['event_id'],'fact','120 Euro')
        m=self.s.one('SELECT id,source_id FROM memories WHERE active=1');src=self.s.one('SELECT * FROM sources WHERE id=?',(m['source_id'],))
        ref={'source_id':src['id'],'sha256':src['hash'],'char_start':0,'char_end':src['chars'],'modality':'text'}
        x=item('MEMORY',m['id'],[ref],'120 Euro',e['event_id'],uncertainty=.1,salience=.2,goal=.5,utility=.5,sq=.9)
        ws=Workspace(self.s,self.r.session);ws.save(e,[x],[],4)
        e2=self.s.event(self.r.session,'Und das Budget?');y=ws.load(e2)[0];self.assertAlmostEqual(y['decay'],BOOT['turn_decay'],places=4)
        y['state_type']='ACTIVE';ws.save(e2,[y],[],4)
        self.assertEqual(WL.report(self.s)['kinds']['MEMORY']['used'],1)
        st,v=self.s.state(WL.KEY,None);st['kinds']['MEMORY'].update(n_retained=20,v_refresh=1.);self.s.set_state(WL.KEY,st,expected=v)
        WL.set_mode(self.s,'ACTIVE','EXPLICIT_HUMAN');e3=self.s.event(self.r.session,'Noch einmal?')
        self.assertGreater(ws.load(e3)[0]['decay'],round(y['decay']*BOOT['turn_decay'],4))

if __name__=='__main__':unittest.main()
