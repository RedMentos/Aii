"""WP-FS4 real predictor: tiny logistic regression (numpy) for "would the tool change my answer's correctness?".
Two feature views: state (runtime confidence features of the first pass) and input (question text only, the control)."""
import numpy as np

def fit(X,y,l2=1.,iters=400,lr=.5):
    X=np.asarray(X,float);y=np.asarray(y,float);mu=X.mean(0);sd=X.std(0)+1e-9;Z=(X-mu)/sd;w=np.zeros(Z.shape[1]);b=0.
    for _ in range(iters):
        p=1/(1+np.exp(-(Z@w+b)));g=p-y;w-=lr*(Z.T@g/len(y)+l2*w/len(y));b-=lr*g.mean()
    return {'w':w,'b':b,'mu':mu,'sd':sd}
def predict(m,x):
    z=((np.asarray(x,float)-m['mu'])/m['sd'])@m['w']+m['b'];return float(1/(1+np.exp(-z)))
def state_feats(f):
    return [f['mean_logprob'],f['min_logprob'],f['p10_logprob'],f['share_below_half'],f['digit_min_logprob'],f['tokens']]
def input_feats(text,nums):
    return [len(text),len(nums or []),sum(c.isdigit() for c in text),int('Summary line' in text or 'summary' in text.lower()),
            int('largest' in text.lower() or 'smallest' in text.lower())]
