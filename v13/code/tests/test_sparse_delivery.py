"""WP-T9 shadow inventories with synthetic native bytes; no native recall/firing proof."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.common import file_hash
from v13.lora_trainer import AdapterRegistry
from v13.memory_trainer import ROLE,merge_training_lineage,forget_memory
from v13.memory_server import MANIFEST,runner_memory,captured_delivery_binding,shadow_delivery
from v13.sparse_memory import DELIVERY_SCHEMA,fact_item_bindings,native_items_path


class SparseDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
        e=self.s.event(self.r.session,'What is the name of my cat?')
        self.r.memory.feedback(e['event_id'],'fact','Mitzi')
        self.memory=self.r.memory.recall('cat',self.r.session)[0];self.mid=self.memory['id']
        self.model=self.home/'c3.gguf';self.model.write_bytes(b'synthetic model')
        self.binary=self.home/'bin/llama-server-mem';self.binary.write_bytes(b'synthetic server')
        (self.home/MANIFEST).write_text(json.dumps({'binary_sha256':file_hash(self.binary)}))
        self.registry=AdapterRegistry(self.s)
        self.path=self.make_native('current.bin')
        self.activate(self.path,'batch1')
    def tearDown(self):
        self.r.close();self.tmp.cleanup()
    def make_native(self,name,legacy=False):
        p=self.home/name;hid=4;ew=2
        p.write_bytes(b'V13SMEM1'+struct.pack('<6i',7,hid,1,ew,32,1)+struct.pack('<2f',.01,1.)+
                      struct.pack('<4f',0,0,0,0)+struct.pack('<4f',1,0,0,0)+struct.pack('<f',.5)+
                      struct.pack('<4f',1,1,1,1)+struct.pack('<2i',5,-1))
        side={'source_pt':None,'rows':[self.mid],'forgotten':[]}
        if not legacy:
            side.update(schema=DELIVERY_SCHEMA,native_sha256=file_hash(p),item_bindings=fact_item_bindings([
                {'memory_id':self.mid,'kind':'fact','prompt':self.memory['key_text'],
                 'target':self.memory['value'],'source_ref':self.memory['source_ref']}]))
        native_items_path(p).write_text(json.dumps(side));return p
    def activate(self,path,batch):
        self.registry.activate(ROLE,path,file_hash(path),file_hash(self.model),batch)
        return captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
    def inventory(self,binding=None,memories=None):
        if binding is None:binding=captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
        return shadow_delivery(self.s,self.home,'C3_LANGUAGE',self.model,binding,
                               [self.memory] if memories is None else memories)
    def edit_side(self,change):
        side=json.loads(native_items_path(self.path).read_text());change(side)
        native_items_path(self.path).write_text(json.dumps(side))
    def test_bound_fact_is_inventory_only_exact_retained(self):
        result=self.inventory();self.assertEqual(result['candidates'],[self.mid])
        self.assertTrue(result['exact_retained']);self.assertEqual(result['mode'],'SHADOW')
        self.assertEqual(result['firing'],'UNMEASURED');self.assertEqual(result['provenance'],[self.memory['source_ref']])
    def test_legacy_or_missing_map_runs_but_cannot_propose(self):
        p=self.make_native('legacy.bin',legacy=True);self.activate(p,'legacy')
        self.assertIsNotNone(runner_memory(self.home,'C3_LANGUAGE',self.model))
        self.assertIsNone(captured_delivery_binding(self.home,'C3_LANGUAGE',self.model))
        self.assertEqual(self.inventory()['candidates'],[])
        native_items_path(p).unlink();self.assertIsNotNone(runner_memory(self.home,'C3_LANGUAGE',self.model))
        self.assertEqual(self.inventory()['candidates'],[])
    def test_unapproved_sidecar_tamper_invalidates_snapshot(self):
        loaded=captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
        self.edit_side(lambda side:side['item_bindings'][self.mid].update(target='Luna'))
        self.assertIsNone(captured_delivery_binding(self.home,'C3_LANGUAGE',self.model))
        self.assertEqual(self.inventory(loaded)['candidates'],[])
    def test_model_native_and_binary_changes_fail_closed(self):
        for p in (self.model,self.path,self.binary):
            original=p.read_bytes();loaded=captured_delivery_binding(self.home,'C3_LANGUAGE',self.model)
            p.write_bytes(original+b'tampered')
            self.assertEqual(self.inventory(loaded)['candidates'],[]);p.write_bytes(original)
    def test_approved_content_or_provenance_mismatch_excluded(self):
        self.edit_side(lambda side:side['item_bindings'][self.mid].update(prompt='dog'))
        self.activate(self.path,'changed-key');self.assertEqual(self.inventory()['candidates'],[])
        self.edit_side(lambda side:side['item_bindings'][self.mid].update(prompt=self.memory['key_text'],
                         source_ref=dict(self.memory['source_ref'],sha256='0'*64)))
        self.activate(self.path,'changed-source');self.assertEqual(self.inventory()['candidates'],[])
    def test_inactive_or_deleted_source_excluded(self):
        with self.s.tx() as c:c.execute('UPDATE memories SET active=0 WHERE id=?',(self.mid,))
        self.assertEqual(self.inventory()['candidates'],[])
        with self.s.tx() as c:
            c.execute('UPDATE memories SET active=1 WHERE id=?',(self.mid,))
            c.execute('UPDATE sources SET deleted=1 WHERE id=?',(self.memory['source_id'],))
        self.assertEqual(self.inventory()['candidates'],[])
    def test_indexes_style_and_ratings_not_delivery_candidates(self):
        for changed in ({'consolidation':{'members':[self.mid]}},{'kind':'style'},
                        {'id':'rating:foo'},{'id':'index:foo'}):
            self.assertEqual(self.inventory(memories=[dict(self.memory,**changed)])['candidates'],[])
    def test_zero_value_unreachable_threshold_or_empty_guard_excluded(self):
        original=self.path.read_bytes()
        for offset,fmt,values in ((76,'<4f',(0,0,0,0)),(72,'<f',(1e9,)),(92,'<2i',(-1,-1))):
            b=bytearray(original);struct.pack_into(fmt,b,offset,*values);self.path.write_bytes(b)
            self.edit_side(lambda side:side.update(native_sha256=file_hash(self.path)))
            self.activate(self.path,'zeroed');self.assertEqual(self.inventory()['candidates'],[])
    def test_malformed_native_size_or_row_map_excluded(self):
        self.edit_side(lambda side:side.update(rows=[]));self.activate(self.path,'bad-rows')
        self.assertEqual(self.inventory()['reason'],'INVALID_NATIVE_ROW_MAP')
        self.path.write_bytes(self.path.read_bytes()[:-1]);self.edit_side(lambda side:side.update(native_sha256=file_hash(self.path)))
        self.activate(self.path,'truncated');self.assertEqual(self.inventory()['reason'],'INVALID_NATIVE_ROW_MAP')
    def test_accumulation_preserves_integer_slot_lineage_and_rejects_changed_fact(self):
        binding=json.loads(native_items_path(self.path).read_text())['item_bindings'][self.mid]
        old={'slot_items':{0:self.mid},'slots':[0],'item_bindings':{self.mid:binding},'forgotten':['gone']}
        new={'slot_items':{1:'new'},'slots':[1],'item_bindings':{'new':dict(binding,prompt='dog')}}
        merged=merge_training_lineage(old,new)
        self.assertEqual(merged['slot_items'],{0:self.mid,1:'new'});self.assertEqual(merged['slots'],[0,1])
        self.assertEqual(set(merged['item_bindings']),{self.mid,'new'});self.assertEqual(merged['forgotten'],['gone'])
        with self.assertRaises(ValueError):merge_training_lineage(old,{'item_bindings':{self.mid:dict(binding,target='Luna')}})
    def test_forget_updates_map_binding_and_rollback_cannot_restore_fact(self):
        old=self.path;new=self.make_native('new.bin');loaded=self.activate(new,'batch2')
        self.assertEqual(forget_memory(self.s,self.mid),1)
        current=self.registry.report()['active'][ROLE]
        for p,binding in ((new,current),(old,current['previous'])):
            side=json.loads(native_items_path(p).read_text())
            self.assertEqual(side['rows'],[None]);self.assertNotIn(self.mid,side['item_bindings'])
            self.assertEqual(side['native_sha256'],file_hash(p));self.assertEqual(binding['sidecar_sha256'],file_hash(native_items_path(p)))
        self.assertEqual(self.inventory(loaded)['candidates'],[])
        self.registry.deactivate(ROLE,'batch2');self.assertEqual(self.inventory()['candidates'],[])
    def test_training_bindings_only_facts(self):
        items=[{'memory_id':str(n),'kind':kind,'prompt':'p','target':'t','source_ref':self.memory['source_ref']}
               for n,kind in enumerate(('fact','style','rated_answer','sdft'))]
        self.assertEqual(set(fact_item_bindings(items)),{'0'})


if __name__=='__main__':unittest.main()
