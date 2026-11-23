"""CLI for explicitly labeled, non-promoted B3 L1 shadow training.

Example labels file:
{
  "schema": "v13.b3-l1-labels/1",
  "task_id": "verified-outcome",
  "label_source": "human_feedback",
  "direction": "B1_TO_B2",
  "seeds": [11, 17, 23],
  "labels": [
    {"body_pair_id": "…", "label": 1, "provenance": "feedback-packet-id"}
  ]
}

Run from v13/code:
  python scripts/b3_train_l1_shadow.py --labels data/b3/l1_labels.json

Supply at least 64 unique pair entries, one explicit label and provenance
reference per pair. Optional --l0-evidence accepts schema
v13.b3-l0-baselines/1, pinned to those exact pair IDs, source hashes, labels,
provenance, holdout indices and seeds, with EXACT/CONTROL/SYMBOLIC metrics.
This creates only shadow adapter artifacts. It never updates B1/B2 weights or
enables receiver injection; an L1 PASS only permits an L2 prefix shadow trial.
"""
import argparse
import json
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parents[1]
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from v13.runtime import Runtime
from v13.b3pairs import SCHEMA
from v13.b3train import train_l1_shadow
from v13.common import dumps


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default=str(Path.home() / "v13"))
    parser.add_argument("--labels", required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--head-steps", type=int, default=25)
    parser.add_argument("--l0-evidence", default=None)
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser().resolve()
    label_path = Path(args.labels).expanduser()
    if not label_path.is_absolute():
        label_path = home / label_path
    label_path = label_path.resolve()
    if not label_path.is_file():
        raise FileNotFoundError(f"L1 labels file not found: {label_path}")
    doc = json.loads(label_path.read_text(encoding="utf-8"))
    if (not isinstance(doc, dict) or doc.get("schema") != "v13.b3-l1-labels/1"
            or not isinstance(doc.get("labels"), list)):
        raise ValueError("labels file must use v13.b3-l1-labels/1 and contain a labels array")
    entries = doc["labels"]
    if not entries or any(not isinstance(x, dict) for x in entries):
        raise ValueError("labels array must contain label objects")
    pair_ids = [x.get("body_pair_id") for x in entries]
    if any(not isinstance(x, str) or not x for x in pair_ids) or len(set(pair_ids)) != len(pair_ids):
        raise ValueError("each label entry needs a unique body_pair_id")
    labels = [x.get("label") for x in entries]
    provenance = [x.get("provenance") for x in entries]

    l0_evidence = None
    if args.l0_evidence:
        evidence_path = Path(args.l0_evidence).expanduser()
        if not evidence_path.is_absolute():
            evidence_path = home / evidence_path
        evidence_path = evidence_path.resolve()
        if not evidence_path.is_file():
            raise FileNotFoundError(f"L0 evidence file not found: {evidence_path}")
        l0_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

    runtime = Runtime(home)
    try:
        rows = runtime.store.rows(
            "SELECT payload FROM packets WHERE kind='B3PairedTapPacket' ORDER BY rowid"
        )
        by_id = {}
        for row in rows:
            packet = json.loads(row["payload"])
            if packet.get("packet_schema") == SCHEMA:
                by_id.setdefault(packet.get("body_pair_id"), packet)
        missing = [pair_id for pair_id in pair_ids if pair_id not in by_id]
        if missing:
            raise ValueError(f"labels reference unknown paired experiences: {missing[:5]}")
        pairs = [by_id[pair_id] for pair_id in pair_ids]
        report = train_l1_shadow(
            runtime.cognition, pairs, labels, provenance,
            task_id=doc.get("task_id"), label_source=doc.get("label_source"),
            direction=doc.get("direction", "B1_TO_B2"),
            seeds=tuple(doc.get("seeds", [11, 17, 23])),
            epochs=args.epochs, head_steps=args.head_steps,
            l0_evidence=l0_evidence,
        )
        print(dumps(report))
        return 0
    finally:
        runtime.close()


if __name__ == "__main__":
    raise SystemExit(main())
