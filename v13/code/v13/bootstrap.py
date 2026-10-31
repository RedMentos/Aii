"""Pinned artifact installation; Android builds the native runner locally."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from .common import APP,atomic_write,dumps,file_hash,Unavailable
from .config import initialize,home_path
from .models import ModelManager,catalog,platform_tag,download_file
from .safe_tar import extract
from .runner_activation import activate_runner_candidate

def run_build(cmd,home):
    print('Native build: '+' '.join(map(str,cmd)),flush=True)
    with open(home/'logs/build.log','ab') as log:
        p=subprocess.Popen(list(map(str,cmd)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        for line in iter(p.stdout.readline,b''):log.write(line);log.flush();print(line.decode(errors='replace').rstrip(),flush=True)
        if p.wait():raise RuntimeError('Build fehlgeschlagen; siehe logs/build.log')

def install_llama_runner(home, progress=print):
    """Stage and validate a new runner without changing the previous target."""
    specs=catalog();tag=platform_tag();r=specs['runner']
    binary=home/'bin/llama-server';manifest=home/'config/runner.json'
    prior=json.loads(manifest.read_text()) if manifest.exists() else {}
    if binary.is_file() and prior.get('tag')==r['tag'] and prior.get('binary_sha256')==file_hash(binary):
        return
    binary.parent.mkdir(parents=True,exist_ok=True)
    # Unique directory: a retry never overwrites the currently active target.
    staging=Path(tempfile.mkdtemp(prefix='.llama-'+r['tag']+'-',dir=binary.parent))
    try:
        if tag in r['linux_binaries']:
            archive=home/'tmp/llama-bin.tar.gz'
            download_file(r['linux_binaries'][tag],archive,progress)
            dest=staging/'release';extract(archive,dest)
            found=list(dest.rglob('llama-server'))
            if len(found)!=1:raise Unavailable('llama-server im Release nicht eindeutig')
            target=found[0]
            if target.is_symlink() or not target.is_file():
                raise Unavailable('llama-server im Release ist keine reguläre Datei')
            target.chmod(0o700)
        else:
            archive=home/'tmp/llama-source.tar.gz'
            download_file({'url':r['source_url'],'sha256':r['source_sha256'],'size':r['source_size']},archive,progress)
            dest=staging/'source';extract(archive,dest)
            source=dest/('llama.cpp-'+r['tag']);build=staging/'build'
            run_build(['cmake','-S',source,'-B',build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DGGML_NATIVE=OFF','-DGGML_OPENMP=OFF','-DGGML_LLAMAFILE=OFF','-DLLAMA_OPENSSL=OFF','-DLLAMA_BUILD_TESTS=OFF','-DLLAMA_BUILD_EXAMPLES=OFF','-DLLAMA_BUILD_SERVER=ON','-DLLAMA_BUILD_UI=OFF','-DLLAMA_USE_PREBUILT_UI=OFF'],home)
            run_build(['cmake','--build',build,'--target','llama-server','--parallel','2'],home)
            target=build/'bin/llama-server'
        activate_runner_candidate(target,binary,manifest,tag=r['tag'],platform=tag)
    except BaseException:
        shutil.rmtree(staging,ignore_errors=True)
        raise
    # The successful candidate directory remains as the live symlink target.
    # Older targets are not deleted without a separate owner/rollback policy.


def install_native(home,progress=print):
    install_llama_runner(home,progress)
    specs=catalog();tag=platform_tag()
    needle_dir=home/'models/needle';(needle_dir/'needle').chmod(0o700)
    worker=home/'bin/needle-worker';source=APP/'scripts/needle_worker.cpp';wm=home/'config/needle-worker.json';marker=json.loads(wm.read_text()) if wm.exists() else {}
    if worker.is_file() and marker.get('source_sha256')==file_hash(source) and marker.get('binary_sha256')==file_hash(worker):return
    compiler=shutil.which('clang++') or shutil.which('g++')
    if not compiler:raise Unavailable('C++ compiler fehlt')
    args=[compiler,'-std=c++17','-O2','-I',str(needle_dir),str(source)]
    if tag.startswith('linux'):
        wheel=specs['models']['needle']['wheels'][tag];path=home/'tmp'/wheel['local_name'];download_file(wheel,path,progress)
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if n.endswith('libneedle3.so')]
            if len(names)!=1:raise Unavailable('Needle shared library fehlt')
            atomic_write(home/'bin/libneedle.so',z.read(names[0]))
        args += ['-L'+str(home/'bin'),'-lneedle','-Wl,-rpath,$ORIGIN']
    else:args += [str(needle_dir/'libneedle.a')]
    tmp=worker.with_suffix('.new');args += ['-pthread','-lm','-ldl','-o',str(tmp)]
    try:
        run_build(args,home);tmp.chmod(0o700);os.replace(tmp,worker)
        atomic_write(wm,dumps({'source_sha256':file_hash(source),'binary_sha256':file_hash(worker),'platform':tag,'native_revision':specs['models']['needle']['revision']}))
    except Exception as e:
        tmp.unlink(missing_ok=True);progress('C2-Embedding-Worker nicht gebaut: '+str(e)+'. Native CLI bleibt verfügbar; Training bleibt gesperrt.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--home');a=p.parse_args();home=home_path(a.home)
    (home/'data').mkdir(parents=True,exist_ok=True)
    with (home/'data/coordinator.lock').open('a+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise Unavailable('V13 läuft oder baut bereits; Chat/Installer zuerst schließen') from exc
        initialize(home);ModelManager(home).install();install_native(home)
if __name__=='__main__':main()
