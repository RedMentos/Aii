"""Isolated Store-coordinated native approval reader candidate.

Live runtime sources stay frozen. Snapshot files pin adapter bytes before the
native child opens them; health polling never holds the Store mutex.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import types

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT='docs/proofs/continuation-20261011/approval-reader-runtime-baseline'
NAMES=('v13/runners.py','v13/runtime.py')

METHODS='''    @contextlib.contextmanager
    def _approval_guard(self,cancel,deadline):
        # Approval can hold the writer mutex across filesystem recovery. A
        # reader waiting for it must still honour its cancellation/deadline.
        check(cancel,deadline)
        if self.approval_store is None:
            yield
            return
        acquired=False
        try:
            while not acquired:
                check(cancel,deadline)
                acquired=self.approval_store.mutex.acquire(timeout=max(0.,min(.05,deadline-time.monotonic())))
            check(cancel,deadline)
            yield
        finally:
            if acquired:self.approval_store.mutex.release()
    def _verify_approval_mirror(self):
        # Caller holds Store.mutex. The database remains authoritative even
        # when a failed mirror recovery leaves an ACTIVATING journal behind.
        if self.approval_store is None:return
        from .lora_trainer import REGISTRY_KEY,MIRROR
        active=(self.approval_store.state(REGISTRY_KEY,None)[0] or {}).get('active',{})
        expected={r:{k:b[k] for k in ('path','sha256','base_model_sha256','batch_id','scale','sidecar_sha256') if k in b}
                  for r,b in active.items() if b}
        try:actual=json.loads((self.home/MIRROR).read_text())
        except FileNotFoundError:actual={}
        except (OSError,ValueError) as exc:raise Unavailable('Adapter mirror unreadable') from exc
        if actual!=expected:raise Unavailable('Adapter mirror differs from committed approval')
    def _snapshot_assets(self,cmd,env):
        if self.approval_store is None or self.purpose!='generate':return
        from .common import file_hash
        from .lora_trainer import REGISTRY_KEY
        active=(self.approval_store.state(REGISTRY_KEY,None)[0] or {}).get('active',{})
        specs=[]
        if '--lora-scaled' in cmd:
            i=cmd.index('--lora-scaled')+1
            specs.append(('adapter',cmd[i],active[self.role]['sha256'],i))
        if self.memory:
            cur=active[self.role+'#sparse_memory'];path=self.memory['env']['V13_MEMORY_FILE']
            specs.append(('memory',path,cur['sha256'],None))
            if cur.get('sidecar_sha256'):
                specs.append(('memory.items',str(path)+'.items.json',cur['sidecar_sha256'],None))
        if not specs:return
        folder=self.home/'tmp'/('runner-assets-'+secrets.token_hex(16));folder.mkdir(parents=True,mode=0o700)
        self._asset_snapshot=folder;self._launch_assets={};self._approved_asset_paths=[p for _,p,_,_ in specs]
        try:
            for kind,path,expected,index in specs:
                dest=Path(str(self._launch_assets['memory'])+'.items.json') if kind=='memory.items' else folder/(kind+Path(path).suffix)
                shutil.copyfile(path,dest)
                if file_hash(dest)!=expected:raise Unavailable('Approved adapter bytes changed during snapshot')
                dest.chmod(0o400);self._launch_assets[kind]=str(dest)
                if index is not None:cmd[index]=str(dest)
                elif kind=='memory':env['V13_MEMORY_FILE']=str(dest)
            # Record hashes independently from original paths; the child opens
            # these private bytes after Store.mutex has been released.
            self._asset_snapshot_hashes={p:file_hash(p) for p in self._launch_assets.values()}
        except BaseException:
            shutil.rmtree(folder,ignore_errors=True);self._asset_snapshot=None;self._launch_assets={};self._asset_snapshot_hashes={};self._approved_asset_paths=[]
            raise
'''

def replace(t,old,new):
    if t.count(old)!=1:raise ValueError('Candidate anchor changed: '+old[:100])
    return t.replace(old,new,1)

def transform(original):
    out=dict(original);t=out['v13/runners.py']
    t=replace(t,"    def __init__(self,home,role,model,config,purpose='generate'):","    def __init__(self,home,role,model,config,purpose='generate',approval_store=None):")
    t=replace(t,'        self.binary=os.environ.get("V13_LLAMA_SERVER",str(home/"bin/llama-server"))',
        '        self.approval_store=approval_store;self._asset_snapshot=None;self._launch_assets={};self._asset_snapshot_hashes={};self._approved_asset_paths=[]\n        self.binary=os.environ.get("V13_LLAMA_SERVER",str(home/"bin/llama-server"))')
    t=replace(t,'        return tuple(stamp(p) for p in paths)',
        '        paths += self._approved_asset_paths+list(self._launch_assets.values())\n        return tuple(stamp(p) for p in paths)')
    t=replace(t,'        if self.log_handle:self.log_handle.close();self.log_handle=None',
        '        if self.log_handle:self.log_handle.close();self.log_handle=None\n        if self._asset_snapshot is not None:shutil.rmtree(self._asset_snapshot,ignore_errors=True)\n        self._asset_snapshot=None;self._launch_assets={};self._asset_snapshot_hashes={};self._approved_asset_paths=[]')
    t=replace(t,'    def load(self,cancel,deadline):\n        check(cancel,deadline)',METHODS+'    def load(self,cancel,deadline):\n        check(cancel,deadline)')
    t=replace(t,'            if self._loaded_stamp==self._lifecycle_stamp():return',
        '            with self._approval_guard(cancel,deadline):\n                self._verify_approval_mirror()\n                if self._loaded_stamp==self._lifecycle_stamp():return')
    start=t.index("        elif self.purpose=='generate':")
    end=t.index('        try:\n            self.proc=subprocess.Popen',start)
    old=t[start:end]
    block=old.split('        self._loaded_binary=cmd[0];launch_stamp=self._lifecycle_stamp()')[0]
    # Preserve the audit candidate insertion anchor outside the critical section.
    t=t[:start]+"        elif self.purpose=='generate':\n            with self._approval_guard(cancel,deadline):\n                self._verify_approval_mirror()\n"+'\n'.join('    '+line for line in block.splitlines()[1:])+"\n                self._snapshot_assets(cmd,env)\n        self._loaded_binary=cmd[0];launch_stamp=self._lifecycle_stamp()\n        check(cancel,deadline)\n"+t[end:]
    start=t.index('            binding=None\n            if self.memory:');end=t.index('        except BaseException:self.unload();raise',start)
    final=t[start:end]
    t=t[:start]+'            with self._approval_guard(cancel,deadline):\n                self._verify_approval_mirror()\n                for path,expected in self._asset_snapshot_hashes.items():\n                    from .common import file_hash\n                    if file_hash(path)!=expected:raise Unavailable("Runner asset snapshot changed")\n'+'\n'.join('    '+line for line in final.splitlines())+'\n'+t[end:]
    t=replace(t,'    def load(self,cancel,deadline):\n        check(cancel,deadline)',
        '    def load(self,cancel,deadline):\n        try:return self._load_validated(cancel,deadline)\n        except BaseException:self.unload();raise\n    def _load_validated(self,cancel,deadline):\n        check(cancel,deadline)')
    # Snapshot failures precede Popen; cleanup the opened log and partial assets.
    t=replace(t,'                self._snapshot_assets(cmd,env)',
        '                try:self._snapshot_assets(cmd,env)\n                except BaseException:self.unload();raise')
    t=replace(t,'    def __init__(self,home,model,config):\n        self.home=Path(home);self.model=model;self.cfg=config',
        '    def __init__(self,home,model,config,approval_store=None):\n        self.home=Path(home);self.model=model;self.cfg=config;self.approval_store=approval_store')
    t=replace(t,'self.template=LlamaRunner(self.home,self.role,self.model,dict(self.cfg,context_tokens=2048,threads=2))',
        'self.template=LlamaRunner(self.home,self.role,self.model,dict(self.cfg,context_tokens=2048,threads=2),approval_store=self.approval_store)')
    t=replace(t,'    def __init__(self,home,models,cfg):self.home=home;self.models=models;self.cfg=cfg;self.current=None;',
        '    def __init__(self,home,models,cfg,approval_store=None):self.home=home;self.models=models;self.cfg=cfg;self.approval_store=approval_store;self.current=None;')
    t=replace(t,'                self.resident[key]=LlamaRunner(self.home,role,path,self.cfg)',
        '                self.resident[key]=LlamaRunner(self.home,role,path,self.cfg)\n                self.resident[key].approval_store=self.approval_store')
    t=replace(t,'CausalStreamRunner(self.home,self.models.path_for(role),self.cfg)',
        'CausalStreamRunner(self.home,self.models.path_for(role),self.cfg,approval_store=self.approval_store)')
    out['v13/runners.py']=t
    out['v13/runtime.py']=replace(out['v13/runtime.py'],'self.pool=RunnerPool(home,self.models,self.cfg);','self.pool=RunnerPool(home,self.models,self.cfg,approval_store=self.store);')
    return out

def sources(root=ROOT):
    folder=root/SNAPSHOT;manifest=json.loads((folder/'manifest.json').read_text());original={}
    if manifest.get('schema')!='APPROVAL_READER_RUNTIME_BASELINE_V1' or set(manifest['files'])!=set(NAMES):raise ValueError('Candidate baseline manifest changed')
    for name,sha in manifest['files'].items():
        data=(folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Candidate baseline digest changed: '+name)
        original[name]=data.decode()
    return original,transform(original)

def load_candidate(name,root=ROOT):
    _,changed=sources(root);module=types.ModuleType('v13._approval_reader_candidate_'+name)
    module.__package__='v13';module.__file__=str(root/('v13/'+name+'.py'))
    exec(compile(changed['v13/'+name+'.py'],module.__file__,'exec'),module.__dict__);return module

def patch_text(root=ROOT):
    original,changed=sources(root)
    return ''.join(''.join(difflib.unified_diff(original[n].splitlines(True),changed[n].splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in NAMES)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.write_text(patch_text());print(a.out)
