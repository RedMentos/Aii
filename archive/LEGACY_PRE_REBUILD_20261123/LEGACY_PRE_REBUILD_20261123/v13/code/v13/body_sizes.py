"""Measured body sizes for the AG13 residency budget (WP-N21, finding of thread P's RAM bench).

The residency decides whether C3, B1 and B2 may stay loaded together under ``body_residency_mb``. The old
estimate (file x 1.1 + 96 MiB) was a guess. What binds under memory pressure is the part the kernel cannot
drop: anonymous memory (llama.cpp's repacked weight copy, KV, compute buffers). The mmap'ed GGUF pages are
file-backed and reclaimable once the weights are repacked. Thread P's cgroup squeeze (Linux, b10964,
runner default flags) shows it: C3+B1+B2 resident run at a hard limit of 2000 MiB without slowdown while
their Anon sum is 1869 MiB, 1750 MiB is an OOM kill; PSS (3268 MiB) would have said "does not fit".

Size of one runner = Anon after work + ``HOT_FILE_MB`` (file pages still touched per token; BOOT from the
squeeze: (2000 - 1869) / 3 ~ 44 MiB with three runners, (1250 - 1129) / 2 ~ 60 MiB sequential -> 64).

Profiles are keyed by the model file's sha256 (from ``specs/models.json``), so a swapped or re-quantized
file never inherits another file's size; such a file falls back to the old formula (``source=ESTIMATE``).

  specs/body-sizes.json   shipped profile, built from the cloud bench (evidence CLOUD_X86_LOWER_BOUND:
                          Android adds ART/Termux overhead and a different aarch64 repack layout)
  store BODY_SIZE_PROFILE imported from a ram_budget_bench run (``:resources bodies import <json>``);
                          DEVICE_MEASURED when that run was on Android, else HOST_MEASURED_NOT_REDMI.
                          Overrides the shipped profile per file.
"""
import json
from pathlib import Path

STATE_KEY='BODY_SIZE_PROFILE';SCHEMA='v13.body_sizes/1'
SPEC=Path(__file__).resolve().parents[1]/'specs/body-sizes.json'
MODELS_SPEC=Path(__file__).resolve().parents[1]/'specs/models.json'
HOT_FILE_MB=64.                   # BOOT, derived from the cgroup squeeze (module doc)
KV_OVERHEAD_MB=96;WEIGHT_FACTOR=1.1  # old estimate, only for unmeasured files

def estimate(path):return round(Path(path).stat().st_size/2**20*WEIGHT_FACTOR+KV_OVERHEAD_MB,1)

def file_index(models_spec=MODELS_SPEC):
    """local file name -> {sha256, size} from the pinned model spec."""
    out={}
    for m in json.loads(Path(models_spec).read_text())['models'].values():
        for f in m.get('files') or []:out[f['local_name']]={'sha256':f['sha256'],'size':f['size']}
    return out

def from_bench(report,evidence=None,models_spec=MODELS_SPEC):
    """Profile entries from a ``scripts/ram_budget_bench.py`` report: only ``single:<ROLE>`` scenarios with the
    runner default flags (no extra args), purpose generate. Files not in the model spec are skipped (no sha)."""
    idx=file_index(models_spec);env=report.get('environment') or {}
    ev=evidence or ('DEVICE_MEASURED' if env.get('android') else ('CLOUD_X86_LOWER_BOUND' if env.get('machine','x86_64').startswith('x86') else 'HOST_MEASURED_NOT_REDMI'))
    out={}
    for row in report.get('results') or []:
        if not str(row.get('scenario','')).startswith('single:') or row.get('error'):continue
        for p in row.get('processes') or []:
            if p.get('extra') or p.get('purpose')!='generate':continue
            f=idx.get(p.get('model'));aw=p.get('after_work') or {}
            anon=aw.get('Pss_Anon',aw.get('Anonymous'))
            if not f or anon is None:continue
            out[f['sha256']]={'file':p['model'],'size_bytes':f['size'],'role':p.get('role'),'anon_mib':round(float(anon),1),'pss_mib':aw.get('Pss'),
                              'hot_file_mib':HOT_FILE_MB,'size_mib':round(float(anon)+HOT_FILE_MB,1),'evidence':ev}
    return out

def shipped():
    try:return json.loads(SPEC.read_text()).get('entries') or {}
    except FileNotFoundError:return {}

def imported(store):
    if store is None:return {}
    st,_=store.state(STATE_KEY,None);return (st or {}).get('entries') or {}

def lookup(sha,store=None):
    if not sha:return None
    return imported(store).get(sha) or shipped().get(sha)

def installed_sha(models,role,path):
    """sha256 of the file that serves ``role`` when it is the installed main file (a swap/RAMP file has none)."""
    try:
        from .models import model_key
        e=models.installed.get(model_key(role,models.b2_control)) or {}
        f=e['files'][e['main_file']]
        if (models.home/f['path']).resolve()==Path(path).resolve():return f.get('sha256')
    except Exception:return None
    return None

def size(models,role,store=None):
    """(size_mib, source) for the runner that serves ``role``; None when the model is missing."""
    try:p=models.path_for(role)
    except Exception:return None,None
    e=lookup(installed_sha(models,role,p),store)
    if e:return e['size_mib'],e['evidence']
    return estimate(p),'ESTIMATE'

def import_report(store,report,evidence=None):
    entries=from_bench(report,evidence)
    if not entries:raise ValueError('keine passenden single:<Rolle>-Messungen mit Standard-Flags im Bericht')
    def fn(st):
        st=st or {'schema':SCHEMA,'entries':{}};st['entries'].update(entries);return st
    cur,v=store.state(STATE_KEY,None);store.set_state(STATE_KEY,fn(cur),expected=v)
    return entries

def reset(store):
    cur,v=store.state(STATE_KEY,None);store.set_state(STATE_KEY,{'schema':SCHEMA,'entries':{}},expected=v)

def fits(sizes,budget_mb):
    """Which combinations fit the residency budget (C3 is pinned)."""
    c3,b1,b2=(sizes.get(r) for r in ('C3_LANGUAGE','B1_DETAIL','B2_GIST'))
    if None in (c3,b1,b2):return None
    return {'C3+B1':c3+b1<=budget_mb,'C3+B2':c3+b2<=budget_mb,'C3+B1+B2':c3+b1+b2<=budget_mb,
            'need_all_mb':round(c3+b1+b2,1),'budget_mb':budget_mb}
