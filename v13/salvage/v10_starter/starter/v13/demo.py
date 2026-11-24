"""Run a model-free scalar test fixture in a temporary database."""
import json
from pathlib import Path
import tempfile
from .contracts import Origin
from .storage import Repository
from .eligibility import Eligibility
from .scheduler import Coordinator
from .demo_learning import ScalarDemoLearner

def main():
    with tempfile.TemporaryDirectory(prefix='v13-demo-') as directory:
        with Repository(str(Path(directory)/'demo.sqlite')) as repo:
            base = repo.initialize({'demo.gist.readout': 1., 'demo.detail.readout': 2.,
                                    'demo.callosum.readout': 3.}, 'scalar-fixture-v1')
            event = repo.append_experience(Origin.SYNTHETIC, 'demo:generated-fixture',
                                           {'x': 1., 'target': 0.}, base.model_version)
            traces = Eligibility()
            traces.activate('demo.gist.readout', event.id, base.model_version, base.id)
            repo.cache_put('demo:derived', {'placeholder': 'not a KV cache'})
            learner = ScalarDemoLearner(repo, traces, Coordinator())
            before = dict(base.weights)
            # d/dw 0.5*(w*x-target)^2 at x=1, target=0 is w.
            result = learner.step(event.id, {'demo.gist.readout': 1.,
                                             'demo.detail.readout': 2.}, 1., .1)
            after = dict(repo.current().weights)
            output = {'kind': 'MODELFREIE STRUKTURDEMO - kein LLM, kein JEPA',
                      'result': result.status, 'before': before, 'after': after,
                      'inactive_detail_unchanged': before['demo.detail.readout']==after['demo.detail.readout'],
                      'cache_invalidated': repo.cache_get('demo:derived') is None,
                      'observed_evidence_count': len(repo.observed_evidence()),
                      'temporary_database_deleted_after_demo': True}
            print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()

