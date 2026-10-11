"""Cooperative inference priority at bounded training-slice boundaries."""

from contextlib import contextmanager
import threading
from typing import Callable, Iterator


class Coordinator:
    """Serializes compute and announces inference before waiting for a slice.

    A running native kernel cannot be interrupted by this Python mechanism.
    The waiting time includes its remaining duration; there is no zero-latency
    or hard-real-time guarantee. Callbacks must remain short and poll cancel.
    """

    def __init__(self) -> None:
        self._state = threading.Lock()
        self._compute = threading.Lock()
        self._inference_requested = threading.Event()
        self._inference_users = 0

    @property
    def inference_requested(self) -> bool:
        return self._inference_requested.is_set()

    @contextmanager
    def inference(self) -> Iterator[None]:
        with self._state:
            self._inference_users += 1
            self._inference_requested.set()
        acquired = False
        try:
            self._compute.acquire()
            acquired = True
            yield
        finally:
            with self._state:
                self._inference_users -= 1
                if self._inference_users == 0:
                    self._inference_requested.clear()
            if acquired:
                self._compute.release()

    def training_slice(self, operation: Callable[[Callable[[], bool]], None]) -> bool:
        if self.inference_requested:
            return False
        with self._compute:
            if self.inference_requested:
                return False
            operation(self._inference_requested.is_set)
            return True
