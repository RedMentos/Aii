"""WP-S3 in AG6: :forget blocks on active LoRA, zeroes sparse-memory slots (also in rollback targets), answer keys."""
from pathlib import Path
import tempfile
import unittest
from v13.runtime import Runtime
from v13.lora_trainer import AdapterRegistry
from v13.memory_trainer import ROLE,answer_keys,check_forget
from v13.common import file_hash
try:
    import torch
except ImportError:torch=None

class MemoryTrainerGlue(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
        e=self.s.event(self.r.session,'What is the name of my cat?');self.r.memory.feedback(e['event_id'],'fact','Mitzi')
        self.mid=self.s.one('SELECT id FROM memories ORDER BY created DESC LIMIT 1')['id']
        self.model=self.home/'c3.gguf';self.model.write_bytes(b'model')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_answer_keys(self):
        self.assertEqual(answer_keys({'prompt':'What is the name of my cat?','target':'Your cat is called Mitzi.'}),['mitzi'])
        self.assertEqual(answer_keys({'prompt':'Where do I work?','target':'You work at the Kranich bakery in Leipzig.'}),['kranich'])
        self.assertEqual(answer_keys({'prompt':'What is my favourite colour?','target':'Your favourite colour is teal.'}),['teal'])
        self.assertEqual(answer_keys({'prompt':'x','target':'y','answer_keys':['k']}),['k'])
    def test_forget_blocks_while_fact_is_in_active_lora(self):
        a=self.home/'a.gguf';a.write_bytes(b'lora')
        self.s.set_state('G6_WEIGHT_CONSOLIDATION',{'revision':'g6-weights-v1','batches':{'g1':{'items':[{'memory_id':self.mid}]}},'consolidated':[self.mid],'order':['g1']})
        AdapterRegistry(self.s).activate('C3_LANGUAGE',a,file_hash(a),file_hash(self.model),'g1')
        with self.assertRaises(ValueError):check_forget(self.s,self.mid)
        with self.assertRaises(ValueError):self.r.memory.forget(self.mid)
        AdapterRegistry(self.s).deactivate('C3_LANGUAGE','g1');check_forget(self.s,self.mid)
    @unittest.skipIf(torch is None,'torch missing')
    def test_forget_zeroes_slots_in_bound_and_previous_artifact(self):
        def art(name,slots):
            n=8;st={'values':torch.ones(n,4),'hkeys':torch.ones(n,4),'written':torch.ones(n),'ent':torch.zeros(n,2,dtype=torch.long)}
            p=self.home/name;torch.save({'revision':'wp-s3-sparse-memory-v1','state':st,'slots':list(slots),'slot_items':{s:m for s,m in slots.items()}},p);return p
        old=art('old.pt',{0:self.mid});new=art('new.pt',{0:self.mid,1:'other'})
        reg=AdapterRegistry(self.s);ms=file_hash(self.model)
        reg.activate(ROLE,old,file_hash(old),ms,'g1');reg.activate(ROLE,new,file_hash(new),ms,'g2')
        self.r.memory.forget(self.mid)
        for p in (old,new):
            st=torch.load(p);self.assertEqual(float(st['state']['values'][0].abs().sum()),0.);self.assertEqual(float(st['state']['written'][0]),0.)
            self.assertNotIn(self.mid,[str(v) for v in st['slot_items'].values()])
        st=torch.load(new);self.assertEqual(float(st['state']['written'][1]),1.)  # other fact untouched
        cur=reg.report()['active'][ROLE];self.assertEqual(cur['sha256'],file_hash(new));self.assertEqual(cur['previous']['sha256'],file_hash(old))

def write_bin(path,rows,hid=4,ew=2):
    """Tiny V13SMEM1 file + row map like sparse_memory.export_native writes (numpy only)."""
    import json,struct
    n=len(rows);b=b'V13SMEM1'+struct.pack('<6i',7,hid,n,ew,32,1)+struct.pack('<2f',.01,1.)+struct.pack('<%df'%hid,*[0.]*hid)
    b+=struct.pack('<%df'%(n*hid),*[1.]*(n*hid))+struct.pack('<%df'%n,*[.5]*n)+struct.pack('<%df'%(n*hid),*[1.]*(n*hid))+struct.pack('<%di'%(n*ew),*[5]*(n*ew))
    Path(path).write_bytes(b);Path(str(path)+'.items.json').write_text(json.dumps({'source_pt':None,'rows':rows}))
    return Path(path)

def read_bin(path):
    import struct
    b=Path(path).read_bytes();lay,hid,n,ew,_,_=struct.unpack_from('<6i',b,8);o=40+4*hid
    keys=struct.unpack_from('<%df'%(n*hid),b,o);o+=4*n*hid;theta=struct.unpack_from('<%df'%n,b,o);o+=4*n
    vals=struct.unpack_from('<%df'%(n*hid),b,o);o+=4*n*hid;ent=struct.unpack_from('<%di'%(n*ew),b,o)
    return hid,ew,keys,theta,vals,ent

class NativeMemoryLive(MemoryTrainerGlue):
    def test_forget_native_bin_without_torch(self):
        old=write_bin(self.home/'old.bin',[self.mid]);new=write_bin(self.home/'new.bin',[self.mid,'other'])
        reg=AdapterRegistry(self.s);ms=file_hash(self.model)
        reg.activate(ROLE,old,file_hash(old),ms,'g1');reg.activate(ROLE,new,file_hash(new),ms,'g2')
        self.r.memory.forget(self.mid)
        hid,ew,keys,theta,vals,ent=read_bin(new)
        self.assertEqual(sum(map(abs,vals[:hid])),0.);self.assertEqual(sum(map(abs,keys[:hid])),0.);self.assertGreater(theta[0],1e8);self.assertEqual(set(ent[:ew]),{-1})
        self.assertEqual(vals[hid:],(1.,)*hid);self.assertEqual(theta[1],.5)  # other fact untouched
        self.assertEqual(read_bin(old)[4],(0.,)*hid)  # rollback target cleaned too
        import json
        self.assertEqual(json.loads(Path(str(new)+'.items.json').read_text())['rows'],[None,'other'])
        cur=reg.report()['active'][ROLE];self.assertEqual(cur['sha256'],file_hash(new))
    def test_superseded_correction_leaves_live_memory(self):
        b=write_bin(self.home/'m.bin',[self.mid,'rating:e1']);AdapterRegistry(self.s).activate(ROLE,b,file_hash(b),file_hash(self.model),'g1')
        eid=self.s.one('SELECT event_id FROM memories WHERE id=?',(self.mid,))['event_id']
        new=self.r.memory.feedback(eid,'fact','Luna')  # same key: the Mitzi row becomes inactive
        self.assertNotEqual(new,self.mid);self.assertEqual(self.s.one('SELECT active FROM memories WHERE id=?',(self.mid,))['active'],0)
        hid,ew,keys,theta,vals,ent=read_bin(b)
        self.assertEqual(vals[:hid],(0.,)*hid);self.assertEqual(vals[hid:],(1.,)*hid)  # rating row is not a memory row: kept
        self.assertEqual(AdapterRegistry(self.s).report()['active'][ROLE]['sha256'],file_hash(b))
    def test_runner_memory_only_for_matching_hashes(self):
        import json
        from v13.memory_server import runner_memory,MANIFEST
        b=write_bin(self.home/'m.bin',['x']);binary=self.home/'bin/llama-server-mem';binary.parent.mkdir(exist_ok=True)
        binary.write_bytes(b'server');self.assertIsNone(runner_memory(self.home,'C3_LANGUAGE',self.model))  # nothing bound
        AdapterRegistry(self.s).activate(ROLE,b,file_hash(b),file_hash(self.model),'g1')
        self.assertIsNone(runner_memory(self.home,'C3_LANGUAGE',self.model))  # no build manifest
        (self.home/MANIFEST).write_text(json.dumps({'binary_sha256':file_hash(binary)}))
        m=runner_memory(self.home,'C3_LANGUAGE',self.model)
        self.assertEqual(m,{'binary':str(binary),'env':{'V13_MEMORY_FILE':str(b)}})
        other=self.home/'other.gguf';other.write_bytes(b'x');self.assertIsNone(runner_memory(self.home,'C3_LANGUAGE',other))
        binary.write_bytes(b'changed');self.assertIsNone(runner_memory(self.home,'C3_LANGUAGE',self.model))
        binary.write_bytes(b'server');b.write_bytes(b.read_bytes()+b'x');self.assertIsNone(runner_memory(self.home,'C3_LANGUAGE',self.model))
    def test_patch_source_idempotent(self):
        from v13.memory_server import patch_source
        srv=self.home/'src/tools/server';srv.mkdir(parents=True)
        (srv/'server.cpp').write_text('int main(){ if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_SERVER)) return 1; }\n')
        (srv/'server-context.cpp').write_text('x;\n                        slot.state = SLOT_STATE_PROCESSING_PROMPT;\ny;\n')
        h=patch_source(self.home/'src');self.assertEqual(patch_source(self.home/'src'),h)
        s=(srv/'server.cpp').read_text();c=(srv/'server-context.cpp').read_text()
        self.assertEqual(s.count('v13_parse_and_attach(argc'),1);self.assertNotIn('common_params_parse(argc',s)
        self.assertEqual(c.count('v13_new_prompt(input_tokens);'),1);self.assertTrue((srv/'v13_memory_hook.h').is_file())

if __name__=='__main__':unittest.main()
