"""Fixed Age-0 envelope. No self-promotion or learned scheduler exists here."""

from dataclasses import dataclass
import math
from typing import Tuple

from .contracts import finite


def budget_steps(compute_budget: float, maximum: int = 8) -> int:
    budget = finite(compute_budget, "compute_budget")
    if not 0 <= budget <= 1:
        raise ValueError("compute_budget must be in [0, 1]")
    if type(maximum) is not int or maximum < 0:
        raise ValueError("maximum must be a nonnegative integer")
    return 0 if budget == 0 else min(maximum, math.ceil(budget * maximum))


@dataclass(frozen=True)
class Age0Policy:
    """Only structural-demo scalar readouts are writable, never real body weights."""

    trainable_paths: Tuple[str, ...] = (
        "demo.gist.readout", "demo.detail.readout", "demo.callosum.readout",
    )
    learning_rate: float = 0.001
    max_abs_update: float = 0.01
    max_updates_per_call: int = 8
    max_internal_rounds: int = 1
    age: int = 0

    def __post_init__(self) -> None:
        if self.age != 0 or self.max_internal_rounds != 1:
            raise ValueError("this package implements the fixed Age-0 envelope only")
        if not isinstance(self.trainable_paths, tuple) or not self.trainable_paths:
            raise ValueError("trainable_paths must be a fixed nonempty tuple")
        if len(set(self.trainable_paths)) != len(self.trainable_paths):
            raise ValueError("trainable_paths must be unique")
        if any(not isinstance(path, str) or not path.startswith("demo.")
               for path in self.trainable_paths):
            raise ValueError("only explicit demo paths are available")
        if not 0 < finite(self.learning_rate, "learning_rate") <= 0.01:
            raise ValueError("Age-0 learning_rate must be in (0, 0.01]")
        if not 0 < finite(self.max_abs_update, "max_abs_update") <= 0.01:
            raise ValueError("Age-0 max_abs_update must be in (0, 0.01]")
        budget_steps(1.0, self.max_updates_per_call)

    def promote(self) -> None:
        raise RuntimeError("Age promotion is unavailable: competence/stability gates are unimplemented")
