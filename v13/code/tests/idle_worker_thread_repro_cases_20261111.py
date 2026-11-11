"""Pinned earlier idle scope: an actual event did not identify its worker."""
import json
import threading
import time

from v13 import world_jepa_idle_runtime_candidate as idle
from v13.operator import Operator
from v13.runtime import Runtime


def test_original_dispatched_scope_can_be_claimed_from_another_thread(tmp_path, monkeypatch):
    runtime = Runtime(tmp_path)
    try:
        runtime.sleep.cycle.set_policy('enabled', 'off')
        Operator(runtime).run(':learning shadow')
        step = idle.step; observed = []
        def actual_job(runtime, event):
            caller = threading.Thread(target=lambda:observed.append(step(runtime, event)))
            caller.start();caller.join(timeout=10)
            assert not caller.is_alive() and len(observed) == 1
            assert observed[0]['status'] == 'BLOCKED_INPUT'
            assert idle.status(runtime)['reserved_today'] == 1
            return step(runtime, event)
        monkeypatch.setattr(idle, 'step', actual_job)
        idle.set_enabled(runtime, True, 'EXPLICIT_HUMAN')
        event_id = json.loads(Operator(runtime).run(':learning idle step'))['scheduled']
        end = time.monotonic()+10
        while time.monotonic() < end:
            record = idle.status(runtime)['last_result']
            if record and record.get('event_id') == event_id and runtime.idle():break
            time.sleep(.01)
        assert runtime.idle() and observed and record['status'] == 'SKIPPED_EVENT_ALREADY_RESERVED'
        assert not hasattr(runtime, '_world_jepa_online')
        print('OLD_IDLE_WORKER_THREAD_COUNTEREXAMPLE actual event reserved by foreign thread')
    finally:
        runtime.close()
