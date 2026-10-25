"""Run388 opt-in AG2 pre-action tool hook contract (RED scaffold; no live wiring).

This module has no effect unless a ToolRegistry is explicitly constructed with
on_pre_execute, on_outcome and on_abort callbacks. It must not be wired into
Growth or active model/age paths without separate registered acceptance.
"""
from .grounding import Grounding


class PreActionGrounding:
    def __init__(self, grounding: Grounding):
        self.grounding = grounding

    def before(self, tx):
        return None  # RED scaffold: no pre-action prediction yet

    def after(self, tx):
        return None

    def abort(self, tx):
        return False
