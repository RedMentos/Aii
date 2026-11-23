"""WP-N21: residency sizes from measured Anon per model file (thread P's RAM bench), estimate only for unmeasured files."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from v13 import body_sizes as S
from v13 import runners
from v13.operator import Operator
from v13.runtime import Runtime

class FakeRunner:
    alive=set()
    def __init__(self,home,role,model,cfg,purpose='generate'):self.role=role;self.model=model;self.purpose=purpose;self.last_metrics={};FakeRunner.alive.add(id(self))
    def pids(self):return [id(self)] if id(self) in FakeRunner.alive else []
    def unload(self):FakeRunner.alive.discard(id(self));return {'process_reaped':True}

def install(home,key,sha,size_mb):
    p=home/'models'/key/(key+'.gguf');p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,'wb') as f:f.truncate(int(size_mb*2**20))
    return {'model_id':key+'-model','exact_revision':'rev-'+key,'license_id':'x','files':{p.name:{'path':str(p.relative_to(home)),'sha256':sha,'size':p.stat().st_size}},'main_file':p.name,'download_complete':True}

SHIP=S.shipped()
SHA={v['role']:k for k,v in SHIP.items()}

def proc(role,model,anon,extra=(),purpose='generate'):
    return {'role':role,'model':model,'purpose':purpose,'extra':list(extra),'after_work':{'Pss':anon*1.8,'Pss_Anon':anon}}
def bench(android,rows):
    return {'environment':{'android':android,'machine':'aarch64' if android else 'x86_64'},'results':rows}

class Profile(unittest.TestCase):
    def test_shipped_cloud_profile_matches_the_squeeze(self):
        self.assertEqual(set(SHA),{'C3_LANGUAGE','B1_DETAIL','B2_GIST'})
        for e in SHIP.values():
            self.assertEqual(e['size_mib'],round(e['anon_mib']+S.HOT_FILE_MB,1));self.assertEqual(e['evidence'],'CLOUD_X86_LOWER_BOUND')
        total=sum(e['size_mib'] for e in SHIP.values())
        self.assertTrue(1750<total<=2100,total)  # squeeze: 1750 MiB OOM, 2000 MiB runs all three
        self.assertGreater(SHIP[SHA['B2_GIST']]['size_mib'],SHIP[SHA['B1_DETAIL']]['size_mib'])  # B2 (smaller file) needs more: the old estimate had it backwards

    def test_from_bench_takes_only_default_flag_generate_runs_of_known_files(self):
        rows=[{'scenario':'single:B1_DETAIL','processes':[proc('B1_DETAIL','LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf',700.)]},
              {'scenario':'single:B2_GIST','processes':[proc('B2_GIST','Qwen3.5-0.8B-Q4_0.gguf',300.,extra=['--no-repack'])]},
              {'scenario':'single:EMBED','processes':[proc('EMBED','embeddinggemma-300M-Q8_0.gguf',100.,purpose='embed')]},
              {'scenario':'single:B2_GIST','processes':[proc('B2_GIST','custom.gguf',500.)]},
              {'scenario':'combo:C3+B1+B2','processes':[proc('C3_LANGUAGE','LFM2.5-350M-QAD-Q4_0.gguf',900.)]}]
        e=S.from_bench(bench(True,rows))
        self.assertEqual(list(e),[SHA['B1_DETAIL']]);self.assertEqual((e[SHA['B1_DETAIL']]['size_mib'],e[SHA['B1_DETAIL']]['evidence']),(764.,'DEVICE_MEASURED'))
        self.assertEqual(S.from_bench(bench(False,rows[:1]))[SHA['B1_DETAIL']]['evidence'],'CLOUD_X86_LOWER_BOUND')
        self.assertEqual(S.fits({'C3_LANGUAGE':300,'B1_DETAIL':800,'B2_GIST':900},1800),{'C3+B1':True,'C3+B2':True,'C3+B1+B2':False,'need_all_mb':2000,'budget_mb':1800})

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);r=Runtime(self.home);r.close()
        inst={'body':install(self.home,'body',SHA['B1_DETAIL'],60),'gist':install(self.home,'gist',SHA['B2_GIST'],50),'language':install(self.home,'language','c'*64,20)}
        (self.home/'config/models.json').write_text(json.dumps(inst))
        self.p=patch.object(runners,'LlamaRunner',FakeRunner);self.p.start();self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.p.stop();self.tmp.cleanup()
    def experts(self):return self.r.bodies.residency.box.load()[0]['experts']

    def test_residency_uses_measured_sizes_and_a_device_import_overrides(self):
        ex=self.experts()
        self.assertEqual((ex['B1_DETAIL']['size_mb'],ex['B1_DETAIL']['size_source']),(SHIP[SHA['B1_DETAIL']]['size_mib'],'CLOUD_X86_LOWER_BOUND'))
        self.assertEqual(ex['C3_LANGUAGE']['size_source'],'ESTIMATE')  # sha not measured -> old formula
        self.assertAlmostEqual(ex['C3_LANGUAGE']['size_mb'],round(20*1.1+96,1))
        rep=json.loads(Operator(self.r).run(':resources bodies'));self.assertEqual(rep['fits']['budget_mb'],1800)
        self.assertFalse(rep['fits']['C3+B1+B2']);self.assertTrue(rep['fits']['C3+B1'])
        (self.home/'exports').mkdir(exist_ok=True)
        (self.home/'exports/ram.json').write_text(json.dumps(bench(True,[{'scenario':'single:B2_GIST','processes':[proc('B2_GIST','Qwen3.5-0.8B-Q4_0.gguf',1000.)]}])))
        rep=json.loads(Operator(self.r).run(':resources bodies import exports/ram.json'))
        self.assertEqual(rep['bodies']['B2_GIST'],{'size_mb':1064.,'source':'DEVICE_MEASURED'})
        self.assertEqual(self.experts()['B2_GIST']['size_mb'],1064.)  # residency re-synced at once
        json.loads(Operator(self.r).run(':resources bodies reset'));self.assertEqual(self.experts()['B2_GIST']['size_source'],'CLOUD_X86_LOWER_BOUND')
        with self.assertRaises(ValueError):S.import_report(self.r.store,bench(True,[]))

if __name__=='__main__':unittest.main()
