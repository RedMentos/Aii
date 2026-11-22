import gzip,hashlib,io,json,os,stat,tarfile,datetime
from pathlib import Path
base=Path('/workspace/scratch/5a9214d3f329');app=base/'v13-work/Aii/v13/code';home=base/'native-audit-cache';proof=app/'docs/proofs/continuation-20261011/night-native-recovery-20261011';report=json.loads((proof/'native-resource-recovery.json').read_text())
assert report['status']=='RESTORED_EXACT_BINDING'
expected=report['current_installed_binding'];bindir=home/'bin/build-mem-b10964/bin';files=[bindir/'llama-server']+[bindir/n for n in sorted(expected['runner_runtime_libraries_sha256'])]
data_cache={};entries={};payloads={}
for p in files:
    resolved=p.resolve()
    assert resolved.parent==bindir.resolve()
    if resolved not in data_cache:data_cache[resolved]=resolved.read_bytes()
    data=data_cache[resolved];wanted=expected['runner_sha256'] if p.name=='llama-server' else expected['runner_runtime_libraries_sha256'][p.name]
    assert hashlib.sha256(data).hexdigest()==wanted,p.name
    rel=p.relative_to(home).as_posix();e={'sha256':wanted,'resolved_size':len(data),'type':'symlink' if p.is_symlink() else 'file','mode':stat.S_IMODE(p.stat().st_mode)}
    if p.is_symlink():
        e['link_target']=os.path.relpath(resolved,p.parent);assert not Path(e['link_target']).is_absolute();payloads[rel]=('symlink',e['link_target'])
    else:payloads[rel]=('file',data)
    entries[rel]=e
for name in ['llama-server','llama-server-mem']:
    rel='bin/'+name;target='build-mem-b10964/bin/llama-server';payloads[rel]=('symlink',target);entries[rel]={'type':'symlink','link_target':target,'sha256':expected['runner_sha256'],'resolved_size':len(data_cache[(bindir/'llama-server').resolve()]),'mode':0o755}
for rel in ['config/memory-server.json','config/runner.json']:
    data=(home/rel).read_bytes();payloads[rel]=('file',data);entries[rel]={'type':'file','sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'mode':0o644}
manifest={'schema':'v13_closed_native_runner_cache_v1','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':'linux-x86_64','tag':'b10964','cache_only':True,'inference_proof':False,'phone_proof':False,'gate_pass':False,'installed_binding':expected,'files':entries,'unique_elf_bytes':sum(map(len,data_cache.values())),'unique_elf_files':len(data_cache),'library_entries':len(expected['runner_runtime_libraries_sha256']),'recovery_report_sha256':hashlib.sha256((proof/'native-resource-recovery.json').read_bytes()).hexdigest()}
payloads['RECOVERY/manifest.json']=('file',(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode())
payloads['RECOVERY/README.txt']=('file',b'Closed Linux x86_64 b10964 runner cache. No models, source tree or build objects. All ELF files exactly match the preregistered native binding. Restore only after validating archive safety and every listed hash, including resolved symlink targets. Model files must be independently restored and SHA-verified. This is a reproducibility cache, not physical Redmi or learned quality evidence. config/memory-server.json records the original recovered source path and must not be mistaken for an existing source tree.\n')
out=base/'deliverables/native-runner-b10964-linux-x86_64.closed.tar.gz';assert not out.exists()
with out.open('xb') as raw:
    with gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w') as tar:
            for name,(kind,value) in sorted(payloads.items()):
                info=tarfile.TarInfo(name);info.mtime=0;info.uid=info.gid=0;info.uname=info.gname='';info.mode=entries.get(name,{}).get('mode',0o644)
                if kind=='symlink':info.type=tarfile.SYMTYPE;info.linkname=value;info.mode=0o777;tar.addfile(info)
                else:info.size=len(value);tar.addfile(info,io.BytesIO(value))
    raw.flush();os.fsync(raw.fileno())
bundle={'schema':'v13_closed_native_runner_bundle_inventory_v1','path':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'bytes':out.stat().st_size,'unique_elf_bytes':manifest['unique_elf_bytes'],'unique_elf_files':manifest['unique_elf_files'],'library_entries':manifest['library_entries'],'archive_entries':len(payloads),'source_bytes':0,'model_bytes':0,'phone_proof':False,'cache_only':True}
(proof/'runner-bundle-inventory.json').write_text(json.dumps(bundle,indent=2)+'\n');print(json.dumps(bundle,indent=2))
