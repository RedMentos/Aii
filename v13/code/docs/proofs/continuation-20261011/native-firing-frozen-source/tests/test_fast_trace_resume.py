"""Proof collector lifecycle with mocked native transport, never a model quality proof."""
import importlib.util
import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPT=Path(__file__).parents[1]/'scripts/fast_trace_compare.py'
spec=importlib.util.spec_from_file_location('fast_trace_resume_under_test',SCRIPT)
bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)


class CheckpointResume(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.args=[]
        for name in ('server','model.gguf','memory.bin'):
            p=self.home/name;p.write_bytes(name.encode());self.args.append(str(p))
        self.out=self.home/'proof.json';self.args.append(str(self.out))
        self.corpus=patch.multiple(bench,FACTS=[('fixture question','fixture answer',['answer'])],
                                  PARAPHRASES=[('paraphrase',['answer'])],NEAR_MISS=[('near',['answer'])],
                                  PROBES=[{'prompt':'retention','expect':['answer']}])
        self.corpus.start()
    def tearDown(self):self.corpus.stop();self.tmp.cleanup()

    def test_failed_native_call_keeps_raw_rows_and_resume_never_replays_completed_row(self):
        proc=Mock()
        full='answer '+'x'*200
        with patch.object(bench,'serve',return_value=proc),patch.object(bench,'ask',side_effect=[(full,21,.3),TimeoutError('native deadline')]):
            with self.assertRaises(TimeoutError):bench.compare(*self.args)
        failed=json.loads(self.out.read_text())
        self.assertEqual(failed['_checkpoint']['status'],'INCOMPLETE')
        self.assertEqual(failed['_checkpoint']['attempts'][0]['error'],'TimeoutError')
        self.assertEqual(failed['base']['facts_rows'][0]['a'],full)
        proc.terminate.assert_called_once();proc.wait.assert_called_once()
        with patch.object(bench,'serve',return_value=Mock()),patch.object(bench,'ask',return_value=('answer',10,.1)) as ask:
            result=bench.compare(*self.args,resume=True)
        self.assertEqual(ask.call_count,15)  # 16 total minus the one durable row
        self.assertEqual(result['base']['facts_rows'],failed['base']['facts_rows'])
        self.assertEqual(result['_checkpoint']['status'],'COMPLETE')
        self.assertEqual([a['status'] for a in result['_checkpoint']['attempts']],['ERROR','COMPLETE'])
        # Reopening a complete checkpoint requires no subprocess or native request.
        with patch.object(bench,'serve',side_effect=AssertionError('duplicate process')),patch.object(bench,'ask',side_effect=AssertionError('duplicate request')):
            bench.compare(*self.args,resume=True)

    def test_changed_native_artifact_or_corpus_cannot_merge_proofs(self):
        with patch.object(bench,'serve',side_effect=RuntimeError('startup failed')):
            with self.assertRaises(RuntimeError):bench.compare(*self.args)
        before=self.out.read_bytes();Path(self.args[2]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'binding differs'):bench.compare(*self.args,resume=True)
        self.assertEqual(self.out.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'Output exists'):bench.compare(*self.args)
        self.assertEqual(self.out.read_bytes(),before)

    def test_repetitions_have_distinct_paired_rows_and_forgotten_probe(self):
        def answer(port,system,question):return ('miss' if port==8614 and question=='retention' else 'answer',10,.1)
        with patch.object(bench,'serve',return_value=Mock()),patch.object(bench,'ask',side_effect=answer) as ask:
            result=bench.compare(*self.args,repeats=2)
        self.assertEqual(ask.call_count,32)
        self.assertEqual(result['exact+trace']['forgotten'],[{'q':'retention','repeat':0},{'q':'retention','repeat':1}])
        self.assertEqual(result['exact+trace']['probes'],0.)
        self.assertEqual(result['base']['probes'],1.)
        self.assertEqual(result['_checkpoint']['binding']['repeats'],2)

    def test_concurrent_resume_rejected_without_touching_existing_proof(self):
        self.out.write_text('existing partial proof')
        with open(str(self.out)+'.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError,'already running'):bench.compare(*self.args,resume=True)
        self.assertEqual(self.out.read_text(),'existing partial proof')

    def test_opt_in_audit_is_request_scoped_and_missing_hooks_are_explicit(self):
        from v13.sparse_audit import PREFIX,SCHEMA
        log_paths={}
        requests={}
        def serve(binary,model,mem,port,log,**kwargs):
            Path(log).write_text('startup\n');log_paths[port]=Path(log);requests[port]=0
            self.assertTrue(kwargs['audit_firing'])
            return Mock()
        def ask(port,system,question):
            requests[port]+=1
            if port==8613:  # instrumented runner fixture; Combined simulates an old binary
                records=[dict(schema=SCHEMA,event='begin',request=requests[port],slots=1,layer=3),
                         dict(schema=SCHEMA,event='batch',request=requests[port],rows=2,batches=1,applied=[1],guard_blocked=[0])]
                with log_paths[port].open('a') as stream:
                    for record in records:stream.write(PREFIX+json.dumps(record)+'\n')
            return 'answer',10,.1
        with patch.object(bench,'serve',side_effect=serve),patch.object(bench,'ask',side_effect=ask):
            result=bench.compare(*self.args,audit_firing=True)
        self.assertNotIn('native_firing',result['base']['facts_rows'][0])
        self.assertEqual(result['trace']['probes_rows'][0]['native_firing']['request'],4)
        self.assertEqual(result['trace']['facts_rows'][0]['native_firing']['fired_rows'],[0])
        self.assertEqual(result['exact+trace']['facts_rows'][0]['native_firing']['reason'],'NO_PROMPT_MARKER')
        self.assertTrue(result['_checkpoint']['binding']['audit_firing'])

    def test_dead_startup_process_is_reaped_without_polling_an_unrelated_server(self):
        proc=Mock();proc.poll.return_value=1
        with patch.object(bench.subprocess,'Popen',return_value=proc),patch.object(bench.urllib.request,'urlopen') as request:
            with self.assertRaisesRegex(RuntimeError,'server exited during startup'):
                bench.serve(*self.args[:3],8653,str(self.home/'dead.log'),audit_firing=True)
        proc.wait.assert_called_once()
        request.assert_not_called()


if __name__=='__main__':unittest.main()
