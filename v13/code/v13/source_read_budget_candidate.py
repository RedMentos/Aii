"""Cooperative deadline/cancellation for a source read in a staged Runtime."""
from contextlib import contextmanager
import math
import time


class ReadBudgetExceeded(ValueError):
    pass


class Budget:
    def __init__(self, deadline=None, should_continue=None, clock=time.monotonic):
        if deadline is not None and (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ValueError('invalid source read deadline')
        if should_continue is not None and not callable(should_continue):
            raise ValueError('invalid source read cancellation callback')
        if not callable(clock):
            raise ValueError('invalid source read clock')
        self.deadline, self.should_continue, self.clock = deadline, should_continue, clock
        self.check()

    def check(self):
        if self.should_continue is not None and self.should_continue() is not True:
            raise ReadBudgetExceeded('source read cancelled')
        if self.deadline is not None and self.clock() >= self.deadline:
            raise ReadBudgetExceeded('source read deadline reached')

    @contextmanager
    def transaction(self, store):
        self.check()
        if self.deadline is None:
            with store.tx() as conn:
                self.check()
                yield conn
                self.check()
            return
        # Both mutex waiting and SQLite busy waiting must fit the read budget.
        acquired = False
        try:
            while not acquired:
                self.check()
                remaining = self.deadline - self.clock()
                acquired = store.mutex.acquire(timeout=max(0., min(.02, remaining)))
            self.check()
            if store.db.in_transaction:
                raise ValueError('bounded source read cannot start inside an existing transaction')
            old_timeout = store.db.execute('PRAGMA busy_timeout').fetchone()[0]
            wait_ms = max(1, min(50, int((self.deadline - self.clock()) * 1000)))
            store.db.execute('PRAGMA busy_timeout=' + str(wait_ms))
            try:
                with store.tx() as conn:
                    self.check()
                    yield conn
                    self.check()
            finally:
                store.db.execute('PRAGMA busy_timeout=' + str(old_timeout))
        finally:
            if acquired:
                store.mutex.release()
