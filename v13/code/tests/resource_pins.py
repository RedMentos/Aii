"""Pin a Runtime's resource state for tests.

The Runtime's coordinator thread re-samples real RAM/temperature on every idle
sleep tick (sleep resource_state -> guard.update). A test that only assigns
``runtime.guard.state`` races that thread: a tick between the assignment and
the code under test overwrites the injected state with the container's real
NORMAL/RECOVERY state (test_bodies TightBudget failed ~5 % of runs that way).
Pinning ``runtime.resources`` alone is not enough: a tick that already looked
up ``guard.update`` or read a real sample before the pin still applies it.

So ``pin`` installs a fresh guard that evaluates one fixed sample whatever a
caller passes in. A tick still in flight on the old guard only mutates the old
object, which nothing reads any more (no component caches ``runtime.guard``)."""
from v13.resources import ResourceGuard

MB=1024*1024
def sample(runtime,state):
    """A resource sample that ResourceGuard.update maps to ``state`` (CRITICAL, PRESSURE or NORMAL)."""
    floor=runtime.cfg['minimum_free_mb']*MB
    mem={'CRITICAL':floor//2,'PRESSURE':floor+floor//2,'NORMAL':8*floor}[state]
    return {'wall_time':0.,'mem_available_bytes':mem,'mem_total_bytes':16*floor,'free_disk_bytes':10**12,
            'battery_temperature_c':None,'battery_percent':None,'charging':None,'processes':[],'own_peak_rss_bytes':0}

class PinnedGuard(ResourceGuard):
    """ResourceGuard whose every update evaluates the pinned sample (the real transition rules still apply)."""
    def __init__(self,cfg,row):super().__init__(cfg);self.row=row
    def update(self,_ignored):return super().update(dict(self.row))

def pin(runtime,state):
    """Route all resource reads and guard updates of ``runtime`` to a fixed sample; returns the resulting state."""
    row=sample(runtime,state);guard=PinnedGuard(runtime.cfg,row)
    runtime.resources=lambda:dict(row);runtime.guard=guard
    return guard.update(None)
