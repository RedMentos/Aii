"""A2→A3→A5 synthetic integration boundary; no Android or semantic authority.

The caller supplies an independent verifier for the immutable teacher source.
This module never treats a model-generated 'trusted' flag as sufficient.
"""
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Callable

from .a3_online_projector import A3Projector


@dataclass(frozen=True)
class TeacherEvidence:
    source_id: str
    teacher_version: str
    feature_vector: tuple
    target_vector: tuple
    final: bool
    consent_scope: str
    content_sha256: str

    def canonical_bytes(self):
        payload = {
            "source_id": self.source_id,
            "teacher_version": self.teacher_version,
            "feature_vector": list(self.feature_vector),
            "target_vector": list(self.target_vector),
            "final": self.final,
            "consent_scope": self.consent_scope,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

    def digest_matches(self):
        return isinstance(self.content_sha256, str) and len(self.content_sha256) == 64 and (
            hashlib.sha256(self.canonical_bytes()).hexdigest() == self.content_sha256
        )


class A3EvidenceBridge:
    """Trusted-source gate is injected from outside the trainable model.

    verify_source(evidence) must consult a source registry and revocation state.
    This is an interface, not a cryptographic attestation or Android permission.
    """

    def __init__(self, projector: A3Projector, verify_source: Callable):
        if not isinstance(projector, A3Projector) or not callable(verify_source):
            raise TypeError("projector and external verifier required")
        self.projector = projector
        self.verify_source = verify_source

    def _validate(self, evidence):
        if not isinstance(evidence, TeacherEvidence):
            raise TypeError("TeacherEvidence required")
        if not evidence.source_id or not evidence.teacher_version:
            raise ValueError("source and version required")
        self.projector._vector(evidence.feature_vector, self.projector.inputs)
        self.projector._vector(evidence.target_vector, self.projector.outputs)
        if not evidence.digest_matches():
            raise ValueError("teacher evidence digest mismatch")

    def learn(self, evidence):
        self._validate(evidence)
        if evidence.final is not True or evidence.consent_scope != "a3_train":
            raise PermissionError("only final explicitly training-approved evidence")
        if self.verify_source(evidence) is not True:
            raise PermissionError("source not independently verified")
        return self.projector.train(evidence.feature_vector, evidence.target_vector, trusted=True)

    def percept(self, evidence):
        self._validate(evidence)
        if evidence.final is not True or self.verify_source(evidence) is not True:
            raise PermissionError("unverified or provisional percept")
        embedding = self.projector.predict(evidence.feature_vector)
        if not all(math.isfinite(v) for v in embedding):
            raise ValueError("nonfinite A3 embedding")
        return {
            "schema": "v13.a5.a3.synthetic.v1",
            "modality": "synthetic_teacher_features",
            "source_id": evidence.source_id,
            "teacher_version": evidence.teacher_version,
            "evidence_sha256": evidence.content_sha256,
            "a3_embedding": embedding,
            "a3_training_steps": self.projector.steps,
            "authority": "observation_only",
            "android_action_allowed": False,
            "provisional": False,
        }
