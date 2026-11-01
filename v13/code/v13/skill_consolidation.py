"""WP-FS7 episode source: executed tool calls of past turns -> procedure schemas -> CANDIDATE skills (SkillLibrary).

Mode (cfg['skill_schema_mode'], default 'shadow'): off | shadow (count what would be proposed, write nothing) | active
(propose CANDIDATE skills; promotion stays with the normal lifecycle, a non-user origin never reaches TRUSTED without Age/user).
Only successful calls with a stored user question are episodes. Private-looking questions (e-mail, phone, key words) are skipped,
and a question is never stored in a skill: only the slotted steps and up to six common trigger words are.
"""
import hashlib,json,re
MODES=('off','shadow','active')
_PRIV=re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+|(?<!\d)(?:\+|00)\d[\d ()/-]{7,}\d|\b(?:passwort|password|token|api[ _-]?key)\b',re.I)

def episodes(runtime,limit=200):
    from .agi import hub
    reg=hub(runtime).tools;calls=reg.box.load()[0]['calls'];by={}
    for c in calls:
        if c.get('status')!='EXECUTED' or c.get('error') or not c.get('event_id'):continue
        by.setdefault(c['event_id'],[]).append({'tool':c['tool'],'args':c['args']})
    out=[]
    for eid,steps in list(by.items())[-limit:]:
        row=runtime.store.one("SELECT text FROM messages WHERE event_id=? AND role='user' ORDER BY rowid LIMIT 1",(eid,))
        text=(row['text'] if row else '') or ''
        if text and not _PRIV.search(text) and all(isinstance(v,(str,int,float)) for s in steps for v in s['args'].values()):
            out.append({'id':eid,'text':text,'steps':steps})
    return out

def run(runtime,min_support=2):
    from .agi import hub,schema
    mode=runtime.cfg.get('skill_schema_mode','shadow')
    if mode=='off':return {'mode':mode,'status':'OFF'}
    eps=episodes(runtime);groups=[g for g in schema.induce(eps,min_support) if g['stage']=='SCHEMA']
    rep={'mode':mode,'episodes':len(eps),'schemas':len(groups),'proposed':[]}
    if mode=='active':
        lib=hub(runtime).skills;have={json.dumps(s['steps'],sort_keys=True) for s in lib.box.load()[0]['skills'].values() if s.get('kind')=='schema'}
        new=[g for g in groups if json.dumps(g['steps'],sort_keys=True) not in have]
        for g in new:
            name='sch_'+hashlib.sha256(json.dumps(g['steps'],sort_keys=True).encode()).hexdigest()[:8]
            try:lib.propose(name,g['steps'],trigger=' '.join(g['trigger'][:6]),origin='SELF')
            except ValueError:continue
            lib.box.mutate(lambda st,n=name:st['skills'][n].update(kind='schema'));rep['proposed'].append(name)
    return rep
