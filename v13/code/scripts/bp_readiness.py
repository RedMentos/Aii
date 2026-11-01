#!/usr/bin/env python3
"""WP-BP12 Bereitschafts-Pruefung: Handy-Paket (WP-Z7) erst, wenn BP1..BP11 drin sind.

Liest docs/bp-bereitschaft/status.json (von Hand/Threads gepflegt, je Eintrag Beleg).
Gibt READY nur, wenn jeder Baustein 'drin' ist. Exit 0 = bereit, 1 = nicht bereit.
"""
import json, sys, pathlib

ALLOWED = {"drin", "teilweise", "offen", "gesperrt"}


def check(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    rows, missing = [], []
    for bp in data["bausteine"]:
        st = bp["stand"]
        if st not in ALLOWED:
            raise ValueError(f"{bp['id']}: unbekannter Stand {st!r}")
        if st == "drin" and not bp.get("beleg"):
            raise ValueError(f"{bp['id']}: 'drin' ohne Beleg")
        rows.append((bp["id"], st, bp["name"]))
        if st != "drin":
            missing.append(bp["id"])
    return rows, missing


def main(argv):
    p = argv[1] if len(argv) > 1 else str(
        pathlib.Path(__file__).resolve().parent.parent / "docs/bp-bereitschaft/status.json")
    rows, missing = check(p)
    for i, st, n in rows:
        print(f"{i:5s} {st:10s} {n}")
    if missing:
        print("NICHT BEREIT, es fehlen:", ", ".join(missing))
        return 1
    print("READY: alle Bausteine drin, Handy-Paket darf gebaut werden")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
