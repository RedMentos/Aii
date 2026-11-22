"""V14 bounded trained receiver for cross-organ numeric packets.

This is a *separate* experimental receiver utility proof. It does not inject
vectors into GGUF hidden states or grant Android/tool/learning authority.
"""
from __future__ import annotations
import hashlib
import json
import math
from .latent_bridge import Projector, receive, vec

SCHEMA = "v14.latent-receiver-utility/1"

class Receiver:
    def __init__(self, target, width, rate=0.05):
        if not target or not isinstance(width, int) or not 1 <= width <= 256:
            raise ValueError("receiver geometry")
        if not 0 < rate <= 0.1:
            raise ValueError("receiver rate")
        self.target, self.width, self.rate = target, width, rate
        self.weights = [0.0] * width
        self.bias = 0.0
        self.steps = 0

    def score(self, values):
        values = vec(values, self.width)
        z = self.bias + sum(w * x for w, x in zip(self.weights, values))
        return 1.0 / (1.0 + math.exp(-max(-40., min(40., z))))

    def learn(self, values, label, *, admitted=False, committed=False):
        if not admitted or not committed:
            raise PermissionError("explicit admitted committed training only")
        if type(label) not in (int, float) or label not in (0, 1):
            raise ValueError("binary label required")
        values = vec(values, self.width)
        before = self.score(values)
        error = float(label) - before
        scale = self.rate / max(1.0, math.sqrt(sum(x*x for x in values)))
        self.weights = [w + scale*error*x for w,x in zip(self.weights, values)]
        self.bias += scale*error
        self.steps += 1
        return -(label*math.log(max(before, 1e-12)) +
                 (1-label)*math.log(max(1-before, 1e-12)))

    def checkpoint(self):
        payload = dict(schema=SCHEMA, target=self.target, width=self.width,
                       rate=self.rate, weights=self.weights, bias=self.bias,
                       steps=self.steps)
        payload["sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        return payload

    @classmethod
    def restore(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("checkpoint type")
        copy = dict(payload)
        sha = copy.pop("sha256", None)
        if hashlib.sha256(json.dumps(copy, sort_keys=True, allow_nan=False).encode()).hexdigest() != sha:
            raise ValueError("checkpoint integrity")
        if copy.get("schema") != SCHEMA:
            raise ValueError("schema")
        receiver = cls(copy["target"], copy["width"], copy["rate"])
        receiver.weights = vec(copy["weights"], receiver.width)
        receiver.bias = vec([copy["bias"]], 1)[0]
        if type(copy["steps"]) is not int or copy["steps"] < 0:
            raise ValueError("steps")
        receiver.steps = copy["steps"]
        return receiver


def evaluate(projector, receiver, examples, *, generation, source_ids):
    """Holdout-only, source/generation/revision-checked receiver evaluation.

    Each example is (source_vector, source_id, binary_label). The caller must
    provide non-overlapping training and holdout source IDs; this function does
    not train or decide whether the data are consented.
    """
    if projector.target != receiver.target or projector.no != receiver.width:
        raise ValueError("incompatible ports")
    rows = list(examples)
    if not rows:
        raise ValueError("empty holdout")
    losses, correct = [], 0
    for x, source_id, label in rows:
        if type(label) not in (int, float) or label not in (0, 1):
            raise ValueError("label")
        packet = projector.project(x, source_id, generation)
        values = receive(packet, receiver.target, generation, source_ids,
                         projector.revision())
        probability = receiver.score(values)
        losses.append(-(label*math.log(max(probability, 1e-12)) +
                        (1-label)*math.log(max(1-probability, 1e-12))))
        correct += (probability >= 0.5) == bool(label)
    return dict(n=len(rows), accuracy=correct/len(rows),
                logloss=sum(losses)/len(rows), receiver_steps=receiver.steps,
                projector_steps=projector.steps, evidence="SYNTHETIC_ONLY")
