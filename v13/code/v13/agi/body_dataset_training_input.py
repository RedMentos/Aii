"""Prepare hash-verified, role-isolated examples for existing BodyJepaTrainer.fit.

No fit() invocation, human approval assertion, or active-weight mutation.
"""
import hashlib
import json
from .body_dataset_reader import load_role_dataset

def prepare_body_training_items(directory, role, *, max_items=256):
    """Return (train_items, heldout_items) with stable content-derived memory IDs.

    The caller MUST authenticate training approval independently and pass
    the existing AG6/age/retention checks before invoking a real trainer.
    """
    if type(max_items) is not int or not 1 <= max_items <= 256:
        raise ValueError("invalid mobile item cap")
    train, heldout = load_role_dataset(directory, role)
    if len(train) > max_items or len(heldout) > max_items:
        raise ValueError("dataset exceeds explicit mobile item cap")
    def convert(rows):
        result = []
        for row in rows:
            identity = [row["role"], row["source_id"], row["source_sha256"],
                        row["prompt"], row["target"]]
            digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False,
                        separators=(",", ":")).encode("utf-8")).hexdigest()
            result.append({"memory_id": "reviewed-"+digest, "prompt": row["prompt"],
                           "target": row["target"]})
        return tuple(result)
    return convert(train), convert(heldout)
