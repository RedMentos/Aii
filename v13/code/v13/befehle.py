"""Scrollable command guide in plain German (WP-UI1): :befehle [Wort] shows docs/BEFEHLE.md, or only the matching
entries. The same file is opened by the home-screen button „V13 Befehle“. Read-only, no model involved."""
from .common import APP

PATH=APP/'docs/BEFEHLE.md'


def entries(text):
    """(section, block) per command entry; a block starts at a line beginning with ':' and runs to the next one."""
    out=[];section='';block=[]
    def flush():
        if block:out.append((section,'\n'.join(block).rstrip()))
    for line in text.splitlines():
        if line.startswith('## '):flush();block=[];section=line[3:].strip();continue
        if line.startswith(':'):flush();block=[line];continue
        if line and not line.startswith((' ',':')):flush();block=[];continue  # free text ends an entry
        if block:block.append(line)
    flush();return out


def operator_command(r,args):
    text=PATH.read_text(encoding='utf-8')
    if not args:return text
    words=[a.lower().lstrip(':') for a in args]
    hits=[(s,b) for s,b in entries(text) if all(w in b.lower() for w in words)]
    if not hits:return 'Nichts gefunden zu „'+' '.join(args)+'“. :befehle ohne Wort zeigt die ganze Liste.'
    return '\n\n'.join(b+'\n    (Abschnitt: '+s+')' for s,b in hits)
