"""Phone check for the WP-Z2l chain candidate: one body, two states, with the rule chain - time and memory on the Redmi.

Runs the WP-Z2l shared-body arm (DS: b2_context_chars=1536, pointer over whole earlier sources, 4 slots; eligibility
tool with recency guard and newest_quoted reader) on three of the Z2l episodes (Baten REVISED, Enif TWICE, Kitalpha
CONFIRM), seed 1, all seven STEP2 variants (21 rows), and samples the resident memory of this process and its children.
Nothing is switched on in the user's runtime; the run uses its own home under --work.
Usage (Termux): python scripts/handy_z2_chain.py --installed-home <installed models home> --work <empty folder>
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
KEEP=('Baten','Enif','Kitalpha')
SEED=1

def _private(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def load():
    l=_private('step2_z2l_for_phone','scripts/step2_z2l_chain.py')
    fixtures=[f for f in l.FIXTURES if f['id'] in KEEP];fix={f['id']:f for f in fixtures}
    for m in (l,l.i,l.h,l.g):m.FIX=fix;m.FIXTURES=fixtures
    l.z.FIXTURES=fixtures;l.z.z2.FIXTURES=fixtures;l.z.FIX=fix;l.z.HARD=list(fix)
    l.z.SEEDS=(SEED,);l.z.z2b.SEEDS=(SEED,)
    return l

def rss_kb(pid):
    """Resident memory of pid and all its descendants (Linux /proc), in kB."""
    total=0;kids={}
    for d in os.listdir('/proc'):
        if not d.isdigit():continue
        try:
            stat=open(f'/proc/{d}/stat').read().rsplit(')',1)[1].split()
            kids.setdefault(int(stat[1]),[]).append(int(d))
        except OSError:continue
    todo=[pid]
    while todo:
        p=todo.pop();todo+=kids.get(p,[])
        try:
            for line in open(f'/proc/{p}/status'):
                if line.startswith('VmRSS:'):total+=int(line.split()[1])
        except OSError:pass
    return total

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--installed-home',required=True);p.add_argument('--work',required=True)
    a=p.parse_args();work=Path(a.work);work.mkdir(parents=True,exist_ok=True)
    l=load();peak=[0];stop=threading.Event()
    def sample():
        while not stop.is_set():peak[0]=max(peak[0],rss_kb(os.getpid()));stop.wait(.5)
    t=threading.Thread(target=sample,daemon=True);t.start();started=time.monotonic()
    try:summary=l.run(a.installed_home,work,'DS',SEED)
    finally:stop.set();t.join()
    report=json.loads((work/('step2_'+l.z.z2b.run_id('DS',SEED)+'.json')).read_text())
    rows=summary['z2l']['rows']
    out={'schema':'HANDY_Z2_CHAIN_V1','rows':len(rows),'wall_s':round(time.monotonic()-started,1),'peak_rss_mb':round(peak[0]/1024,1),
         'row_elapsed_s':sorted(round(r.get('elapsed_s',0),1) for r in report['rows']),
         'b2_prompt_tokens':[t for t in summary['z2e']['b2_prompt_tokens'] if t],
         'chain_exact_both_exact':sum(r['action']==r['oracle'] for r in rows if r['variant']=='both_exact'),
         'chain_wrong':sum(r['action'] in ('A','B','NONE') and r['action']!=r['oracle'] for r in rows),
         'kickoff_in_context':summary['z2g']['validity'],'structural':summary['tool_status']!='STRUCTURAL_FAIL'}
    (work/'handy_z2_chain_result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=1))
if __name__=='__main__':main()
