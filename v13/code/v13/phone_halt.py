"""Stop buttons on the phone home screen (WP-UI1): a Termux:Widget tap reaches the running chat.

Why: on the phone the user may not be in the chat window when something has to stop now. A home-screen button
(Termux:Widget, see scripts/termux_widget/) cannot type into the chat, and a second process cannot open the store
(Store holds the coordinator lock). So the button only drops a request file into <home>/control/, and the running
chat applies it with exactly the same functions as the typed commands (:notaus, :stillstand).

Rules:
- One direction only: a file can switch Notaus or Stillstand ON, never off. Lifting stays a typed command in the
  chat (:notaus aus, :stillstand aus), so a stray file or another app with Termux rights can never weaken a stop.
- A request that is there at chat start is applied before the first input, so V13 starts already stopped.
- Every handled file is renamed to <name>.erledigt-<time>, so it is not applied again after a typed release.
- Unknown file names are ignored; the file content is never read or interpreted.
"""
import threading
import time
from . import prohibitions as P
from . import standstill

DIR='control'
REQUESTS=('STILLSTAND','NOTAUS')  # STILLSTAND first: it already contains Notaus
POLL_SECONDS=.5


def control_dir(home):
    d=home/DIR;d.mkdir(parents=True,exist_ok=True,mode=0o700);return d


def pending(home):
    d=control_dir(home);return [n for n in REQUESTS if (d/n).exists()]


def _done(path,clock=time.time):
    try:path.rename(path.with_name(path.name+'.erledigt-'+time.strftime('%Y%m%dT%H%M%S',time.localtime(clock()))))
    except FileNotFoundError:pass
    except OSError:
        try:path.unlink()
        except OSError:pass


def apply_once(r,notify=None):
    """Apply every waiting request; returns the texts shown to the user."""
    out=[];d=control_dir(r.home)
    for name in pending(r.home):
        if not (d/name).exists():continue  # covered by an earlier request in this round
        if name=='STILLSTAND':text='Knopf „Stillstand“ gedrückt.\n'+standstill.text(standstill.engage(r))
        else:text='Knopf „Notaus“ gedrückt.\n'+P.notaus_command(r,[])
        r.store.log('phone_halt_button',None,{'request':name})
        _done(d/name);out.append(text)
        if name=='STILLSTAND' and (d/'NOTAUS').exists():_done(d/'NOTAUS')  # already covered
        if notify:notify(text)
    return out


def watch(r,notify=None,poll=POLL_SECONDS):
    """Background thread for the chat; ends with r.stop. Applies requests already waiting before it returns."""
    say=notify or (lambda t:r.notice(t))
    try:apply_once(r,say)
    except Exception as exc:say('Stopp-Knopf: Fehler beim Anwenden: '+str(exc))
    def loop():
        while not r.stop.wait(poll):
            try:apply_once(r,say)
            except Exception as exc:say('Stopp-Knopf: Fehler beim Anwenden: '+str(exc))
    t=threading.Thread(target=loop,name='v13-phone-halt',daemon=True);t.start()
    return t


def prestart(home):
    """Apply pre-existing home-screen STOP requests before CLI constructs Runtime.

    Store's coordinator lock serializes this preflight with Runtime startup.
    All stop flags and the original human ownership record are committed in
    ONE SQLite transaction; request files are acknowledged only afterwards.
    This intentionally does not claim to cover direct Runtime(home) callers.
    """
    import json
    from pathlib import Path
    from . import age as A
    from .common import dumps
    from .store import Store

    home=Path(home)
    names=pending(home)
    if not names:return []
    s=Store(home)
    try:
        with s.tx() as c:
            prohibitions, pv=P.load(s)
            if prohibitions.get('fail_closed'):
                raise ValueError('Unlesbarer Notaus-Zustand; Widget-Datei bleibt erhalten')
            if 'STILLSTAND' in names:
                age_state, av=s.state(A.STATE_KEY,None)
                age_state=A.default_state() if age_state is None else age_state
                if (not isinstance(age_state,dict) or age_state.get('revision')!=A.REVISION
                    or not isinstance(age_state.get('frozen'),bool)
                    or not isinstance(age_state.get('history'),list)):
                    raise ValueError('Unlesbarer Age-Zustand; Widget-Datei bleibt erhalten')
                state, sv=s.state(standstill.KEY,None)
                state=({'revision':standstill.REVISION,'on':False,'since':None,'set':{}}
                       if state is None else state)
                if (not isinstance(state,dict) or state.get('revision')!=standstill.REVISION
                    or not isinstance(state.get('on'),bool) or not isinstance(state.get('set'),dict)
                    or any(k not in ('notaus','queue','age') or not isinstance(v,bool)
                           for k,v in state['set'].items())):
                    raise ValueError('Unlesbarer Stillstand-Zustand; Widget-Datei bleibt erhalten')
                before={'notaus':prohibitions['halt'],
                        'queue':s.queue_paused(),'age':age_state['frozen']}
                newly={k:not v for k,v in before.items()}
                if state['on']:
                    newly={k:bool(state['set'].get(k,False) or newly[k]) for k in newly}
                # No coordinator exists yet. This durable queue gate is committed
                # before Runtime can start its worker or recover queued turns.
                c.execute("INSERT OR REPLACE INTO meta VALUES (?,?)",('queue_paused',dumps(True)))
                if not age_state['frozen']:
                    age_state['frozen']=True
                    A.AgeControl(s,{})._event(age_state,'FREEZE','system',None,None,'user')
                    c.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)",
                              (A.STATE_KEY,av+1,dumps(age_state)))
                state.update(on=True,since=state.get('since') or time.time(),set=newly)
                c.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)",
                          (standstill.KEY,sv+1,dumps(state)))
                names_to_ack=['STILLSTAND']+(['NOTAUS'] if 'NOTAUS' in names else [])
                notices=['Knopf „Stillstand“ vor dem Start angewendet. Aufheben nur mit :stillstand aus.']
                action='STILLSTAND'
            else:
                names_to_ack=['NOTAUS']
                notices=['Knopf „Notaus“ vor dem Start angewendet. Aufheben nur mit :notaus aus.']
                action='NOTAUS'
            if not prohibitions['halt']:
                prohibitions['halt']=True
                prohibitions['halt_since']=time.time()
                prohibitions['changes']=prohibitions.get('changes',0)+1
                c.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)",
                          (P.KEY,pv+1,dumps(prohibitions)))
            c.execute("INSERT INTO telemetry(kind,event_id,metrics,created) VALUES (?,?,?,?)",
                      ('phone_halt_button',None,dumps({'request':action,'phase':'prestart'}),time.time()))
        # A crash between COMMIT and rename is safe: a retry keeps the
        # persisted 'set_by_standstill' ownership and never releases a stop.
        d=control_dir(home)
        for name in names_to_ack:_done(d/name)
        return notices
    finally:
        s.close()
