"""WP-T3: utility of the JEF control mechanisms with real C3/B1/B2 weights (cloud, English).

Arms on the same fixtures, same seed, same order, one fresh brain per arm (warm processes, new session per fixture):
  baseline            shipped defaults (adaptive effort, focal coalition + Inquisition, gist/attention SHADOW)
  effort_low/high     R5: fixed effort instead of adaptive (G5B)
  no_inquisition      focal loop without Inquisition P1/P2 (G5)
  no_coalition        every candidate admitted, no coalition competition (G3D)
  gist_active         B2 gets gist slots instead of the 960-char segments (G1B)
  attention_active    learned attention/gain acts (A4/F1)
  coupling_0/1        C4.uncertainty_coupling_gain 0 / 1 instead of BOOT .5
Score: regex task assertions + expected-number coverage on the final answer (no model judge), turn latency, offers used.
Claim limit: 12 short fixtures, one seed, lexical checks; diagnostic for direction, not a quality benchmark.
Usage: utility_bench.py <installed_home> <out.json> [arm,arm,...]"""
import json
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write
from v13.config import initialize,save_config
from v13.proofs import audit_event
from v13.runtime import Runtime
from v13 import focal as F
from v13 import effort as EF

FIX=[
 ('aurora','Compare the options for Project Aurora. Budget: 120 euros. Option Red costs 80 euros and takes 2 days. Option Blue costs 110 euros and takes 1 day. Constraint: local only, no cloud. State the remaining budget for each option and briefly summarise the trade-off.',
  [40,10],{'red':r'(?is)red.{0,60}\b40\b|\b40\b.{0,60}red','blue':r'(?is)blue.{0,60}\b10\b|\b10\b.{0,60}blue'}),
 ('borealis','Compare two plans for Project Borealis. Budget: 70 euros. Plan A costs 45 euros and takes 4 days. Plan B costs 65 euros and takes 8 days. Hard constraint: finished after 6 days at the latest. State the remaining budget for both plans and decide which plan meets the deadline.',
  [25,5],{'a_rest':r'(?is)plan\s*a.{0,60}\b25\b|\b25\b.{0,60}plan\s*a','b_rest':r'(?is)plan\s*b.{0,60}\b5\b|\b5\b.{0,60}plan\s*b','pick_a':r'(?is)plan\s*a[^.]{0,80}(meets|within|fits|choose|pick|recommend)|(choose|pick|recommend|only)[^.]{0,40}plan\s*a'}),
 ('train','The train to Graz leaves at 07:45 from platform 3. The bus to Linz leaves at 08:10 from stop B. The ferry leaves at 09:30. Which connection leaves first, and from where?',
  [],{'train':r'(?i)train','time':r'07:45|7:45','where':r'(?i)platform\s*3'}),
 ('invoice','Invoice 55-1209 is for 340 euros and due on 2 November. Invoice 55-1210 is for 125 euros and already paid. How much is still open in total, and which invoice number is it?',
  [340],{'num':r'55-1209','amount':r'\b340\b'}),
 ('recipe','A recipe for 4 people needs 300 grams of flour and 2 eggs. How much flour and how many eggs are needed for 6 people?',
  [450,3],{'flour':r'\b450\b','eggs':r'\b3\b[^\d]{0,20}eggs?|eggs?[^\d]{0,20}\b3\b'}),
 ('meeting','The team meeting moved from Monday 10:00 to Wednesday 14:30 because the room was booked. Lena cannot attend on Wednesday. When is the meeting now and who will miss it?',
  [],{'day':r'(?i)wednesday','time':r'14:30|2:30','who':r'(?i)lena'}),
 ('conflict','Note 1 says the server password was changed on 3 May. Note 2 says the password has not been changed since January. Do the notes agree? Explain briefly.',
  [],{'disagree':r"(?i)\b(no|not|don't|do not|contradict|disagree|conflict|inconsisten)"}),
 ('storage','A phone has 128 GB of storage. Apps use 47 GB, photos use 38 GB and the system uses 12 GB. How much space is free?',
  [31],{'free':r'\b31\b'}),
 ('long_detail','Summary of the field report: the survey team visited three villages over two weeks. In the first village they counted 214 households and noted good water access. The second village was smaller, with 96 households, and had a broken pump that was repaired on day 5. The third village had 158 households and the team recommended a second school. How many households did the team count in total, and which village had the broken pump?',
  [468],{'total':r'\b468\b','pump':r'(?i)second'}),
 ('gist','Here are the meeting notes: the budget is tight; marketing wants more ads; engineering wants two more weeks for testing; support reports more complaints about crashes; the CEO wants the release on time. In one or two sentences, what is the main tension?',
  [],{'tension':r'(?i)(release|time|deadline|on time).{0,120}(test|quality|crash)|(test|quality|crash).{0,120}(release|time|deadline|on time)'}),
 ('units','A cyclist rides 18 km in the morning and 27 km in the afternoon. The goal for the day is 50 km. How many kilometres are missing?',
  [5],{'missing':r'\b5\b'}),
 ('choice','Laptop X costs 900 euros and weighs 1.2 kg. Laptop Y costs 750 euros and weighs 2.1 kg. I travel a lot and my limit is 1000 euros. Which laptop fits better and why?',
  [],{'x':r'(?i)laptop\s*x|\bx\b','why':r'(?i)(light|weigh|1\.2)'}),
]
ARMS=('baseline','effort_low','effort_high','no_inquisition','no_coalition','gist_active','attention_active','coupling_0','coupling_1')

def configure(r,arm):
    """Apply one arm in-process; returns an undo callable for module-level patches."""
    undo=[]
    def patch(obj,name,val):
        old=getattr(obj,name);setattr(obj,name,val);undo.append(lambda:setattr(obj,name,old))
    if arm in ('effort_low','effort_high'):EF.set_mode(r.store,arm.split('_')[1])
    elif arm=='no_inquisition':patch(F.Inquisition,'triggers',lambda self,*a,**k:[])
    elif arm=='no_coalition':
        orig=F.admit
        patch(F,'admit',lambda cands,capacity,threshold,interrupt=F.BOOT['sal_interrupt']:orig(cands,max(capacity,len(cands)),0.,interrupt))
    elif arm=='gist_active':
        from v13.gist import Gist
        Gist(r.store).set_mode('ACTIVE','EXPLICIT_HUMAN')
    elif arm=='attention_active':
        from v13.attention import controller
        controller(r).set_mode('ACTIVE','EXPLICIT_HUMAN')
    elif arm.startswith('coupling_'):
        b=dict(F.BOOT);b['uncertainty_coupling_gain']=float(arm.split('_')[1]);patch(F,'BOOT',b)
    return lambda:[u() for u in reversed(undo)]

def score(text,nums,checks):
    a={k:re.search(p,text or '') is not None for k,p in checks.items()}
    n={str(x):re.search(r'(?<![\d.,])'+str(x)+r'(?![\d])',text or '') is not None for x in nums}
    return a,n

def run_arm(installed,arm,fixtures):
    rows=[]
    with tempfile.TemporaryDirectory(prefix='v13-t3-') as tmp:
        home=Path(tmp);cfg=initialize(home)
        for n in ('models','bin'):shutil.rmtree(home/n);(home/n).symlink_to(installed/n,target_is_directory=True)
        shutil.copyfile(installed/'config/models.json',home/'config/models.json')
        save_config(home,cfg|{'learning_mode':'RECORD_ONLY','teacher_enabled':False,'history_turns':0})
        r=Runtime(home);undo=configure(r,arm)
        try:
            for fid,text,nums,checks in fixtures:
                r.session=r.store.new_session();t0=time.monotonic();eid=r.submit(text);end=t0+400
                while not r.idle():
                    if time.monotonic()>end:r.cancel();break
                    time.sleep(.1)
                a=audit_event(r.store,eid);out=a.get('output') or '';meta=a.get('output_metadata') or {}
                ok,num=score(out,nums,checks)
                rows.append({'fixture':fid,'arm':arm,'assertions':ok,'numbers':num,'pass':all(ok.values()) and all(num.values()),
                             'assert_rate':sum(ok.values())/max(1,len(ok)),'turn_s':round(time.monotonic()-t0,2),'offers':[o['role'] for o in a.get('offers',[])],
                             'focal':meta.get('focal'),'output':out[:400]})
                print(json.dumps({k:rows[-1][k] for k in ('arm','fixture','pass','assert_rate','turn_s','offers')}),flush=True)
        finally:
            undo();r.close()
    return rows

def summarize(rows):
    out={}
    for r in rows:
        s=out.setdefault(r['arm'],{'n':0,'pass':0,'assert':0.,'turn_s':0.,'offers':0})
        s['n']+=1;s['pass']+=r['pass'];s['assert']+=r['assert_rate'];s['turn_s']+=r['turn_s'];s['offers']+=len(r['offers'])
    return {a:{'pass_rate':round(s['pass']/s['n'],3),'assert_rate':round(s['assert']/s['n'],3),'mean_turn_s':round(s['turn_s']/s['n'],1),'offers_per_turn':round(s['offers']/s['n'],2),'n':s['n']} for a,s in out.items()}

def main(installed,out,arms=None):
    installed=Path(installed).resolve();out=Path(out);arms=arms.split(',') if arms else ARMS
    prev=json.loads(out.read_text()) if out.exists() else {'rows':[]}
    rows=[r for r in prev['rows'] if r['arm'] not in arms]
    for arm in arms:
        rows+=run_arm(installed,arm,FIX)
        atomic_write(out,json.dumps({'kind':'WP_T3_UTILITY_BENCH','fixtures':[f[0] for f in FIX],'summary':summarize(rows),'rows':rows,
            'claim_limit':'12 short English fixtures, one seed, regex checks on the final answer; direction only'},indent=1))
    print(json.dumps(summarize(rows),indent=1))

if __name__=='__main__':main(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None)
