#!/usr/bin/env python3
"""Test-only observation hooks around the unchanged NumPy training worker.

The parent kills this disposable process only after a durable phase marker.
No hook is installed in the production worker or normal learning path.
"""
import argparse
import ast
import inspect
import json
import os
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))


def objective_lines(function):
    """Locate actual forward/backward statements, refusing a changed objective."""
    source, first = inspect.getsourcelines(function)
    tree = ast.parse(''.join(source))
    found = {}
    for node in tree.body[0].body:
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if 'logits' in names:
            found['forward'] = first + node.lineno - 1
        if 'd' in names:
            found['backward'] = first + node.lineno - 1
    if set(found) != {'forward', 'backward'}:
        raise ValueError('Unrecognized objective; phase observation unavailable')
    return found


def main(argv=None):
    from v13 import learning_worker as worker
    from v13.common import atomic_write, file_hash
    ap = argparse.ArgumentParser()
    ap.add_argument('request', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('phase', choices=('forward', 'backward', 'checkpoint'))
    a = ap.parse_args(argv)
    a.output.mkdir(parents=True, exist_ok=True)

    def reached(location):
        atomic_write(a.output/'phase_reached.json', json.dumps({
            'phase': a.phase, 'location': location,
            'worker_sha256': file_hash(APP/'v13/learning_worker.py'),
        }))
        # The parent owns this child and will SIGKILL it. EOF is an error,
        # never permission to continue past an unobserved interruption point.
        sys.stdin.buffer.read(1)
        raise RuntimeError('Phase probe released without parent kill')

    if a.phase == 'checkpoint':
        original = worker.np.savez

        class PartialCheckpoint:
            def __init__(self, stream):
                self.stream = stream

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def write(self, data):
                result = self.stream.write(data)
                if data:
                    self.stream.flush()
                    os.fsync(self.stream.fileno())
                    reached('candidate.npz: first nonempty write durably flushed')
                return result

        worker.np.savez = lambda stream, **values: original(PartialCheckpoint(stream), **values)
    else:
        target = objective_lines(worker.objective)[a.phase]

        def trace(frame, event, arg):
            if (event == 'line' and frame.f_code is worker.objective.__code__
                    and frame.f_lineno == target and frame.f_back is not None
                    and frame.f_back.f_code is worker.optimize.__code__):
                reached('learning_worker.objective line %d inside optimize' % target)
            return trace

        sys.settrace(trace)
    worker.train(json.loads(a.request.read_text()), str(a.output))
    raise RuntimeError('Requested phase not reached')


if __name__ == '__main__':
    main()
