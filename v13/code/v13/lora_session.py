"""WP-BP8 real-learning harness: a LoRA body session that learns in small windows and reports a competence plus an independent noise signal.

`LoraTrainer.fit` is one monolithic job (reload, train to a target loss, export). Age/plasticity control needs the opposite: many tiny windows on one
resident body, the step size set per window by `AgeControl.plasticity`, and a cheap measurement after each window. This session keeps model, adapter and
optimizer in memory; `step(items, lr_scale)` is one accumulated pass with the KL-to-base anchors; `competence(probes)` is a teacher-forced token accuracy
on the probe answers, split into two independent halves whose disagreement is the independent noise signal (`age.record(metrics['noise_signal'])`).
No export, no authority. Torch/peft are imported lazily.
"""
from pathlib import Path
from .lora_trainer import LoraTrainer, DEFAULTS

def split_halves(n):
    """Even/odd index split of n probes: two interleaved halves, so each covers all question kinds."""
    return list(range(0, n, 2)), list(range(1, n, 2))

def combine(acc):
    """acc: per-probe accuracies. Returns (competence, noise_signal = |half A - half B| / 2)."""
    a, b = split_halves(len(acc))
    ma = sum(acc[i] for i in a) / max(len(a), 1); mb = sum(acc[i] for i in b) / max(len(b), 1)
    return (ma + mb) / 2, abs(ma - mb) / 2

class LoraSession:
    def __init__(self, master, work, anchors=(), cfg=None, optimizer='adamw', momentum=0.9):
        self.tr = LoraTrainer(master, work, anchors=list(anchors), cfg=dict(DEFAULTS, **(cfg or {})))
        self.torch, self.tok, model = self.tr._load()
        cfg = self.tr.cfg; torch = self.torch
        self.anchor_seqs = []
        for a in self.tr.anchors:
            pid, _ = self.tr._encode(self.tok, a); self.anchor_seqs.append(pid + self.tr._greedy(torch, model, pid, 24))
        with torch.no_grad():
            self.anchor_logp = [torch.log_softmax(model(torch.tensor([s])).logits[0].float(), -1) for s in self.anchor_seqs]
        from peft import LoraConfig, get_peft_model
        lc = LoraConfig(r=int(cfg['rank']), lora_alpha=float(cfg['alpha']), lora_dropout=0., target_modules=list(cfg['targets']), bias='none')
        self.model = get_peft_model(model, lc)
        self.params = [p for p in self.model.parameters() if p.requires_grad]
        self.base_lr = float(cfg['lr'])
        if optimizer == 'sgd':  # WP-BP9b: plain SGD keeps the step proportional to the (weighted) gradient; Adam rescales a tiny gradient back up
            self.opt = torch.optim.SGD(self.params, lr=self.base_lr, momentum=float(momentum))
        else:
            self.opt = torch.optim.AdamW(self.params, lr=self.base_lr, weight_decay=float(cfg['weight_decay']))
        self.gen = torch.Generator().manual_seed(int(cfg['seed'])); self.steps = 0
        self.model.train()

    def step(self, items, lr_scale=1.0):
        torch, cfg = self.torch, self.tr.cfg
        for g in self.opt.param_groups: g['lr'] = self.base_lr * float(lr_scale)
        data = [self.tr._encode(self.tok, i['prompt'], i['target']) for i in items]
        self.opt.zero_grad(); ce = 0.
        for k in torch.randperm(len(data), generator=self.gen).tolist():
            ids, lab = data[k]; o = self.model(torch.tensor([ids]), labels=torch.tensor([lab]))
            (o.loss * float(items[k].get('weight', 1.)) / len(data)).backward(); ce += float(o.loss.detach())
        if self.anchor_seqs and float(cfg['anchor_weight']) > 0:
            pick = torch.randperm(len(self.anchor_seqs), generator=self.gen).tolist()[:int(cfg['anchors_per_step'])]
            for j in pick:
                cl = torch.log_softmax(self.model(torch.tensor([self.anchor_seqs[j]])).logits[0].float(), -1); bl = self.anchor_logp[j]
                (float(cfg['anchor_weight']) * (bl.exp() * (bl - cl)).sum(-1).mean() / len(pick)).backward()
        self.opt.step(); self.steps += 1
        return {'ce': ce / len(data), 'lr_scale': float(lr_scale)}

    def probe_accuracies(self, probes):
        """probes: list of (prompt, target). Teacher-forced token accuracy of the target given the prompt, per probe."""
        torch = self.torch; out = []; self.model.eval()
        with torch.no_grad():
            for q, t in probes:
                ids, lab = self.tr._encode(self.tok, q, t)
                logits = self.model(torch.tensor([ids])).logits[0]
                pos = [j for j, v in enumerate(lab) if v != -100 and j > 0]
                out.append(sum(int(logits[j - 1].argmax()) == lab[j] for j in pos) / max(len(pos), 1))
        self.model.train(); return out

    def competence(self, probes):
        return combine(self.probe_accuracies(probes))
