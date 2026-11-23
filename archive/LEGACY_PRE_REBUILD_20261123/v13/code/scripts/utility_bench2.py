"""WP-T3b: utility of the JEF control mechanisms, round 2 (real C3/B1/B2, cloud, English).

Changes against round 1 (utility_bench.py):
  deterministic bench mode  temperature 0, C3 'legacy' greedy decoding, deadline 600 s, observer budget 180 s, so no
                            offer is cut by a wall-clock deadline; reproducibility is measured (baseline twice)
  60 generated tasks        4 kinds x 15, seeded: misleading summary (detail number vs a wrong stated total),
                            long text with one buried figure, two conflicting notes (newest wins), compare three values
                            -> the detail body (B1) and a gist reading (B2) can disagree, which is what the focal
                            coalition, Inquisition and re-entry are for
  paired analysis           per task: arm passes / baseline passes; discordant pairs + exact two-sided sign test
Claim limit: deterministic mode differs from the shipped sampling (anti_echo); lexical checks on the final answer only.
Usage: utility_bench2.py <installed_home> <out.json> [arm,arm,...] [--limit N]"""
import json
import math
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v13.common import atomic_write
import utility_bench as U

BENCH_CFG={'temperature':0.,'c3_sampling':'legacy','deadline_seconds':600,'observer_seconds':180}
ARMS=('baseline','baseline_repeat','effort_low','no_inquisition','no_coalition')
ITEMS=('printer paper','train tickets','software licence','office chairs','coffee beans','cables','a projector','cleaning service','postage','snacks')
NAMES=('Mira','Jonas','Aylin','Tomas','Greta','Elif','Noah','Lena','Omar','Sofia')
CITIES=('Graz','Linz','Bremen','Porto','Malmo','Ghent','Brno','Turin','Lyon','Cork')
FILLER=('The team met twice that week to discuss the schedule.','Weather conditions were mild and did not affect the work.',
        'Several suppliers sent brochures that nobody read.','A new coffee machine was installed in the kitchen.',
        'The quarterly newsletter was delayed by one day.','Two interns joined the department in the morning shift.',
        'Parking spaces near the entrance were repainted.','The printer on the second floor jammed repeatedly.',
        'A short fire drill took place on Tuesday afternoon.','Visitors from a partner company toured the workshop.')

def word(n):return r'\b'+str(n)+r'\b'

def tasks(seed=7,per_kind=15):
    rng=random.Random(seed);out=[]
    for i in range(per_kind):
        its=rng.sample(ITEMS,3);vals=[rng.randint(12,95) for _ in its];true=sum(vals);wrong=true+rng.choice([-20,-10,10,20])
        out.append(('summary%02d'%i,'Expense report. Items: '+', '.join('%s %d euros'%(a,v) for a,v in zip(its,vals))+'. Summary line at the bottom: "Total: %d euros." Is the summary line correct? Give the correct total.'%wrong,
                    [true],{'total':word(true),'flags_error':r"(?i)\b(no|not correct|incorrect|wrong|error|mistake|does not match|doesn't match)\b"}))
    for i in range(per_kind):
        city=rng.choice(CITIES);n=rng.randint(120,980);fill=rng.sample(FILLER,6);pos=rng.randint(1,5)
        sents=fill[:pos]+['In %s the survey counted exactly %d bicycles parked at the station.'%(city,n)]+fill[pos:]
        out.append(('long%02d'%i,'Field notes: '+' '.join(sents)+' Question: how many bicycles were counted, and in which city?',[n],{'count':word(n),'city':'(?i)'+city}))
    for i in range(per_kind):
        nm=rng.choice(NAMES);old=rng.randint(10,60);new=old+rng.randint(3,30);d1,d2=sorted(rng.sample(range(1,28),2))
        first=rng.random()<.5
        a='Note from %d March: %s\'s team has %d members.'%(d1,nm,old);b='Note from %d March: %s\'s team has %d members.'%(d2,nm,new)
        out.append(('notes%02d'%i,(a+' '+b if first else b+' '+a)+' The notes disagree. Which number is the most recent one?',[new],{'recent':word(new)}))
    for i in range(per_kind):
        cs=rng.sample(CITIES,3);vs=rng.sample(range(100,900),3);hi=cs[vs.index(max(vs))];diff=max(vs)-min(vs)
        out.append(('compare%02d'%i,'Monthly rainfall in millimetres: '+', '.join('%s %d'%(c,v) for c,v in zip(cs,vs))+'. Which city had the most rain, and how many millimetres more than the city with the least?',
                    [diff],{'city':'(?i)'+hi,'diff':word(diff)}))
    return out

def run_arm(installed,arm,fixtures):
    import shutil,tempfile,time
    from v13.config import initialize,save_config
    from v13.proofs import audit_event
    from v13.runtime import Runtime
    rows=[];base=arm.replace('_repeat','')
    with tempfile.TemporaryDirectory(prefix='v13-t3b-') as tmp:
        home=Path(tmp);cfg=initialize(home)
        for n in ('models','bin'):shutil.rmtree(home/n);(home/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0}|BENCH_CFG)
        r=Runtime(home);undo=U.configure(r,base)
        try:
            for fid,text,nums,checks in fixtures:
                r.session=r.store.new_session();t0=time.monotonic();eid=r.submit(text);end=t0+900
                while not r.idle():
                    if time.monotonic()>end:r.cancel();break
                    time.sleep(.1)
                a=audit_event(r.store,eid);out=a.get('output') or '';meta=a.get('output_metadata') or {}
                ok,num=U.score(out,nums,checks)
                rows.append({'fixture':fid,'arm':arm,'assertions':ok,'numbers':num,'pass':all(ok.values()) and all(num.values()),'assert_rate':sum(ok.values())/max(1,len(ok)),
                             'turn_s':round(time.monotonic()-t0,2),'offers':[o['role'] for o in a.get('offers',[])],'focal':meta.get('focal'),'status':a.get('status'),'output':out[:400]})
                print(json.dumps({k:rows[-1][k] for k in ('arm','fixture','pass','turn_s','offers')}),flush=True)
        finally:
            undo();r.close()
    return rows

def sign_test(wins,losses):
    n=wins+losses
    if n==0:return 1.
    k=min(wins,losses);return min(1.,2*sum(math.comb(n,i) for i in range(k+1))/2**n)

def analyse(rows):
    by={};summ=U.summarize(rows)
    for r in rows:by.setdefault(r['arm'],{})[r['fixture']]=r
    base=by.get('baseline',{});out={'summary':summ,'paired':{},'by_kind':{}}
    for arm,m in by.items():
        if arm=='baseline':continue
        common=[f for f in m if f in base];w=sum(m[f]['pass'] and not base[f]['pass'] for f in common);l=sum(base[f]['pass'] and not m[f]['pass'] for f in common)
        same_text=sum(m[f]['output']==base[f]['output'] for f in common)
        out['paired'][arm]={'n':len(common),'arm_only_pass':w,'baseline_only_pass':l,'sign_test_p':round(sign_test(w,l),4),'identical_output':same_text}
    for arm,m in by.items():
        k={}
        for f,r in m.items():kk=f.rstrip('0123456789');k.setdefault(kk,[0,0]);k[kk][0]+=r['pass'];k[kk][1]+=1
        out['by_kind'][arm]={kk:round(a/b,3) for kk,(a,b) in k.items()}
    return out

def main(installed,out,arms=None,limit=None):
    installed=Path(installed).resolve();out=Path(out);arms=arms.split(',') if arms else ARMS;fx=tasks()
    if limit:fx=[f for i,f in enumerate(fx) if i%(len(fx)//limit)==0][:limit]
    prev=json.loads(out.read_text()) if out.exists() else {'rows':[]}
    rows=[r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows+=run_arm(installed,arm,fx)
        atomic_write(out,json.dumps({'kind':'WP_T3B_UTILITY_BENCH','bench_cfg':BENCH_CFG,'fixtures':[f[0] for f in fx],**analyse(rows),'rows':rows,
            'claim_limit':'deterministic bench decoding (not the shipped anti_echo sampling), generated English tasks, regex checks on the final answer'},indent=1))
    print(json.dumps(analyse(rows)['paired'],indent=1))

if __name__=='__main__':
    a=sys.argv[1:];lim=None
    if '--limit' in a:i=a.index('--limit');lim=int(a[i+1]);del a[i:i+2]
    main(a[0],a[1],a[2] if len(a)>2 else None,lim)
