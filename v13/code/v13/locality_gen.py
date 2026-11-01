"""WP-BP2b: near-miss training questions for the weight-learning path, generated from the fact question itself (no model, no hand list).

BP2a showed that KL-anchoring questions about OTHER people to the base body cuts the leak of a newly learned fact (0.75 -> 0.19), but
those questions were hand-written. In daily use the human teaches arbitrary facts, so the anchors must come from the question text:
the personal subject is swapped for another person and the verb is kept grammatical. Only first-person questions are rewritten;
anything that does not match a known pattern yields no anchor (reported, never invented). Pure functions, no I/O.
"""
import re

# Subjects used for TRAINING anchors. Keep disjoint from any evaluation subjects and from lora_trainer.SWAP_NOUNS' evaluation use.
TRAIN_SUBJECTS=('friend','mother','father','boss','cousin','uncle','colleague','neighbour','grandmother','son')
# Subjects for the GATE's near-miss questions: never used as training anchors (evaluation stays held-out).
EVAL_SUBJECTS=('wife','nephew','girlfriend','stepbrother','granddaughter','sister')
_POSS=re.compile(r"\bmy (\w+)(?!'s)\b",re.I)

def variants(question,subjects=TRAIN_SUBJECTS,k=2):
    """Up to k near-miss rewrites of a first-person question about other people. [] when no pattern matches."""
    q=question.strip()
    out=[]
    for i,p in enumerate(subjects):
        if len(out)>=k:break
        r=_rewrite(q,p)
        if r and r!=q and r not in out:out.append(r)
    return out

def _rewrite(q,p):
    # 1) "... my <noun> ..." -> "... my <p>'s <noun> ..." ; the noun after "my" becomes owned by the other person
    m=_POSS.search(q)
    if m:
        return q[:m.start()]+"my %s's %s"%(p,m.group(1))+q[m.end():]
    # 2) "Where do I work?" / "Which city did I move to last year?" / "What language am I learning?" -> my <p>
    for pat,rep in ((r"\bdo I\b","does my %s"),(r"\bdid I\b","did my %s"),(r"\bam I\b","is my %s"),(r"\bhave I\b","has my %s"),
                    (r"\bwas I\b","was my %s"),(r"\bshould I\b","should my %s"),(r"\bcan I\b","can my %s"),(r"\bwill I\b","will my %s")):
        m=re.search(pat,q)
        if m:return q[:m.start()]+rep%p+q[m.end():]
    return None

def anchors_for(questions,subjects=TRAIN_SUBJECTS,k=2):
    """(anchor list, report). Report counts questions that got no anchor so the caller can see the coverage."""
    out=[];missed=[]
    for n,q in enumerate(questions):
        rot=tuple(subjects[(n*k+j)%len(subjects)] for j in range(len(subjects)))  # spread subjects across facts
        v=variants(q,rot,k)
        if not v:missed.append(q)
        out+=v
    return out,{'questions':len(questions),'anchors':len(out),'no_pattern':missed}
