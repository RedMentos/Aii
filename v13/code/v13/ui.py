"""Interactive input stays responsive while the coordinator generates text."""
import sys
import threading
from .common import safe_text
from .operator import Operator
from .phone_halt import watch as watch_buttons

def typing():
    """True while the operator has unsent text in the input line (readline only)."""
    try:
        import readline
        return bool(readline.get_line_buffer())
    except Exception:return False

def read_block(prompt,ready=None,read=input):
    """One input; lines that arrive within 50 ms (a multi-line paste) join into one block."""
    lines=[read(prompt)]
    if ready is None:
        import select
        ready=lambda:bool(select.select([sys.stdin],[],[],.05)[0])
    try:
        while len(lines)<500 and ready():lines.append(read(''))
    except (EOFError,OSError,ValueError):pass
    return '\n'.join(lines)

def visible_delta(store, session, cursor, seen, limit=256):
    """Bounded plain-UI history cursor with streaming suffix updates.

    On first render show the latest eight messages, as before. Afterwards
    drain every committed message in ascending ID order, even if more than
    eight arrived between render ticks. Keep only recent/active lengths.
    """
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError('UI history page limit')
    recent = store.history(session, 8)
    if cursor is None:
        cursor = max(0, int(recent[0]['id']) - 1) if recent else 0
    query = getattr(store, 'rows', None)
    if callable(query):
        fresh = query('SELECT * FROM messages WHERE session_id=? AND id>? ORDER BY id LIMIT ?',
                      (session, cursor, limit))
        if fresh:
            cursor = int(fresh[-1]['id'])
        active = query("SELECT * FROM messages WHERE session_id=? AND id<=? "
                       "AND status IN ('DRAFT','STREAMING','OUTPUT_COMMITTED') "
                       "ORDER BY id DESC LIMIT 32", (session, cursor))
    else:
        # Legacy UI-only test doubles without SQL have no paginated source.
        fresh = [m for m in recent if m['id'] > cursor]
        if fresh:
            cursor = int(fresh[-1]['id'])
        active = []
    out = []
    visited = set()
    def add(message):
        mid = int(message['id'])
        if mid in visited:
            return
        visited.add(mid)
        if message['role'] == 'user':
            return
        content = message['text'] or ''
        old = seen.get(mid, 0)
        if len(content) > old:
            out.append((message['role'], content[old:], old == 0))
        seen[mid] = len(content)
    for message in fresh:
        add(message)
    for message in sorted(active + [m for m in recent if m['id'] <= cursor],
                          key=lambda m: m['id']):
        add(message)
    keep = {int(m['id']) for m in recent + active}
    for mid in list(seen):
        if mid not in keep:
            seen.pop(mid, None)
    return cursor, out


def plain(r):
    op=Operator(r);done=threading.Event();seen={};cursor=[None];current_session=[r.session];held=[];held_lock=threading.Lock()
    def show_notices(items):
        for x in items:print('\n[V13] '+safe_text(x),flush=True)
    def notify(t):
        # Worker threads only enqueue. Printing here could overtake a notice
        # already claimed by render but not yet formatted/output.
        with held_lock:
            held.append(t)
    r.notify=notify
    watch_buttons(r)  # WP-UI1: Termux home-screen stop requests, ON-only
    def render():
        while not done.wait(.1):
            if typing():continue
            with held_lock:
                if typing():continue
                ready=held[:];held.clear()
            # A notice must not remain hidden indefinitely merely because
            # no second worker notification arrives after typing ends.
            show_notices(ready)
            if r.session != current_session[0]:
                current_session[0]=r.session;cursor[0]=None;seen.clear()
            cursor[0],changes=visible_delta(r.store,r.session,cursor[0],seen)
            for role,delta,first in changes:
                print(('\n'+role+'> ' if first else '')+safe_text(delta),end='',flush=True)
    t=threading.Thread(target=render,daemon=True);t.start()
    try:
        print('V13 lokal · :help · Strg+C bricht ab · :shutdown beendet',flush=True)
        while not r.stop.is_set():
            try:line=read_block('\ndu> ')
            except KeyboardInterrupt:r.cancel();continue
            except EOFError:break
            try:
                result=op.run(line)
                if line.startswith(':') and result:print(safe_text(result),flush=True)
            except Exception as exc:print('[Fehler] '+safe_text(exc),flush=True)
    finally:done.set();t.join(1)

def chat(r,force_plain=False):
    if force_plain or not sys.stdin.isatty():return plain(r)
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.layout import Layout,HSplit,Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.widgets import TextArea
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.styles import Style
        from prompt_toolkit.document import Document
    except ImportError:return plain(r)
    op=Operator(r);notices=[];notice_lock=threading.Lock();last_view=[None];app=None
    def notice(text):
        with notice_lock:notices.append(safe_text(text));del notices[:-8]
        if app:app.invalidate()
    r.notify=notice
    watch_buttons(r)  # WP-UI1: same stop watcher in prompt-toolkit UI
    transcript=TextArea(text='',read_only=True,scrollbar=True,wrap_lines=True,focusable=True)
    def accept(buffer):
        text=buffer.text
        if not text.strip():return False
        try:
            result=op.run(text)
            if text.startswith(':') and result:notice(result)
        except Exception as exc:notice('Fehler: '+str(exc))
        if r.stop.is_set():app.exit()
        return False
    inputbox=TextArea(height=3,prompt='du › ',multiline=False,wrap_lines=True,accept_handler=accept)
    def header():return ' V13 · Age 0 · '+r.cfg['learning_mode']+' · '+r.status+' · Wartend: '+str(r.jobs.qsize())+' '
    layout=Layout(HSplit([Window(FormattedTextControl(header),height=1,style='class:header'),transcript,Window(height=1,char='─'),inputbox,Window(FormattedTextControl(' :help  Strg+C Abbruch  Strg+D Ende  Tab Verlauf/Eingabe  Esc Eingabe '),height=1,style='class:footer')]),focused_element=inputbox)
    kb=KeyBindings()
    from prompt_toolkit.keys import Keys
    @kb.add(Keys.BracketedPaste)
    def paste(event):
        # WP-V5: a multi-line paste stays one input block.
        inputbox.buffer.insert_text(event.data.replace('\r\n','\n').replace('\r','\n'))
    @kb.add('c-c')
    def cancel(event):r.cancel()
    @kb.add('c-d')
    def close(event):r.stop.set();r.cancel_event.set();event.app.exit()
    @kb.add('f1')
    def help_(event):notice(op.run(':help'))
    @kb.add('tab')
    def focus(event):event.app.layout.focus(transcript if event.app.layout.has_focus(inputbox) else inputbox)
    @kb.add('escape')
    def input_(event):event.app.layout.focus(inputbox)
    def refresh(application):
        rows=r.store.history(r.session,250);pieces=[]
        for m in rows:pieces.append(('Du' if m['role']=='user' else m['role'])+' · '+m['status']+'\n'+safe_text(m['text']))
        with notice_lock:pieces+=['[Status] '+x for x in notices]
        text='\n\n'.join(pieces)
        if text!=last_view[0]:
            pos=len(text) if application.layout.has_focus(inputbox) else min(transcript.buffer.cursor_position,len(text))
            transcript.buffer.set_document(Document(text,pos),bypass_readonly=True);last_view[0]=text
    app=Application(layout=layout,key_bindings=kb,full_screen=True,refresh_interval=.25,before_render=refresh,style=Style.from_dict({'header':'bg:#163b46 #ffffff','footer':'bg:#20242b #9bc4d5'}),mouse_support=False)
    app.run()
