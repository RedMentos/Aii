"""Shared plumbing for the WP-AG growth modules (FORSCHUNG.md §9, ROADMAP WP-AG1..AG12).

Every module keeps one versioned JSON state in store.states (optimistic write with
the read version), checks Age rights through age.AgeControl and never grants itself
authority: anything that would touch weights, structure, hard rules or the outside
world ends as a PENDING human request, not as an action.
"""
import math
import time
from ..common import uid,dumps

ORIGINS=('USER','SYSTEM','SELF')

class StateBox:
    """Versioned state slot. mutate(fn) re-reads and retries once on a concurrent write."""
    def __init__(self,store,key,revision,empty):
        self.s=store;self.key=key;self.revision=revision;self.empty=empty
    def load(self):
        st,v=self.s.state(self.key,None)
        if st is None:st=self.empty()|{'revision':self.revision}
        if st.get('revision')!=self.revision:raise ValueError(self.key+': state revision mismatch')
        return st,v
    def mutate(self,fn):
        for attempt in (0,1):
            st,v=self.load();out=fn(st)
            dumps(st)  # JSON-safe or fail before writing
            try:self.s.set_state(self.key,st,expected=v);return out
            except ValueError:
                if attempt:raise

def age_allows(age,right,origin='SELF',resource_mode='GREEN'):
    """USER-initiated work is not V13's own initiative; SYSTEM/SELF need the Age right. No controller = Age 0."""
    if origin=='USER':return True
    if age is None:
        from ..age import RIGHTS
        return RIGHTS.get(right,99)==0
    try:return age.may(right,resource_mode=resource_mode) if hasattr(age,'may') else age.allowed(right,resource_mode=resource_mode)  # WP-T2 per capability
    except Exception:return False

def budget(age,name,default=0):
    if age is None:return default
    try:return age.budgets('system').get(name,default)
    except Exception:return default

def clamp01(x):
    """Clamp a measured probability; nonfinite values carry zero evidence."""
    value=float(x)
    if not math.isfinite(value):
        return 0.
    return max(0.,min(1.,value))

def new_id(prefix):return uid(prefix)

def ts(clock=None):return (clock or time.time)()
