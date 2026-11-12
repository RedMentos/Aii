"""Feature-only A3 inference boundary for A5 and non-authoritative B/C observations.

Host synthetic contract, not canonical A5 or Android instrumentation. No teacher
targets are required at inference time. Source approval is external to this module.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Callable

from .a3_online_projector import A3Projector


@dataclass(frozen=True)
class FeatureObservation:
    source_id: str
    modality: str
    feature_vector: tuple
    final: bool
    feature_sha256: str

    def canonical_bytes(self):
        return json.dumps({
            "source_id": self.source_id, "modality": self.modality,
            "feature_vector": list(self.feature_vector), "final": self.final,
        }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

    def valid_digest(self):
        return (isinstance(self.feature_sha256, str)
                and len(self.feature_sha256) == 64
                and hashlib.sha256(self.canonical_bytes()).hexdigest() == self.feature_sha256)


class A3InferenceRuntime:
    """Independent verifier must check consent, source state, and revocation."""

    def __init__(self, projector: A3Projector, verify_source: Callable):
        if not isinstance(projector, A3Projector) or not callable(verify_source):
            raise TypeError("projector and independent source verifier required")
        self.projector = projector
        self.verify_source = verify_source

    def observe(self, observation: FeatureObservation):
        if not isinstance(observation, FeatureObservation):
            raise TypeError("FeatureObservation required")
        if not observation.source_id or observation.modality not in (
                "synthetic_audio", "synthetic_visual", "synthetic_ui"):
            raise ValueError("invalid source or unsupported modality")
        self.projector._vector(observation.feature_vector, self.projector.inputs)
        if not observation.valid_digest():
            raise ValueError("feature digest mismatch")
        if observation.final is not True or self.verify_source(observation) is not True:
            raise PermissionError("source is provisional, revoked or unapproved")
        embedding = self.projector.predict(observation.feature_vector)
        if not all(math.isfinite(x) for x in embedding):
            raise ValueError("nonfinite embedding")
        percept = {
            "schema": "v13.a5.a3.feature_only.synthetic.v1",
            "modality": observation.modality,
            "source_id": observation.source_id,
            "source_sha256": observation.feature_sha256,
            "a3_embedding": embedding,
            "a3_training_steps": self.projector.steps,
            "authority": "observation_only",
            "android_action_allowed": False,
            "provisional": False,
        }
        # A5 and organ views contain no teacher targets and no executable action.
        return {
            "a5": percept,
            "b1": {"source_id": observation.source_id, "embedding": embedding,
                   "authority": "observation_only"},
            "b2": {"source_id": observation.source_id,
                   "embedding_norm": math.sqrt(sum(x*x for x in embedding)),
                   "authority": "observation_only"},
            "jef": {"source_id": observation.source_id, "modality": observation.modality,
                    "observation_only": True, "android_action_allowed": False},
        }
