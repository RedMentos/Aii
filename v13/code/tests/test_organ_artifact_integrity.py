"""Real Store/file regressions for organ restore: metadata alone cannot prove intact artifacts. No model calls."""
from v13 import organ as O
import shutil
from unittest.mock import patch
from v13.common import digest,dumps,file_hash
from v13.runtime import Runtime
from test_organ import Base


class ArtifactIntegrity(Base):
    def saved_component(self):
        self.put('b1_predictor','B1_DETAIL',b'b1-good')
        snap=O.snapshot(self.r,'B1_DETAIL')
        path=self.r.home/snap['components']['b1_predictor']['path']
        rel=snap.get('component_files',{}).get('b1_predictor',path.name)
        backup=self.r.home/'organs/B1_DETAIL'/snap['id']/'files'/rel
        return snap,path,backup

    def test_missing_active_artifact_is_repaired_without_metadata_change(self):
        snap,path,_=self.saved_component();old_generation=self.r.store.generation_id;path.unlink()
        c=O.check(self.r,snap['id'])
        self.assertFalse(c['identical']);self.assertEqual(c['parts']['components:b1_predictor'],'MISSING')
        self.assertTrue(c['restorable'])
        out=O.restore(self.r,snap['id'])
        self.assertEqual(out['status'],'RESTORED');self.assertNotEqual(out['generation'],old_generation)
        active=self.r.home/self.r.store.components()['b1_predictor']['path']
        self.assertEqual(active.read_bytes(),b'b1-good');self.assertFalse(path.exists())
        self.r.store.validate_artifacts(self.r.store.generation())

    def test_corrupt_active_artifact_is_repaired_and_survives_restart(self):
        snap,path,_=self.saved_component();path.write_bytes(b'broken')
        self.assertEqual(O.check(self.r,snap['id'])['parts']['components:b1_predictor'],'CHANGED')
        self.assertEqual(O.restore(self.r,snap['id'])['status'],'RESTORED')
        self.r.store.validate_artifacts(self.r.store.generation())
        home=self.r.home;self.r.close();self.r=Runtime(home);self.r.models.revision=lambda role:self.rev.get(role)
        self.assertTrue(O.check(self.r,snap['id'])['identical'])
        active=self.r.home/self.r.store.components()['b1_predictor']['path']
        self.assertEqual(active.read_bytes(),b'b1-good');self.assertEqual(path.read_bytes(),b'broken')

    def test_damaged_saved_component_is_refused_even_when_active_matches(self):
        snap,path,backup=self.saved_component();gid=self.r.store.generation_id
        backup.write_bytes(b'broken-backup')
        c=O.check(self.r,snap['id'])
        self.assertFalse(c['restorable'] or c['identical']);self.assertFalse(c['backup_intact'])
        self.assertEqual(c['backup_parts']['components:b1_predictor'],'CHANGED')
        self.assertIn('BESCHÄDIGT',O.text_check(c))
        with self.assertRaises(RuntimeError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid);self.assertEqual(path.read_bytes(),b'b1-good')

    def test_missing_saved_component_refuses_before_other_file_repair(self):
        self.put('first','B1_DETAIL',b'first-good')
        snap,path,backup=self.saved_component();gid=self.r.store.generation_id
        first=self.r.home/snap['components']['first']['path'];first.write_bytes(b'first-broken');backup.unlink()
        c=O.check(self.r,snap['id']);self.assertFalse(c['restorable'])
        self.assertEqual(c['backup_parts']['components:b1_predictor'],'MISSING')
        with self.assertRaises(RuntimeError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid);self.assertEqual(first.read_bytes(),b'first-broken')

    def test_missing_saved_bridge_refuses_unchanged_organ(self):
        self.bridge('B1_TO_B2.json','{"v":1}');snap=O.snapshot(self.r,'B1_DETAIL');gid=self.r.store.generation_id
        (self.r.home/'organs/B1_DETAIL'/snap['id']/'files/B1_TO_B2.json').unlink()
        c=O.check(self.r,snap['id'])
        self.assertFalse(c['restorable'] or c['identical'])
        with self.assertRaises(RuntimeError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid)
        self.assertEqual((self.r.home/'b3/B1_TO_B2.json').read_text(),'{"v":1}')

    def test_path_owned_by_other_organ_is_refused_before_overwrite(self):
        snap,path,_=self.saved_component();path.write_bytes(b'route-newer')
        s=self.r.store;base=s.generation();entry=dict(base['components']['b1_predictor'])
        entry.update(encoder_role='C2_CONTROL',encoder_revision=self.rev['C2_CONTROL'],
                     dependency_revisions={'C2_CONTROL':self.rev['C2_CONTROL']},sha256=file_hash(path))
        comps={'route':entry};hashes={entry['path']:entry['sha256']}
        with s.tx() as cur:s._generation(cur,s.generation_id,hashes,base['config'],base['rule_version'],base['models'],[],comps,None)
        gid=s.generation_id
        with self.assertRaises(ValueError):O.restore(self.r,snap['id'])
        self.assertEqual(s.generation_id,gid);self.assertEqual(path.read_bytes(),b'route-newer')
        s.validate_artifacts(s.generation())

    def publish_components(self,comps):
        s=self.r.store;base=s.generation();hashes={e['path']:e['sha256'] for e in comps.values()}
        with s.tx() as cur:s._generation(cur,s.generation_id,hashes,base['config'],base['rule_version'],base['models'],[],comps,None)

    def two_components(self):
        self.put('b1_predictor','B1_DETAIL',b'first-good');self.put('b2_predictor','B1_DETAIL',b'second-good')
        snap=O.snapshot(self.r,'B1_DETAIL')
        paths=[self.r.home/snap['components'][name]['path'] for name in ('b1_predictor','b2_predictor')]
        return snap,*paths

    def test_later_collision_refuses_before_repairing_earlier_artifact(self):
        snap,first,second=self.two_components();first.write_bytes(b'first-broken');second.write_bytes(b'other-organ')
        comps=self.r.store.components();entry=dict(comps.pop('b2_predictor'))
        entry.update(encoder_role='C2_CONTROL',dependency_revisions={'C2_CONTROL':self.rev['C2_CONTROL']},sha256=file_hash(second))
        comps['route']=entry;self.publish_components(comps);gid=self.r.store.generation_id
        before=set((self.r.home/'checkpoints').iterdir())
        with self.assertRaises(ValueError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid)
        self.assertEqual(first.read_bytes(),b'first-broken');self.assertEqual(second.read_bytes(),b'other-organ')
        self.assertEqual(set((self.r.home/'checkpoints').iterdir()),before)

    def test_later_dependency_refuses_before_repairing_earlier_artifact(self):
        self.put('b1_predictor','B1_DETAIL',b'first-good');self.put('b2_predictor','B1_DETAIL',b'second-good')
        comps=self.r.store.components();comps['b2_predictor']['dependency_revisions']['C2_CONTROL']=self.rev['C2_CONTROL']
        self.publish_components(comps);snap=O.snapshot(self.r,'B1_DETAIL');gid=self.r.store.generation_id
        first=self.r.home/comps['b1_predictor']['path'];first.write_bytes(b'first-broken');self.rev['C2_CONTROL']='new-rev'
        with self.assertRaises(ValueError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid);self.assertEqual(first.read_bytes(),b'first-broken')

    def test_refused_commit_leaves_existing_files_and_no_staged_files(self):
        snap,first,second=self.two_components();first.write_bytes(b'first-broken');second.write_bytes(b'second-broken')
        gid=self.r.store.generation_id;before=set((self.r.home/'checkpoints').iterdir())
        with patch.object(self.r.store,'_generation',side_effect=ValueError('refused commit')):
            with self.assertRaises(ValueError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid)
        self.assertEqual(first.read_bytes(),b'first-broken');self.assertEqual(second.read_bytes(),b'second-broken')
        self.assertEqual(set((self.r.home/'checkpoints').iterdir()),before)

    def test_later_copy_failure_leaves_existing_files_and_no_staged_files(self):
        snap,first,second=self.two_components();first.write_bytes(b'first-broken');second.write_bytes(b'second-broken')
        gid=self.r.store.generation_id;before=set((self.r.home/'checkpoints').iterdir());real=O._copy_new;calls=[]
        def fail_second(*args):
            calls.append(1)
            if len(calls)==2:raise OSError('injected copy failure')
            return real(*args)
        with patch.object(O,'_copy_new',side_effect=fail_second):
            with self.assertRaises(OSError):O.restore(self.r,snap['id'])
        self.assertEqual(self.r.store.generation_id,gid)
        self.assertEqual(first.read_bytes(),b'first-broken');self.assertEqual(second.read_bytes(),b'second-broken')
        self.assertEqual(set((self.r.home/'checkpoints').iterdir()),before)

    def test_same_basename_snapshot_preserves_both_components(self):
        self.put('b1_predictor','B1_DETAIL',b'first-good');self.put('b2_predictor','B1_DETAIL',b'second-good')
        comps=self.r.store.components()
        for name,e in comps.items():
            target=self.r.home/'checkpoints'/name/'candidate.npz';target.parent.mkdir();shutil.move(self.r.home/e['path'],target)
            e['path']=str(target.relative_to(self.r.home))
        self.publish_components(comps);snap=O.snapshot(self.r,'B1_DETAIL')
        self.assertTrue(O.check(self.r,snap['id'])['backup_intact'])
        self.put('b1_predictor','B1_DETAIL',b'first-new');self.put('b2_predictor','B1_DETAIL',b'second-new')
        self.assertEqual(O.restore(self.r,snap['id'])['status'],'RESTORED')
        active=self.r.store.components()
        self.assertEqual((self.r.home/active['b1_predictor']['path']).read_bytes(),b'first-good')
        self.assertEqual((self.r.home/active['b2_predictor']['path']).read_bytes(),b'second-good')
        self.r.store.validate_artifacts(self.r.store.generation())

    def test_legacy_flat_backup_still_restores(self):
        snap,path,backup=self.saved_component();folder=backup.parents[2]
        legacy=folder/'files'/path.name;shutil.move(backup,legacy)
        snap.pop('component_files');snap['hash']=digest(dumps({k:v for k,v in snap.items() if k!='hash'}))
        (folder/'manifest.json').write_text(dumps(snap));path.unlink()
        self.assertTrue(O.check(self.r,snap['id'])['backup_intact'])
        self.assertEqual(O.restore(self.r,snap['id'])['status'],'RESTORED')
        active=self.r.home/self.r.store.components()['b1_predictor']['path']
        self.assertEqual(active.read_bytes(),b'b1-good');self.assertFalse(path.exists())
