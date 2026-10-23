"""WP-AGE0b organ checkpoint: snapshot/check/restore one model organ's heads and bridges without touching other organs;
refused while busy or after a model change; damaged backups are refused. No models (fake artifacts in a test generation)."""
import json
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.operator import Operator
from v13.common import file_hash
from v13 import organ as O
from v13 import standstill as S


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.op=Operator(self.r)
        self.rev={'B1_DETAIL':'b1-rev1','C2_CONTROL':'c2-rev1'}
        self.r.models.revision=lambda role:self.rev.get(role)
        self.n=0
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def put(self,component,role,content):
        """Install a fake committed component in a new generation (what Store.switch_generation would write)."""
        self.n+=1;rel=f'checkpoints/{component}-u{self.n}.npz';p=self.r.home/rel;p.parent.mkdir(exist_ok=True);p.write_bytes(content)
        s=self.r.store;base=s.generation();comps=dict(s.components(base));hashes=dict(base['hashes'])
        if component in comps:hashes.pop(comps[component]['path'])
        comps[component]={'path':rel,'sha256':file_hash(p),'update_id':None,'encoder_role':role,'encoder_revision':self.rev[role],
                          'dependency_revisions':{role:self.rev[role]},'context_revision':None}
        hashes[rel]=comps[component]['sha256']
        with s.tx() as c:s._generation(c,s.generation_id,hashes,base['config'],base['rule_version'],base['models'],[],comps,None)
    def bridge(self,name,text):
        d=self.r.home/'b3';d.mkdir(exist_ok=True);(d/name).write_text(text)
    def active(self,component):return self.r.store.components().get(component,{}).get('sha256')


class OrganTests(Base):
    def test_membership_is_per_role(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-a');self.put('route','C2_CONTROL',b'route-a');self.bridge('B1_TO_B2.json','{"v":1}')
        m=O.members(self.r,'B1_DETAIL')
        self.assertEqual(sorted(m['components']),['b1_predictor']);self.assertEqual(list(m['bridges']),['B1_TO_B2.json'])
        self.assertEqual(sorted(O.members(self.r,'C2_CONTROL')['components']),['route'])

    def test_restore_puts_back_one_organ_and_leaves_the_other(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-good');self.put('route','C2_CONTROL',b'route-a');self.bridge('B1_TO_B2.json','{"v":1}')
        good=self.active('b1_predictor');snap=O.snapshot(self.r,'B1_DETAIL')
        self.put('b1_predictor','B1_DETAIL',b'b1-broken');self.put('route','C2_CONTROL',b'route-newer');self.bridge('B1_TO_B2.json','{"v":2}')
        route_now=self.active('route')
        c=O.check(self.r,snap['id']);self.assertFalse(c['identical']);self.assertEqual(c['parts']['components:b1_predictor'],'CHANGED')
        out=O.restore(self.r,snap['id']);self.assertEqual(out['status'],'RESTORED')
        self.assertEqual(self.active('b1_predictor'),good);self.assertEqual(self.active('route'),route_now)  # other organ untouched
        self.assertEqual(json.loads((self.r.home/'b3/B1_TO_B2.json').read_text()),{'v':1})
        self.assertTrue(O.check(self.r,snap['id'])['identical'])
        self.r.store.validate_artifacts(self.r.store.generation())
        self.assertIsNone(self.r.store.generation().get('last_weight_update_id'))  # LIFO rollback closed, cannot undo silently

    def test_restore_brings_back_a_deleted_artifact_file(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-good');snap=O.snapshot(self.r,'B1_DETAIL');path=self.r.home/snap['components']['b1_predictor']['path']
        self.put('b1_predictor','B1_DETAIL',b'b1-x');path.unlink()
        O.restore(self.r,snap['id']);active=self.r.home/self.r.store.components()['b1_predictor']['path']
        self.assertEqual(active.read_bytes(),b'b1-good');self.assertFalse(path.exists())  # old generations are never overwritten

    def test_component_added_after_snapshot_is_removed_on_restore(self):
        snap=O.snapshot(self.r,'B1_DETAIL');self.put('b1_predictor','B1_DETAIL',b'b1-new')
        self.assertEqual(O.check(self.r,snap['id'])['parts']['components:b1_predictor'],'ADDED')
        O.restore(self.r,snap['id']);self.assertIsNone(self.active('b1_predictor'))

    def test_model_change_refuses_restore(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-good');snap=O.snapshot(self.r,'B1_DETAIL');self.rev['B1_DETAIL']='b1-rev2'
        c=O.check(self.r,snap['id']);self.assertFalse(c['model_same'] or c['restorable'])
        with self.assertRaises(ValueError):O.restore(self.r,snap['id'])

    def test_damaged_backup_is_refused(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-good');snap=O.snapshot(self.r,'B1_DETAIL');self.put('b1_predictor','B1_DETAIL',b'b1-x')
        f=self.r.home/'organs/B1_DETAIL'/snap['id']/'manifest.json';m=json.loads(f.read_text());m['bridges']={'X_TO_B1.json':'0'};f.write_text(json.dumps(m))
        with self.assertRaises(RuntimeError):O.check(self.r,snap['id'])
        f.write_text(json.dumps(snap));(self.r.home/'organs/B1_DETAIL'/snap['id']/'files'/snap['component_files']['b1_predictor']).write_bytes(b'evil')
        (self.r.home/snap['components']['b1_predictor']['path']).unlink()
        with self.assertRaises(RuntimeError):O.restore(self.r,snap['id'])
        self.assertNotEqual(self.active('b1_predictor'),snap['components']['b1_predictor']['sha256'])

    def test_snapshot_refused_while_busy_works_in_standstill(self):
        self.r.idle=lambda:False
        with self.assertRaises(ValueError):O.snapshot(self.r,'B1_DETAIL')
        del self.r.idle;S.engage(self.r);self.assertIn('Organ-Sicherung',self.op.run(':organ snapshot B1_DETAIL'))
        self.assertEqual(len(O.listing(self.r)),1);S.release(self.r)

    def test_refused_commit_leaves_bridges_untouched(self):
        self.bridge('B1_TO_B2.json','{"v":1}');snap=O.snapshot(self.r,'B1_DETAIL');self.bridge('B1_TO_B2.json','{"v":2}')
        real=self.r.store._generation
        def boom(*a,**k):raise ValueError('Generation konkurrierend geändert')
        self.r.store._generation=boom
        with self.assertRaises(ValueError):O.restore(self.r,snap['id'])
        self.r.store._generation=real;self.assertEqual(json.loads((self.r.home/'b3/B1_TO_B2.json').read_text()),{'v':2})

    def test_operator_check_text(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-good');snap=O.snapshot(self.r,'B1_DETAIL')
        self.assertIn('unverändert',self.op.run(':organ check '+snap['id']))
        with self.assertRaises(ValueError):self.op.run(':organ check organ_nope')


if __name__=='__main__':unittest.main()
