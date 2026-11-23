"""A scalar SGD fixture to test locality; this is NOT JEPA or an LLM learner."""

from dataclasses import dataclass
from typing import Callable, Mapping, Tuple

from .contracts import finite
from .eligibility import Eligibility
from .policy import Age0Policy, budget_steps
from .scheduler import Coordinator
from .storage import Repository, ValidationReport


@dataclass(frozen=True)
class StepResult:
    status: str
    updated_paths: Tuple[str, ...] = ()
    snapshot_id: int = 0


class ScalarDemoLearner:
    def __init__(self, repository: Repository, eligibility: Eligibility,
                 coordinator: Coordinator, policy: Age0Policy = Age0Policy()):
        self.repository = repository
        self.eligibility = eligibility
        self.coordinator = coordinator
        self.policy = policy

    def step(self, experience_id: str, local_gradients: Mapping[str, float],
             modulation: float, compute_budget: float) -> StepResult:
        limit = budget_steps(compute_budget, self.policy.max_updates_per_call)
        mod = finite(modulation, "modulation")
        if not 0 <= mod <= 1:
            raise ValueError("demo modulation must be in [0, 1]")
        gradients = {path: finite(value, "local gradient") for path, value in local_gradients.items()}
        if limit == 0:
            return StepResult("budget_zero")
        if mod == 0:
            return StepResult("modulation_zero")
        result = StepResult("inference_priority")

        def operation(cancel: Callable[[], bool]) -> None:
            nonlocal result
            experience = self.repository.experience(experience_id)
            base = self.repository.current()
            if experience.model_version != base.model_version:
                result = StepResult("stale_experience_model", snapshot_id=base.id)
                return
            candidate = dict(base.weights)
            traces = []
            for path in sorted(gradients):
                if cancel():
                    result = StepResult("yielded_to_inference", snapshot_id=base.id)
                    return
                if path not in self.policy.trainable_paths or path not in candidate:
                    continue
                trace = self.eligibility.get(path, experience_id, base.model_version, base.id)
                if trace is None:
                    continue
                delta = -self.policy.learning_rate * self.eligibility.strength(trace) * mod * gradients[path]
                delta = max(-self.policy.max_abs_update, min(self.policy.max_abs_update, delta))
                if delta == 0:
                    continue
                candidate[path] += delta
                traces.append(trace)
                if len(traces) >= limit:
                    break
            if not traces:
                result = StepResult("no_eligible_update", snapshot_id=base.id)
                return
            if cancel():
                result = StepResult("yielded_to_inference", snapshot_id=base.id)
                return

            def validate(values: Mapping[str, float], old: object) -> ValidationReport:
                changed = {path for path in candidate if candidate[path] != base.weights[path]}
                selected = {trace.path for trace in traces}
                passed = (
                    changed == selected and set(values) == set(base.weights)
                    and all(abs(values[path] - base.weights[path]) <= self.policy.max_abs_update + 1e-12
                            for path in changed)
                    and not cancel()
                )
                return ValidationReport(passed, "scalar-demo-locality-v1", (
                    "only selected eligible demo paths changed", "bounded finite scalar updates",
                    "inference request checked before publication",
                ))

            # This tiny transaction is a non-preemptible final part of the slice.
            # A request arriving after the last check waits until it completes.
            from .storage import ValidationFailed
            try:
                committed = self.repository.commit(candidate, base.id, base.model_version, validate)
            except ValidationFailed:
                if cancel():
                    result = StepResult("yielded_to_inference", snapshot_id=base.id)
                    return
                raise
            for trace in traces:
                self.eligibility.consume(trace)
            result = StepResult("committed", tuple(trace.path for trace in traces), committed.id)

        self.coordinator.training_slice(operation)
        return result
