"""Frozen-source builder and SQLite Runtime tests with simulated C3, not Redmi proof."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

CODE = Path(__file__).resolve().parents[1]

if os.environ.get('V13_RECORD_GUARD_INNER') == '1':
    from v13.runtime import Runtime
    from v13.operator import Operator
    from v13.online_world import OnlineWorld

    class MaterializedRuntime(unittest.TestCase):
        def setUp(self):
            self.tmp = tempfile.TemporaryDirectory()
            self.addCleanup(self.tmp.cleanup)
            self.home = Path(self.tmp.name)
            self.r = Runtime(self.home)
            self.addCleanup(lambda: self.r.close())
            self.r.sleep.cycle.set_policy('enabled','off')
            self.r.cfg['observer_mode'] = 'off'
            self.r._route = Mock(return_value=('simple',{'source':'SYNTHETIC_TEST'}))
            class Runner:
                role='C3_LANGUAGE'
                last_metrics={}
                def generate(self,*args,**kwargs):return iter(['synthetic answer'])
            self.r.pool.get = Mock(return_value=Runner())
            self.r.learner.output_delta = Mock(return_value=None)
            self.op = Operator(self.r)

        def turn(self):
            event=self.r.submit('Test question for online-world transition.')
            deadline=time.monotonic()+10
            while not self.r.idle() and time.monotonic()<deadline:time.sleep(.005)
            self.assertTrue(self.r.idle(), 'runtime did not settle')
            self.assertEqual(self.r.last_answer()['status'],'FINAL')
            return event

        def shadow(self):
            self.assertIn('SHADOW_UPDATE',self.op.run(':learning shadow'))

        def test_record_only_blocks_automatic_and_direct_updates_and_restart(self):
            self.turn()
            self.assertFalse(hasattr(self.r,'_online_world'))
            self.assertFalse((self.home/'online_world'/'online_predictor.npz').exists())
            self.assertEqual(self.r.online_world_update()['status'],'SKIPPED_RECORD_ONLY')
            world=OnlineWorld(self.r)
            self.assertEqual(world.update()['status'],'SKIPPED_RECORD_ONLY')
            self.assertEqual(world.model.seen,0)
            self.assertFalse(world.model.path.exists())
            self.r.close()
            self.r=Runtime(self.home)
            self.assertEqual(self.r.cfg['learning_mode'],'RECORD_ONLY')
            self.assertEqual(self.r.online_world_update()['status'],'SKIPPED_RECORD_ONLY')
            self.assertFalse((self.home/'online_world'/'online_predictor.npz').exists())

        def test_shadow_requires_opt_in_for_automatic_but_explicit_run_works(self):
            self.turn();self.shadow()
            self.assertEqual(self.r.online_world_update()['status'],'SKIPPED_OFF')
            self.assertFalse((self.home/'online_world'/'online_predictor.npz').exists())
            manual=json.loads(self.op.run(':growth onlineworld run 8'))
            self.assertGreaterEqual(manual['learned'],1)
            self.assertTrue((self.home/'online_world'/'online_predictor.npz').exists())
            before=self.r._online_world.model.seen
            self.turn()
            self.assertEqual(self.r._online_world.model.seen,before)
            enabled=json.loads(self.op.run(':growth onlineworld on'))
            self.assertTrue(enabled['enabled'])
            self.turn()
            self.assertGreater(self.r._online_world.model.seen,before)
            before=self.r._online_world.model.seen
            self.op.run(':pause training');self.turn()
            self.assertEqual(self.r._online_world.model.seen,before)
            self.assertEqual(self.r.online_world_update()['status'],'SKIPPED_PAUSED_TRAINING')
            self.op.run(':resume training')
            self.assertGreater(self.r.online_world_update()['learned'],0)
            self.op.run(':growth onlineworld off')
            self.assertEqual(self.r.online_world_update()['status'],'SKIPPED_OFF')
            self.op.run(':learning record')
            self.assertEqual(self.r.online_world_update(authority='EXPLICIT_HUMAN')['status'],'SKIPPED_RECORD_ONLY')

        def test_reentrant_stop_restores_in_memory_weights_and_no_checkpoint(self):
            self.turn();self.shadow()
            world=OnlineWorld(self.r)
            original=world.model.observe;before=world.model.W.copy()
            def change_mode(*args,**kwargs):
                result=original(*args,**kwargs)
                self.r.cfg['learning_mode']='RECORD_ONLY'
                return result
            world.model.observe=change_mode
            result=world.update(authority='EXPLICIT_HUMAN')
            self.assertEqual(result['status'],'SKIPPED_RECORD_ONLY')
            self.assertEqual(world.model.seen,0)
            self.assertTrue((world.model.W==before).all())
            self.assertFalse(world.model.path.exists())

        def test_torn_cursor_fails_closed_even_after_restart(self):
            self.turn();self.shadow()
            world=OnlineWorld(self.r)
            import v13.online_world as module
            replace=module.os.replace
            def fail_cursor(src,dest):
                if Path(dest)==world.cursor:raise OSError('injected cursor failure')
                return replace(src,dest)
            with patch.object(module.os,'replace',side_effect=fail_cursor):
                with self.assertRaises(OSError):world.update(authority='EXPLICIT_HUMAN')
            self.assertTrue(world.model.path.exists())
            self.assertFalse(world.cursor.exists())
            self.assertEqual(world.update(authority='EXPLICIT_HUMAN')['status'],'SKIPPED_TORN_OR_BOUNDED_CURSOR')
            self.r.close();self.r=Runtime(self.home)
            self.assertEqual(self.r.online_world_update(authority='EXPLICIT_HUMAN')['status'],'SKIPPED_TORN_OR_BOUNDED_CURSOR')

        def test_resources_and_invalid_authority_stop_before_learning(self):
            self.turn();self.shadow();self.op.run(':growth onlineworld on')
            self.r.guard.state='PRESSURE'
            self.assertEqual(self.r.online_world_update()['status'],'SKIPPED_RESOURCES')
            self.r.guard.state='NORMAL'
            with self.assertRaises(ValueError):self.r.online_world_update(authority='UNTRUSTED')
            self.assertFalse((self.home/'online_world'/'online_predictor.npz').exists())

        def test_busy_learning_instance_and_manual_call_while_active_are_refused(self):
            import threading
            self.turn();self.shadow()
            world=OnlineWorld(self.r)
            lock=threading.Lock();lock.acquire();self.r._online_world_update_lock=lock
            try:self.assertEqual(world.update(authority='EXPLICIT_HUMAN')['status'],'SKIPPED_UPDATE_BUSY')
            finally:lock.release()
            self.r.current='turn'
            try:
                with self.assertRaisesRegex(ValueError,'laufenden Vorgang'):
                    world.update(authority='EXPLICIT_HUMAN')
            finally:self.r.current=None
            self.assertFalse(world.model.path.exists())

        def test_checkpoint_exception_after_publication_latches_until_restart(self):
            self.turn();self.shadow()
            world=OnlineWorld(self.r)
            publish=world.model.checkpoint
            def write_then_fail():
                publish()
                raise OSError('injected after checkpoint publication')
            world.model.checkpoint=write_then_fail
            with self.assertRaises(OSError):world.update(authority='EXPLICIT_HUMAN')
            self.assertTrue(world.model.path.exists())
            self.assertEqual(world.model.seen,0)  # in-memory rollback
            self.assertEqual(world.update(authority='EXPLICIT_HUMAN')['status'],'SKIPPED_TORN_OR_BOUNDED_CURSOR')
            self.r.close();self.r=Runtime(self.home)
            self.assertEqual(self.r.online_world_update(authority='EXPLICIT_HUMAN')['status'],'SKIPPED_TORN_OR_BOUNDED_CURSOR')

else:
    from scripts import record_only_online_guard_candidate_20261116 as candidate

    class Candidate(unittest.TestCase):
        def test_materialized_runtime_end_to_end(self):
            with tempfile.TemporaryDirectory(prefix='v13-record-guard-') as tmp:
                dest=Path(tmp)/'code';dest.mkdir()
                for dirname in ('v13','specs','scripts'):
                    shutil.copytree(CODE/dirname,dest/dirname,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
                for name,raw in candidate.build_sources(CODE).items():
                    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                env=dict(os.environ,PYTHONPATH=str(dest),V13_RECORD_GUARD_INNER='1',PYTHONDONTWRITEBYTECODE='1')
                result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'-v'],cwd=dest,env=env,capture_output=True,text=True,timeout=80)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
                self.assertIn('Ran 7 tests',result.stderr)

        def test_source_mutation_fails_before_build(self):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name in candidate.SOURCE_SHA256:
                    target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(CODE/name,target)
                runtime=root/'v13/runtime.py'
                runtime.write_bytes(runtime.read_bytes()+b'\n# unexpected edit\n')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):
                    candidate.build_sources(root)

        def test_output_does_not_mutate_originals(self):
            before={name:hashlib.sha256((CODE/name).read_bytes()).hexdigest() for name in candidate.SOURCE_SHA256}
            replacement=candidate.build_sources(CODE)
            self.assertEqual(set(replacement),set(before))
            self.assertEqual(before,{name:hashlib.sha256((CODE/name).read_bytes()).hexdigest() for name in before})
            for name,data in replacement.items():
                self.assertNotEqual(hashlib.sha256(data).hexdigest(),before[name])
                compile(data,name,'exec')

        def test_android_style_ancestor_alias_is_allowed_but_internal_link_is_not(self):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);physical=root/'physical';code=physical/'code';code.mkdir(parents=True)
                for name in candidate.SOURCE_SHA256:
                    target=code/name;target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(CODE/name,target)
                alias=root/'android-alias';alias.symlink_to(physical,target_is_directory=True)
                self.assertEqual(set(candidate.build_sources(alias/'code')),set(candidate.SOURCE_SHA256))
                world=code/'v13/online_world.py';alternate=code/'world_copy.py'
                world.rename(alternate);world.symlink_to(alternate)
                with self.assertRaisesRegex(ValueError,'unsafe'):
                    candidate.build_sources(code)

if __name__ == '__main__':unittest.main()
