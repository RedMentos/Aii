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
