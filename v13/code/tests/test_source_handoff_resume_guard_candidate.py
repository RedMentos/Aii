"""No native inference: negative state-forgery and row ledger tests."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
try:
    from scripts import source_handoff_resume_guard_candidate as guard
except ModuleNotFoundError:
    import source_handoff_resume_guard_candidate as guard


class StrictResumeGuard(unittest.TestCase):
    def row(self,fixture='Mira',arm='baseline',status='RECORDED'):
        return {'fixture':fixture,'arm':arm,'status':status,
                'score':{'utility':0.5,'exact':False},'delivered_prior_quotes':[],
                'oracle_visible_to_native': False, 'processes_reaped': True,
                'checks': {k: True for k in guard.NATIVE_CHECKS},
                'offer':{'native_metrics':{'status':'FINAL'}},
                'consumer_metrics':{'status':'FINAL'}}

    def report(self,rows=None,status='RUNNING'):
        rows=rows if rows is not None else [self.row()]
        return {'schema':'SOURCE_HANDOFF_ABLATION_V1','preregistration_sha256':'same-reg',
                'canonical_gate_pass':False,'learned_semantic_utility_proven':False,'phone_measured':False,
                'status':status,'rows':rows,
                'row_sha256':{r['fixture']+'/'+r['arm']:guard.row_sha(r) for r in rows},
                'summary':guard.expected_summary(rows) if rows else None}

    def test_valid_partial_resume_retains_completed_rows(self):
        r=self.report()
        self.assertEqual(guard.validate_resume(r,'same-reg'),{('Mira','baseline')})

    def test_separate_gate_forgery_not_hidden_by_valid_row_hashes(self):
        for field in guard.GATE_FIELDS:
            with self.subTest(field=field):
                r=self.report();r[field]=True
                with self.assertRaisesRegex(ValueError,'Unproven'):guard.validate_resume(r,'same-reg')
                r[field]='false'
                with self.assertRaisesRegex(ValueError,'Unproven'):guard.validate_resume(r,'same-reg')

    def test_cannot_forge_completed_status_on_partial_or_failing_rows(self):
        r=self.report(status='RECORDED_DIAGNOSIS')
        r['installed_artifacts_unchanged']=True
        with self.assertRaisesRegex(ValueError,'incomplete/failed'):guard.validate_resume(r,'same-reg')
        rows=[self.row(f,a) for f in guard.FIXTURES for a in guard.ARMS]
        rows[-1]['status']='ERROR'
        r=self.report(rows,status='RECORDED_DIAGNOSIS');r['installed_artifacts_unchanged']=True
        with self.assertRaisesRegex(ValueError,'incomplete/failed'):guard.validate_resume(r,'same-reg')

    def test_verified_finished_report_complete_after_true_binding(self):
        rows=[self.row(f,a) for f in guard.FIXTURES for a in guard.ARMS]
        r=self.report(rows,status='RECORDED_DIAGNOSIS')
        r['installed_artifacts_unchanged']=True
        self.assertEqual(len(guard.validate_resume(r,'same-reg')),16)
        r['installed_artifacts_unchanged']=False
        with self.assertRaisesRegex(ValueError,'artifacts'):guard.validate_resume(r,'same-reg')

    def test_duplicate_and_extra_hash_key_are_refused(self):
        r=self.report();r['row_sha256']['Lumen/baseline']='0'*64
        with self.assertRaisesRegex(ValueError,'ledger changed'):guard.validate_resume(r,'same-reg')
        r=self.report();r['rows'].append(copy.deepcopy(r['rows'][0]))
        with self.assertRaisesRegex(ValueError,'row keys'):guard.validate_resume(r,'same-reg')

    def test_modified_row_and_summary_refused_independently(self):
        r=self.report();r['rows'][0]['score']['utility']=0.1
        with self.assertRaisesRegex(ValueError,'row bytes'):guard.validate_resume(r,'same-reg')
        r=self.report();r['summary']['baseline']['exact_decisions']=1
        with self.assertRaisesRegex(ValueError,'summary'):guard.validate_resume(r,'same-reg')

    def test_unknown_lifecycle_and_malformed_score_refused(self):
        r=self.report();r['status']='UTILITY_PASS';
        with self.assertRaisesRegex(ValueError,'lifecycle'):guard.validate_resume(r,'same-reg')
        r=self.report();r['rows'][0]['score']['utility']=True;r['row_sha256']={r['rows'][0]['fixture']+'/'+r['rows'][0]['arm']:guard.row_sha(r['rows'][0])}
        with self.assertRaisesRegex(ValueError,'Malformed utility'):guard.validate_resume(r,'same-reg')

    def test_interrupted_state_preserved(self):
        r=self.report(status='INTERRUPTED')
        with self.assertRaisesRegex(ValueError,'interrupted last row'):guard.validate_resume(r,'same-reg')
        r['rows'][0]['status']='INTERRUPTED'
        r['row_sha256']={'Mira/baseline':guard.row_sha(r['rows'][0])}
        r['summary']=guard.expected_summary(r['rows'])
        self.assertEqual(guard.validate_resume(r,'same-reg'),{('Mira','baseline')})


    def test_out_of_order_rows_refused_despite_valid_sha_ledgers(self):
        rows=[self.row('Mira','baseline'), self.row('Lumen','baseline')]
        with self.assertRaisesRegex(ValueError,'contiguous'):
            guard.validate_resume(self.report(rows),'same-reg')
        rows=[self.row('Mira','state_off')]
        with self.assertRaisesRegex(ValueError,'contiguous'):
            guard.validate_resume(self.report(rows),'same-reg')

    def test_recorded_native_requires_reaped_process_and_no_oracle(self):
        for field,bad in [('processes_reaped',False),('oracle_visible_to_native',True)]:
            with self.subTest(field=field):
                r=self.report()
                r['rows'][0][field]=bad
                r['row_sha256']={'Mira/baseline': guard.row_sha(r['rows'][0])}
                with self.assertRaisesRegex(ValueError,'native evidence'):
                    guard.validate_resume(r,'same-reg')

    def test_recorded_native_rejects_missing_false_or_nonboolean_checks(self):
        for bad in (False,None,1,'true'):
            with self.subTest(bad=bad):
                r=self.report();r['rows'][0]['checks']['real_C3_final']=bad
                r['row_sha256']={'Mira/baseline': guard.row_sha(r['rows'][0])}
                with self.assertRaisesRegex(ValueError,'native evidence'):
                    guard.validate_resume(r,'same-reg')

    def test_final_native_statuses_required_for_recorded(self):
        for where in ('offer','consumer_metrics'):
            r=self.report()
            if where=='offer':r['rows'][0]['offer']['native_metrics']['status']='DEADLINE'
            else:r['rows'][0]['consumer_metrics']['status']='DEADLINE'
            r['row_sha256']={'Mira/baseline': guard.row_sha(r['rows'][0])}
            with self.assertRaisesRegex(ValueError,'native evidence'):
                guard.validate_resume(r,'same-reg')

    def test_no_rows_cannot_claim_nonempty_summary(self):
        r=self.report([],status='RUNNING')
        self.assertEqual(guard.validate_resume(r,'same-reg'),set())
        r['summary']={'baseline':{}}
        with self.assertRaisesRegex(ValueError,'summary'):
            guard.validate_resume(r,'same-reg')

    def test_diagnostic_error_row_not_falsely_promoted(self):
        r=self.report([self.row(status='ERROR')])
        self.assertEqual(guard.validate_resume(r,'same-reg'),{('Mira','baseline')})
        r['status']='RECORDED_DIAGNOSIS';r['installed_artifacts_unchanged']=True
        with self.assertRaisesRegex(ValueError,'incomplete/failed'):
            guard.validate_resume(r,'same-reg')


    def test_malformed_offer_and_metrics_fail_closed(self):
        for key,bad in [('offer','not a dict'),('consumer_metrics','not a dict')]:
            r=self.report();r['rows'][0][key]=bad
            r['row_sha256']={'Mira/baseline':guard.row_sha(r['rows'][0])}
            with self.assertRaisesRegex(ValueError,'native evidence'):
                guard.validate_resume(r,'same-reg')

    def test_readonly_cli_validates_preregistration_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); reg=root/'prereg.json'; report=root/'report.json'
            reg.write_text(json.dumps({'schema':'SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1',
                 'arm_order':list(guard.ARMS),'fixtures':[{'id':i} for i in guard.FIXTURES]}))
            expected=hashlib.sha256(reg.read_bytes()).hexdigest()
            r=self.report();r['preregistration_sha256']=expected
            report.write_text(json.dumps(r))
            before=report.read_bytes()
            receipt=guard.audit_files(reg,report)
            self.assertEqual(receipt['status'],'RESUME_LEDGER_VALID_NOT_UTILITY_PASS')
            self.assertEqual(receipt['rows'],1)
            self.assertIs(receipt['source_and_model_binding_verified'],False)
            self.assertEqual(report.read_bytes(),before)
            result=subprocess.run([sys.executable,str(Path(guard.__file__)),
               '--preregistration',str(reg),'--report',str(report)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('delivered_prior_quotes',result.stdout)
            self.assertEqual(json.loads(result.stdout)['remaining_rows'],15)
            reg.write_bytes(reg.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'preregistration changed'):
                guard.audit_files(reg,report)

    def test_registration_rejects_non_dict_fixture_and_extra_slots(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);reg=root/'pre.json';report=root/'res.json'
            original={'schema':'SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1',
                 'arm_order':list(guard.ARMS),'fixtures':[{'id':i} for i in guard.FIXTURES]}
            for extra in ([None], [{'id':'UNLISTED'}]):
                value=copy.deepcopy(original);value['fixtures']+=extra
                reg.write_text(json.dumps(value))
                r=self.report();r['preregistration_sha256']=hashlib.sha256(reg.read_bytes()).hexdigest()
                report.write_text(json.dumps(r))
                with self.assertRaisesRegex(ValueError,'preregistration'):
                    guard.audit_files(reg,report)

    def test_cli_refuses_modified_report_or_symlink_without_leakage(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);reg=root/'pre.json';report=root/'res.json'
            reg.write_text(json.dumps({'schema':'SOURCE_HANDOFF_ABLATION_PREREGISTRATION_V1',
                 'arm_order':list(guard.ARMS),'fixtures':[{'id':i} for i in guard.FIXTURES]}))
            r=self.report();r['preregistration_sha256']=hashlib.sha256(reg.read_bytes()).hexdigest()
            r['rows'][0]['score']['utility']=0.88
            report.write_text(json.dumps(r))
            cmd=[sys.executable,str(Path(guard.__file__)),'--preregistration',str(reg),'--report',str(report)]
            out=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(out.returncode,2)
            self.assertEqual(json.loads(out.stderr)['status'],'RESUME_LEDGER_REJECTED')
            link=root/'link.json';link.symlink_to(report)
            out=subprocess.run([*cmd[:-1],str(link)],capture_output=True,text=True)
            self.assertEqual(out.returncode,2)

    def test_changed_registration_refused(self):
        with self.assertRaisesRegex(ValueError,'preregistration changed'):
            guard.validate_resume(self.report(),'other-reg')

if __name__=='__main__':unittest.main()
