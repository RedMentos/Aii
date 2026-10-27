"""Consumers of released modules (WP-BP11b): the only two readers of modules_gate.corpus().

1. recall(): look up module knowledge for a question. Read-only retrieval (token overlap, memory.relevance), every hit
   carries its tag MODULE:<id>:<sha8> and the label "aus Modul, nicht als wahr geprüft". Reachable for a body only through
   the tool `module_recall` (READ_LOCAL, off until the user enables it, passes bans and user rules like every tool).
2. export_dataset(): writes the tagged items as JSONL for a later training run (TTY command `:modul export`). Nothing trains
   from it automatically.
Both return nothing unless the module feature, the learning switch, the module state and the safety parts agree
(modules_gate.corpus). Revoking a module removes it from both at once. Weights already trained from an exported file are not
undone by a revoke: retrain from a fresh export. Claim limit: plumbing and provenance tested on synthetic modules; no learning
gain measured, no model change.
"""
import json
from .common import atomic_write,digest
from . import modules_gate as M
from .memory import relevance

LABEL='aus Modul, nicht als wahr geprüft'
MIN_SCORE=0.15

def recall(store,query,k=3):
    """Top-k module items for the question, best first. Empty when nothing is released/allowed or nothing is relevant."""
    q=str(query or '')[:500]
    if not q.strip():return []
    hits=[]
    for it in M.corpus(store):
        sc=max(relevance(q,it['text']),relevance(q,(it['title'] or '')+' '+it['text']))
        if sc>=MIN_SCORE:hits.append((sc,it))
    hits.sort(key=lambda x:(-x[0],x[1]['tag'],x[1]['text']))
    return [{'text':it['text'],'title':it['title'],'tag':it['tag'],'score':round(sc,3),'label':LABEL} for sc,it in hits[:max(1,min(int(k),10))]]

def tool(store):
    """Tool body for module_recall, bound to one store."""
    def run(query):
        hits=recall(store,query);return {'hits':hits,'count':len(hits),'label':LABEL}
    return run

def _export_gate(store):
    # An export writes locally; a typed ban on this exact tool must take
    # precedence even when the read-only module corpus is still available.
    why=M.gate(store,'module_export','WRITE_LOCAL',({'WRITE_LOCAL','LEARN'},{'MODULE','FILE'}))
    if why:raise PermissionError('Modul-Export gesperrt: '+why)


def export_dataset(store,path):
    """JSONL, one tagged item per line, plus the digest of the content. Returns {'path','items','digest'}; raises when nothing is released."""
    _export_gate(store)  # Notaus/ban before corpus or no-data error.
    initial_version=M.box(store).load()[1]
    items=M.corpus(store)
    if not items:raise ValueError('Nichts freigegeben oder Lernen aus: kein Export (:modul lernen an, Modul freigeben)')
    body='\n'.join(json.dumps({'text':i['text'],'title':i['title'],'tag':i['tag']},ensure_ascii=False,sort_keys=True) for i in items)+'\n'
    _export_gate(store)  # Recheck after source reads, before write.
    # A revoke/disable while reading cannot be turned into a new training
    # dataset. Re-read bytes as well as the version (ABA switch toggles count).
    if M.box(store).load()[1]!=initial_version or M.corpus(store)!=items or M.box(store).load()[1]!=initial_version:
        raise PermissionError('Modul während des Exports geändert oder zurückgenommen')
    _export_gate(store)
    atomic_write(path,body.encode());return {'path':str(path),'items':len(items),'digest':digest(body)}
