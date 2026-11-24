"""Actual Store/permission tests and explicit nonnative artifact fixtures."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import export_live_output_dataset as exporter
from scripts.train_live_output_adapter import prepare
from v13.common import digest,dumps,file_hash
from v13.config import initialize
from v13.contracts import packet
from v13.learning import Learner
from v13.store import Store
import test_live_output_training as training_tests

class LiveExport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.home=self.root/'home';initialize(self.home)
        self.s=Store(self.home);session=self.s.new_session();self.event=self.s.event(session,'Software test query')
        self.r=SimpleNamespace(store=self.s,session=session,models=SimpleNamespace(revision=lambda _:'SOFTWARE_REVISION'))
        self.learner=Learner(self.r);self.messages=[{'role':'user','content':'Software test query'}];ref=self.s.source(dumps(self.messages),'C3_OUTPUT_CONTEXT')
        self.ctx=packet('OutputAdapterContext','C3_LANGUAGE',self.event['event_id'],self.s.generation_id,[self.event['source_ref'],ref],context_ref=ref,model_revision='SOFTWARE_REVISION',context_revision=self.learner.output_context_revision(),native_role='C3_LANGUAGE')
        self.s.add_packet('OutputAdapterContext',self.ctx);self.learner.output_feedback(self.event['event_id'],'Explicit software label','learn')
        self.d=json.loads(self.s.one("SELECT payload FROM packets WHERE kind='HumanDecision' ORDER BY created DESC LIMIT 1")['payload']);self.id=self.d['packet_id'];self.source=self.d['source_ref']['source_id']
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def selected(self):return exporter.select_label(self.s,self.id,self.source,'SOFTWARE_REVISION',True)
    def test_original_runtime_label_requires_explicit_intent_and_exact_source(self):
        self.assertEqual(self.selected()['messages'],self.messages)
        with self.assertRaisesRegex(ValueError,'--learn'):exporter.select_label(self.s,self.id,self.source,'SOFTWARE_REVISION',False)
        with self.assertRaisesRegex(ValueError,'label/source'):exporter.select_label(self.s,self.id,'wrong','SOFTWARE_REVISION',True)
        with self.assertRaisesRegex(ValueError,'revision'):exporter.select_label(self.s,self.id,self.source,'OTHER_REVISION',True)
    def test_revocation_deletion_and_newer_context_correction_refused(self):
        with self.s.tx() as c:c.execute("UPDATE feedback SET permission='record' WHERE source_id=?",(self.source,))
        with self.assertRaisesRegex(ValueError,'revoked'):self.selected()
        with self.s.tx() as c:c.execute("UPDATE feedback SET permission='learn' WHERE source_id=?",(self.source,))
        self.learner.output_feedback(self.event['event_id'],'Newer explicit label','learn')
        with self.assertRaisesRegex(ValueError,'superseded'):self.selected()
        with self.s.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(self.source,))
        with self.assertRaisesRegex(ValueError,'gelöschter'):self.selected()
    def test_export_derivation_persists_new_packet_original_bytes_unchanged(self):
        selected=self.selected();raw=selected['original_payload'];path=self.root/'observed.json';path.write_text(dumps({'software_fixture':True}))
        derived=exporter.persist_export_decision(self.s,selected,path,{'software_fixture':True},True)
        self.assertNotEqual(derived['packet_id'],self.id);self.assertEqual(derived['value'],self.d['value'])
        self.assertFalse(derived['export_binding']['human_saw_future_features']);self.assertEqual(derived['export_binding']['original_human_decision_payload_sha256'],digest(raw))
        self.assertEqual(self.s.one('SELECT payload FROM packets WHERE id=?',(self.id,))['payload'],raw)
        self.assertEqual(self.s.read_source(derived['export_binding']['observed_source_ref']),path.read_text())
        self.assertEqual(self.selected()['decision'],self.d)
    def test_active_installed_coordinator_refuses_before_native_binding(self):
        with patch.object(exporter,'bind_installed',side_effect=AssertionError('native binding must not start')) as native:
            with self.assertRaisesRegex(RuntimeError,'läuft bereits'):exporter.capture(self.home,self.root/'blocked',self.id,self.source,True)
            native.assert_not_called()
        report=json.loads((self.root/'blocked/capture-report.json').read_text());self.assertFalse(report['native_calls'])

    def fragment(self,index,target,query):
        f=training_tests.LiveTraining();f.setUp();self.addCleanup(f.tearDown)
        f.context['messages'][-1]['content']=query;f.write('query_source',query,text=True);f.write('context',f.context);context_sha=digest(dumps(f.context))
        for name in ('tokens','features','result','observed'):
            value=json.loads((f.root/(name+'.json')).read_text())
            if name=='observed':value['native_context_binding']['context_source_sha256']=context_sha
            else:value['context_source_sha256']=context_sha
            if name=='result':value['handle']['context_source_sha256']=context_sha
            f.write(name,value)
        # Final raw hashes must follow exact updated source/token/feature bytes.
        result=json.loads((f.root/'result.json').read_text());result['token_file_sha256']=f.entry['tokens']['sha256'];result['handle']['token_file_sha256']=f.entry['tokens']['sha256'];result['handle']['features_sha256']=f.entry['features']['sha256'];f.write('result',result)
        observed=json.loads((f.root/'observed.json').read_text());observed['native_context_binding']['features_sha256']=f.entry['features']['sha256'];f.write('observed',observed)
        query_ref={'source_id':'SOFTWARE_QUERY_'+str(index),'sha256':digest(query),'char_start':0,'char_end':len(query),'modality':'text'}
        ref={'source_id':'SOFTWARE_CONTEXT_'+str(index),'sha256':digest(dumps(f.context['messages'])),'char_start':0,'char_end':len(dumps(f.context['messages'])),'modality':'text'}
        ctx=packet('OutputAdapterContext','C3_LANGUAGE','SOFTWARE_EVENT','SOFTWARE_GENERATION',[query_ref,ref],context_ref=ref,model_revision='SOFTWARE_REVISION',context_revision='SOFTWARE_CONTEXT_REVISION',native_role='C3_LANGUAGE')
        event=packet('EventEnvelope','A0_SOURCE','SOFTWARE_EVENT','SOFTWARE_GENERATION',[query_ref],source_ref=query_ref,authority='AUTHORITATIVE',kind='USER_TEXT')
        selection={'context_ref':ref,'context_packet_id':ctx['packet_id'],'source_refs':ctx['provenance'],'context_revision':ctx['context_revision'],'model_revision':ctx['model_revision'],'target_position':0}
        original=packet('HumanDecision','F5_HUMAN_CONTROL','SOFTWARE_EVENT','SOFTWARE_GENERATION',[f.decision['source_ref']],kind='output',value=f.label,learning_permission='learn',source_ref=f.decision['source_ref'],selection=selection)
        f.write('original',original);f.write('original_context',ctx);f.write('original_event',event)
        decision=packet('HumanDecision','F5_HUMAN_CONTROL','SOFTWARE_EVENT','SOFTWARE_GENERATION',kind='output',value=f.label,learning_permission='learn',source_ref=original['source_ref'],selection=dict(selection,feature_abi=f.abi,live_observation_sha256=f.entry['observed']['sha256']),export_binding={'original_human_decision_packet_id':original['packet_id'],'original_human_decision_payload_sha256':f.entry['original']['sha256'],'original_label_source_ref':original['source_ref'],'human_saw_future_features':False,'observed_source_ref':{'sha256':f.entry['observed']['sha256']}})
        f.write('human_decision',decision);tokenization=json.loads((f.root/'label_tokenization.json').read_text());tokenization['token_ids'][0]=target;f.write('label_tokenization',tokenization)
        fragment={'schema':exporter.FRAGMENT,'authority':'EXPLICIT_OPERATOR_LEARN_REEXPORT','feature_abi':f.abi,'observation':{n:f.entry[n] for n in exporter.NAMES},'original_human_decision':f.entry['original'],'original_context_packet':f.entry['original_context'],'original_event':f.entry['original_event'],'export_decision_packet_id':decision['packet_id'],'target_token_id':target}
        path=f.root/'fragment.json';path.write_text(dumps(fragment));return path
    def test_offline_assembly_preserves_label_lineage_and_is_trainer_usable(self):
        paths=[self.fragment(0,1,'Distinct software query A'),self.fragment(1,2,'Distinct software query B')]
        with patch.object(exporter,'bind_installed',side_effect=AssertionError('offline assembly must not bind native')):
            report=exporter.assemble(paths,self.root/'assembled')
        inp,_,_=prepare(self.root/'assembled/dataset.json');self.assertEqual(inp['target_indices'],[0,1]);self.assertEqual(report['observations'],2);self.assertFalse(report['native_calls'])
        for i,path in enumerate(paths):
            fragment=json.loads(path.read_text());copied=self.root/'assembled'/('observation-'+str(i))/'original_human_decision.json'
            self.assertEqual(file_hash(copied),fragment['original_human_decision']['sha256'])
    def test_import_refuses_changed_original_decision_and_mixed_abi(self):
        paths=[self.fragment(0,1,'Distinct software query A'),self.fragment(1,2,'Distinct software query B')]
        fragment=json.loads(paths[0].read_text());original=paths[0].parent/fragment['original_human_decision']['path'];original.write_text('{}')
        with self.assertRaisesRegex(ValueError,'bytes changed'):exporter.assemble(paths,self.root/'tamper')
        paths=[self.fragment(2,1,'Distinct software query C'),self.fragment(3,2,'Distinct software query D')]
        second=json.loads(paths[1].read_text());second['feature_abi']['n_batch']=512;paths[1].write_text(dumps(second))
        with self.assertRaisesRegex(ValueError,'ABI mismatch'):exporter.assemble(paths,self.root/'mixed')

if __name__=='__main__':unittest.main()
