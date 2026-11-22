"""Actual compiled poll policy tests; synthetic math is not native model proof."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from v13.common import APP


class NativeNormPollPolicyTests(unittest.TestCase):
    def test_compiled_bounded_symmetric_policy_and_strict_refusal(self):
        compiler = shutil.which('g++') or shutil.which('clang++')
        if not compiler:
            self.skipTest('C++ compiler unavailable; no native policy execution claimed')
        source = r'''
#include "native_norm_poll_policy.hpp"
#include <cassert>
#include <limits>
int main(){
 using namespace v13_norm_poll;
 std::vector<float> master(1024,1.f), gradient(1024,0.f); gradient[0]=1.f;
 auto trials=candidates(master,gradient), repeated=candidates(master,gradient);
 assert(trials.size()==20 && repeated.size()==20);
 double best=0.; int evaluated=0,improved=0;
 for(size_t i=0;i<trials.size();++i){
  auto & trial=trials[i]; assert(trial.values==repeated[i].values);
  assert(trial.update_l2>0. && trial.update_l2<=cap);
  assert(trial.sign==-1||trial.sign==1);
  // Authored staircase objective: surrogate descent is wrong; forward polling
  // can evaluate both signs without asserting a differentiable quantizer.
  double delta=double(trial.values[0])-master[0];
  double loss=-std::floor(delta/.0002)*.01;
  if(improves(0.,loss,trial.update_l2)){++improved;best=std::min(best,loss);}
  ++evaluated;
 }
 assert(evaluated==20 && improved>0 && best<0.);
 assert(trials[0].sign==-1 && double(trials[0].values[0])-master[0]<0.);
 assert(!improves(0.,0.,.001)); assert(!improves(0.,1.,.001));
 assert(!improves(0.,-1.,.002)); assert(!improves(0.,-1.,0.));
 assert(!improves(0.,std::numeric_limits<double>::quiet_NaN(),.001));
 gradient[0]=std::numeric_limits<float>::infinity();
 bool refused=false;try{candidates(master,gradient);}catch(const std::invalid_argument&){refused=true;}assert(refused);
 gradient.assign(1024,0.f);assert(candidates(master,gradient).size()==16);
 refused=false;try{candidates(std::vector<float>(1,0.f),gradient);}catch(const std::invalid_argument&){refused=true;}assert(refused);
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder); (path / 'test.cpp').write_text(source)
            built = subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                '-I', str(APP / 'docs/proofs'), str(path / 'test.cpp'), '-o', str(path / 'test')],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            measured = subprocess.run([str(path / 'test')], capture_output=True, text=True, timeout=10)
            self.assertEqual(measured.returncode, 0, measured.stderr)
