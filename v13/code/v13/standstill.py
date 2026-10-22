"""Full standstill (:stillstand, WP-SAFE2): one user command that stops every change V13 could make on its own.

Why: :notaus only stops tools and approvals (and the running turn); learning, replay, sleep/dream, timers and queued
training jobs keep running. :pause stops the job queue (and with it the scheduler tick, all background work and
per-turn learning) but leaves tools and Age promotion alone, and :age freeze only stops Age promotion. Review point 2
of PR #27 (GPT, 22.10.): "freeze must mean a confirmed stop of all affected changes". This module combines the three
existing switches, waits for the running job to end and reports what is confirmed and what is not.

Parts (each an existing, persisted switch, so a restart stays in standstill):
  notaus  prohibitions.halt   no tool call, no approval is executed
  queue   Runtime.pause       no turn, no learning/replay/sleep/dream/training job, no scheduler tick; running job cancelled
  age     AgeControl.freeze   no Age promotion
Release (:stillstand aus) only undoes the parts this command switched on itself; parts the user had set before stay.
Not covered (said in the status): operator commands the user types himself still run, and an external process that
ignores the cancel signal is only reported, never claimed as stopped.
"""
import time
from . import age as agectl
from . import prohibitions as P

KEY='STANDSTILL'
REVISION='v13-standstill-v1'
WAIT_SECONDS=10.


def _state(store):return store.state(KEY,{'revision':REVISION,'on':False,'since':None,'set':{}})


def _held_background(r):
    """Scheduler events that would run after release (pending or held), so release never resumes silently."""
    try:
        st,_=r.sleep.scheduler._load()
        return sum(1 for e in st['events'] if e['status'] in {'PENDING','HELD_AGE'} and e['origin']!='USER')
    except Exception:return None


def parts(r):
    a=agectl.controller(r)
    return {'notaus':bool(P.report(r.store)['notaus']),'queue':bool(r.paused and r.store.queue_paused()),
            'age':bool(a.view()['frozen'])}


def status(r):
    st,_=_state(r.store);p=parts(r);job=r.current
    return {'revision':REVISION,'on':bool(st['on']),'since':st['since'],'parts':p,'all_parts_on':all(p.values()),
            'running_job':job,'confirmed_still':bool(all(p.values()) and job is None),'set_by_standstill':st['set'],
            'background_waiting':_held_background(r),
            'claim_limit':'Stops tools, approvals, the job queue (turns, learning, replay, sleep, dream, training, scheduler) '
                          'and Age promotion. Operator commands typed by the user still run.'}


def engage(r,wait=WAIT_SECONDS,clock=time.monotonic):
    st,v=_state(r.store);before=parts(r)
    P.halt(r.store,True,authority=P.HUMAN)
    if not before['queue']:r.pause()
    else:r.cancel()
    if not before['age']:agectl.controller(r).freeze(True)
    newly={k:not before[k] for k in before}
    if st['on']:newly={k:bool(st['set'].get(k) or newly[k]) for k in newly}  # repeated call keeps the first record
    r.store.set_state(KEY,{'revision':REVISION,'on':True,'since':st['since'] or time.time(),'set':newly},expected=v)
    end=clock()+max(0.,float(wait))
    while r.current is not None and clock()<end:time.sleep(.02)
    r.store.log('standstill',None,{'on':True,'set':newly,'running_job':r.current})
    return status(r)


def release(r):
    st,v=_state(r.store)
    if not st['on']:return status(r)
    done=st['set']
    if done.get('age'):agectl.controller(r).freeze(False)
    if done.get('notaus'):P.halt(r.store,False,authority=P.HUMAN)
    waiting=_held_background(r)
    r.store.set_state(KEY,{'revision':REVISION,'on':False,'since':None,'set':{}},expected=v)
    if done.get('queue'):r.resume()
    r.store.log('standstill',None,{'on':False,'released':done,'background_waiting':waiting})
    return status(r)|{'released':done,'background_resumes':waiting}


def text(s):
    if not s['on'] and not s.get('released'):
        return 'Stillstand: aus. (:stillstand hält alles an: Werkzeuge, Lernen, Hintergrund, Alterung.)'
    names={'notaus':'Werkzeuge und Freigaben','queue':'Aufgaben, Lernen, Traum/Schlaf, Hintergrund','age':'Alterung (Stufenaufstieg)'}
    if s.get('released') is not None:
        kept=[names[k] for k,on in s['parts'].items() if on]
        out=['Stillstand aufgehoben.']
        if kept:out.append('Weiter angehalten (vorher schon von dir gesetzt): '+', '.join(kept)+'.')
        if s.get('background_resumes'):out.append(f"{s['background_resumes']} wartende Hintergrund-Aufgaben laufen jetzt wieder an.")
        return '\n'.join(out)
    lines=['STILLSTAND AN.']
    for k,label in names.items():lines.append(('  angehalten: ' if s['parts'][k] else '  NICHT angehalten: ')+label)
    if s['running_job']:lines.append(f"  ACHTUNG: laufender Vorgang „{s['running_job']}“ hat noch nicht aufgehört (Abbruch angefordert). :stillstand status prüft erneut.")
    elif s['confirmed_still']:lines.append('  Bestätigt: kein Vorgang läuft mehr.')
    lines.append('Deine eigenen Befehle gehen weiter. Aufheben: :stillstand aus')
    return '\n'.join(lines)


def operator_command(r,args):
    """:stillstand [aus|status|json]"""
    import json
    if not args:return text(engage(r))
    if args==['aus']:return text(release(r))
    if args==['status']:return text(status(r))
    if args==['json']:return json.dumps(status(r),ensure_ascii=False,sort_keys=True)
    raise ValueError(':stillstand | :stillstand aus | :stillstand status | :stillstand json')
