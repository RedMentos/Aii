"""WP-S3 live path: a second llama-server binary that serves the approved keyed sparse memory (V13_MEMORY_FILE).

The pinned runner source (specs/models.json runner.source_url, same tag) is patched in a separate tree:
  tools/server/server.cpp gets `#define V13_MEMORY_SERVER` + scripts/v13_memory_hook.h, and its common_params_parse call
  becomes v13_parse_and_attach, which installs the cb_eval memory hook only when V13_MEMORY_FILE is set;
  server-context.cpp hands every new slot prompt to v13_new_prompt (entity-guard context incl. the cached prefix).
Without the variable the binary behaves like the normal runner. The normal bin/llama-server is never touched.
Build (minutes on the phone): python -m v13.memory_server --home ~/v13 build [--source DIR]
runner_memory(home, role, model) tells LlamaRunner which binary + env to use; anything that does not match the approved
binding byte for byte returns None and the normal runner serves the turn.
"""
import argparse,json,os,shutil
from pathlib import Path
from .common import APP,atomic_write,dumps,file_hash,Unavailable

ROLE_SUFFIX='#sparse_memory'
MANIFEST='config/memory-server.json'
HEADER=APP/'scripts/v13_memory_hook.h'

def patch_source(src):
    """Idempotent patch of a llama.cpp tree (server.cpp + server-context.cpp). Returns the patched server.cpp sha256."""
    src=Path(src);srv=src/'tools/server/server.cpp'
    if not srv.is_file():raise Unavailable('tools/server/server.cpp fehlt in '+str(src))
    shutil.copyfile(HEADER,src/'tools/server/v13_memory_hook.h');t=srv.read_text()
    call='common_params_parse(argc, argv, params, LLAMA_EXAMPLE_SERVER)'
    if 'v13_parse_and_attach' not in t:
        if t.count(call)!=1:raise Unavailable('Server-Quelle passt nicht zum Patch (Aufruf nicht eindeutig)')
        t='#define V13_MEMORY_SERVER\n#include "v13_memory_hook.h"\n'+t.replace(call,'v13_parse_and_attach(argc, argv, params, LLAMA_EXAMPLE_SERVER)')
        srv.write_text(t)
    ctxf=src/'tools/server/server-context.cpp';c=ctxf.read_text();anchor='slot.state = SLOT_STATE_PROCESSING_PROMPT;\n'
    if 'v13_new_prompt' not in c:  # guard context = the whole prompt, also the part the prompt cache reuses
        if c.count(anchor)!=1:raise Unavailable('server-context.cpp passt nicht zum Patch (Prompt-Start nicht eindeutig)')
        c='#define V13_MEMORY_SERVER\n#include "v13_memory_hook.h"\n'+c.replace(anchor,anchor+'                        v13_new_prompt(input_tokens);\n')
        ctxf.write_text(c)
    return file_hash(srv)

def build(home,source=None,progress=print,jobs=2):
    from .bootstrap import extract,run_build
    from .models import catalog,download_file
    home=Path(home);r=catalog()['runner']
    if source is None:
        archive=home/'tmp/llama-source.tar.gz'
        download_file({'url':r['source_url'],'sha256':r['source_sha256'],'size':r['source_size']},archive,progress)
        dest=home/'tmp'/('mem-'+r['tag']);extract(archive,dest);source=dest/('llama.cpp-'+r['tag'])
    source=Path(source);patched=patch_source(source);b=home/'bin'/('build-mem-'+r['tag'])
    run_build(['cmake','-S',source,'-B',b,'-DCMAKE_BUILD_TYPE=Release','-DGGML_NATIVE=OFF','-DGGML_OPENMP=OFF','-DGGML_LLAMAFILE=OFF','-DLLAMA_OPENSSL=OFF',
               '-DLLAMA_CURL=OFF','-DLLAMA_BUILD_TESTS=OFF','-DLLAMA_BUILD_EXAMPLES=OFF','-DLLAMA_BUILD_SERVER=ON','-DLLAMA_BUILD_UI=OFF','-DLLAMA_USE_PREBUILT_UI=OFF'],home)
    run_build(['cmake','--build',b,'--target','llama-server','--parallel',str(jobs)],home)
    target=b/'bin/llama-server';link=home/'bin/llama-server-mem';tmp=home/'bin/llama-server-mem.new'
    tmp.unlink(missing_ok=True);tmp.symlink_to(target);os.replace(tmp,link)
    m={'tag':r['tag'],'source':str(source),'server_cpp_sha256':patched,'header_sha256':file_hash(HEADER),'server_context_sha256':file_hash(source/'tools/server/server-context.cpp'),'binary_sha256':file_hash(link)}
    atomic_write(home/MANIFEST,dumps(m));return m

def runner_memory(home,role,model_path):
    """{'binary','env'} for an approved, hash-bound memory of this role on exactly this model file, else None."""
    home=Path(home)
    try:
        cur=json.loads((home/'config/lora-active.json').read_text()).get(role+ROLE_SUFFIX)
        man=json.loads((home/MANIFEST).read_text())
    except (OSError,ValueError):return None
    if not cur or not cur.get('path','').endswith('.bin'):return None
    binary=home/'bin/llama-server-mem'
    try:
        if not binary.is_file() or file_hash(binary)!=man.get('binary_sha256'):return None
        if file_hash(model_path)!=cur['base_model_sha256'] or file_hash(cur['path'])!=cur['sha256']:return None
    except OSError:return None
    return {'binary':str(binary),'env':{'V13_MEMORY_FILE':cur['path']}}

def captured_delivery_binding(home,role,model_path):
    """Snapshot an approved row map for a runner load; this is not a firing or recall measurement."""
    from .sparse_memory import native_items_path,DELIVERY_SCHEMA
    try:
        mem=runner_memory(home,role,model_path)
        if not mem:return None
        cur=json.loads((Path(home)/'config/lora-active.json').read_text())[role+ROLE_SUFFIX]
        side=native_items_path(cur['path']);sha=file_hash(side)
        if sha!=cur.get('sidecar_sha256'):return None
        metadata=json.loads(side.read_text())
        if metadata.get('schema')!=DELIVERY_SCHEMA or metadata.get('native_sha256')!=cur['sha256']:return None
        if not isinstance(metadata.get('rows'),list) or not isinstance(metadata.get('item_bindings'),dict):return None
        return {'path':cur['path'],'native_sha256':cur['sha256'],'model_sha256':cur['base_model_sha256'],
                'binary_sha256':file_hash(mem['binary']),'sidecar_sha256':sha,'batch_id':cur['batch_id']}
    except (OSError,ValueError,KeyError,TypeError):return None

def _native_live_rows(path):
    """Structural row inventory only: nonzero values/keys and reachable thresholds do not prove firing."""
    import struct,math
    b=Path(path).read_bytes()
    if len(b)<40 or b[:8]!=b'V13SMEM1':raise ValueError('Native header')
    layer,hid,n,ew,topk,guard=struct.unpack_from('<6i',b,8);tau,scale=struct.unpack_from('<2f',b,32)
    if not (0<=layer<4096 and 0<hid<=16384 and 0<=n<=65536 and 0<ew<=1024 and 0<topk<=65536 and guard in (0,1)):
        raise ValueError('Native dimensions')
    if not math.isfinite(tau) or tau<=0 or not math.isfinite(scale) or scale==0:raise ValueError('Native gates')
    if len(b)!=40+4*hid+8*n*hid+4*n+4*n*ew:raise ValueError('Native size')
    keys=40+4*hid;theta=keys+4*n*hid;values=theta+4*n;ent=values+4*n*hid
    live=set()
    for r in range(n):
        k=struct.unpack_from('<%df'%hid,b,keys+4*r*hid);v=struct.unpack_from('<%df'%hid,b,values+4*r*hid)
        th=struct.unpack_from('<f',b,theta+4*r)[0];e=struct.unpack_from('<%di'%ew,b,ent+4*r*ew)
        if (math.isfinite(th) and th<=1. and any(x!=0 for x in k) and any(x!=0 for x in v)
                and all(math.isfinite(x) for x in (*k,*v)) and (not guard or any(x>=0 for x in e))):live.add(r)
    return n,live

def shadow_delivery(store,home,role,model_path,loaded_binding,memories):
    """Inventory possible duplicate fact delivery; Exact stays present and native firing remains unmeasured.

    Caller supplies the snapshot of the actual healthy native-memory process, never a prospective runner.
    """
    from .sparse_memory import native_items_path
    result={'mode':'SHADOW','exact_retained':True,'firing':'UNMEASURED','candidates':[],'provenance':[],'reasons':[],
            'binding':loaded_binding}
    current=captured_delivery_binding(home,role,model_path)
    if not current or current!=loaded_binding:
        result['reason']='NO_MATCHING_LOADED_BINDING';return result
    try:
        metadata=json.loads(native_items_path(current['path']).read_text());n,live=_native_live_rows(current['path'])
        if len(metadata['rows'])!=n:raise ValueError('Native row map size')
        forgotten={str(m) for m in metadata.get('forgotten',[])}
    except (OSError,ValueError,KeyError,TypeError):
        result['reason']='INVALID_NATIVE_ROW_MAP';return result
    for memory in memories:
        mid=memory.get('id');reason='NOT_ORDINARY_FACT'
        if isinstance(mid,str) and memory.get('kind')=='fact' and not memory.get('consolidation'):
            reason='NO_BOUND_LIVE_ROWS'
            binding=metadata['item_bindings'].get(mid)
            rows=[r for r,m in enumerate(metadata['rows']) if m==mid]
            if mid not in forgotten and binding and rows and all(r in live for r in rows):
                reason='SOURCE_OR_CONTENT_MISMATCH'
                try:
                    m=store.one('SELECT m.*,s.hash,s.chars,s.deleted FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?',(mid,))
                    ref=binding['source_ref']
                    expected={'source_id':m['source_id'],'sha256':m['hash'],'char_start':0,'char_end':m['chars'],'modality':'text'} if m else None
                    if (m and m['active'] and not m['deleted'] and m['kind']=='fact'
                            and binding['prompt']==m['key_text']==memory['key_text']
                            and binding['target']==m['value']==memory['value']
                            and ref==expected==memory['source_ref'] and store.read_source(ref)==m['value']):
                        result['candidates'].append(mid);result['provenance'].append(dict(ref));reason='BOUND_FACT_POSSIBLE_FIRING_UNMEASURED'
                except (OSError,KeyError,TypeError,ValueError):pass
        result['reasons'].append({'memory_id':mid,'reason':reason})
    result['reason']='INVENTORY_ONLY';return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--home',required=True);ap.add_argument('cmd',choices=['build','status','patch']);ap.add_argument('--source')
    ap.add_argument('--jobs',type=int,default=2);a=ap.parse_args()
    if a.cmd=='patch':print(patch_source(a.source));return
    if a.cmd=='build':print(json.dumps(build(Path(a.home).expanduser(),a.source,jobs=a.jobs),indent=1));return
    p=Path(a.home).expanduser()/MANIFEST;print(p.read_text() if p.is_file() else '{"built":false}')

if __name__=='__main__':main()
