#!/usr/bin/env python3
# V13_FIX1: patcht V13_RUN_FIXED.py sauber und prueft Syntax.
import pathlib
import py_compile

P = pathlib.Path.home() / "v13" / "V13_RUN_FIXED.py"
ALTS = [
    (
        "        inv, var, cov = vicreg_loss(pf, tf)",
        "        vic_tot, inv, var, cov = vicreg_loss(pf, tf)",
    ),
]
MAIN = '''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-wire-fast", action="store_true")
    a = ap.parse_args()
    try:
        torch.set_num_threads(3)
    except Exception:
        pass
    print("V13 RUN | torch %s" % torch.__version__, flush=True)
    if a.test_wire_fast:
        test_wire_fast()
        return
    repl()


if __name__ == "__main__":
    main()
'''

if not P.exists():
    raise SystemExit("FEHLT: " + str(P))

t = P.read_text(encoding="utf-8")
n = []
for alt, neu in ALTS:
    if neu not in t and alt in t:
        t = t.replace(alt, neu, 1)
        n.append("vicreg-unpack")

if 'if __name__ == "__main__":' not in t:
    t = t.rstrip("\n") + "\n" + MAIN
    n.append("main")

bak = P.with_suffix(".py.bak")
bak.write_text(P.read_text(encoding="utf-8"), encoding="utf-8")
P.write_text(t, encoding="utf-8")

try:
    py_compile.compile(str(P), doraise=True)
    print("SYNTAX-OK   fixes=%s   backup=%s" % (n or ["keine noetig"], bak.name))
except Exception as e:
    P.write_text(bak.read_text(encoding="utf-8"), encoding="utf-8")
    raise SystemExit("SYNTAX-FEHLER, zurueckgerollt: " + str(e))