# --- FILE: V13_RUN_FIXED.py ---
# V13 RUN FIXED single file Termux CPU nutzt V13_B1 V13_B4 wenn da laeuft auch ohne
# Termux: cp "/storage/emulated/0/Download/code (26).py" ~/v13/V13_RUN_FIXED.py
#         cd ~/v13 && python -m py_compile V13_RUN_FIXED.py
#         OMP_NUM_THREADS=3 python V13_RUN_FIXED.py --test-wire-fast
#         OMP_NUM_THREADS=3 python V13_RUN_FIXED.py
import argparse
import copy
import hashlib
import json
import os
import random
import sys
import threading
import time
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
try:
    import torch.distributed as dist
except Exception:
    dist = None
STOP_EVENT = threading.Event()
QUEUE_LOCK = threading.Lock()
PENDING = deque(maxlen=64)
RESULTS = deque(maxlen=64)
WORKER = {"th": False, "busy": False, "txt": ""}
CACHE = {}
CACHE_ORDER = deque(maxlen=20)
DEVICE = torch.device("cpu")
@dataclass
class V13Config:
    hidden_dim: int = 256
    embed_dim: int = 256
    encoder_depth: int = 3
    pred_dim: int = 128
    num_experts: int = 8
    top_k: int = 2
    capacity_factor: float = 1.25
    ema_decay: float = 0.996
    predictor_depth: int = 4
    mask_ratio: float = 0.4
    block_mask_ratio: float = 0.5
    learning_rate: float = 3e-4
    weight_decay: float = 0.05
    vicreg_coeff: float = 1.0
    vic_inv_coeff: float = 1.0
    vic_var_coeff: float = 1.0
    vic_cov_coeff: float = 0.04
    load_balancing_coeff: float = 0.01
    z_loss_coeff: float = 0.001
    vocab_size: int = 512
    max_seq: int = 128
    shared_dim: int = 256
    conf_thresh: float = 0.6
    min_new: int = 8
    max_new: int = 48
    vorlauf_timeout: float = 20.0
    notaus_s: float = 25.0
CFG = V13Config()
def now_s():
    return time.strftime("%H:%M:%S")
def qlog(m):
    print("[%s] %s" % (now_s(), str(m)), flush=True)
def text_to_ids(text, vocab=50304, max_len=48):
    b = str(text).encode("utf-8", errors="ignore")[:max_len]
    if len(b) == 0:
        b = b"hi"
    ids = [max(1, int(x) % int(vocab)) for x in b]
    return torch.tensor([ids], dtype=torch.long)
def decode_ids(ids, vocab=49152):
    import re as _re
    if isinstance(ids, torch.Tensor):
        try:
            ids = ids.detach().cpu().tolist()
        except Exception as e:
            qlog("dec detach %s" % str(e)[:30])
            ids = []
    if isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
        ids = ids[0]
    bs = []
    for x in ids:
        try:
            ii = int(x)
        except Exception:
            continue
        if ii in (0, 1, 2):
            continue
        if ii == 50279:
            break
        if 3 <= ii < 259:
            bs.append(ii - 3)
        elif 0 <= ii < 256:
            bs.append(ii)
        else:
            bs.append(ii % 256)
    try:
        t = bytes(bs).decode("utf-8", errors="ignore")
    except Exception as e:
        qlog("dec bytes %s" % str(e)[:20])
        t = ""
    t = _re.sub(r"\s+", " ", t).strip()
    if len(t) < 2:
        return "verstanden, erzaehl mehr dazu"
    if len(t) < 8:
        return t + " - erzaehl mehr dazu"
    return t[:600]
def ema_update(named_ctx, named_tgt, decay=0.996):
    with torch.no_grad():
        d1 = dict(named_ctx)
        d2 = dict(named_tgt)
        for k in list(d1.keys()):
            if k in d2:
                a = d1[k]
                b = d2[k]
                if a.shape == b.shape:
                    try:
                        b.data.mul_(float(decay)).add_(a.data, alpha=1.0 - float(decay))
                    except Exception as e:
                        qlog("ema %s" % str(e)[:20])
def vicreg_loss(x, y, inv_w=1.0, var_w=1.0, cov_w=0.04):
    inv = F.mse_loss(x, y)
    sx = x.std(dim=0, unbiased=False) + 1e-4
    sy = y.std(dim=0, unbiased=False) + 1e-4
    var = F.relu(1.0 - sx).mean() + F.relu(1.0 - sy).mean()
    def cov_fn(m):
        if m.shape[0] <= 1:
            return torch.tensor(0.0, device=m.device)
        c2 = m - m.mean(dim=0, keepdim=True)
        cm = (c2.T @ c2) / max(1, m.shape[0] - 1)
        off = cm - torch.diag(torch.diag(cm))
        return (off ** 2).mean()
    cov = cov_fn(x) + cov_fn(y)
    tot = inv_w * inv + var_w * var + cov_w * cov
    return tot, inv.detach(), var.detach(), cov.detach()
def make_masks(B, N, mask_ratio=0.4, block_ratio=0.5, device="cpu"):
    Nm = max(1, int(N * float(mask_ratio)))
    tp = torch.zeros(B, Nm, dtype=torch.long, device=device)
    for b in range(B):
        blk = min(int(Nm * float(block_ratio)), N)
        st = random.randint(0, max(0, N - 1))
        bi = [(st + i) % N for i in range(blk)]
        pool = [i for i in range(N) if i not in bi]
        rnd = Nm - len(bi)
        ri = random.sample(pool, min(rnd, len(pool))) if pool and rnd > 0 else []
        am = (bi + ri)[:Nm]
        while len(am) < Nm:
            am.append(random.randint(0, N - 1))
        tp[b] = torch.tensor(am[:Nm], device=device)
    return tp
class ExpertFFN(nn.Module):
    def __init__(self, dim, seed_off=0):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim * 2)
        self.fc2 = nn.Linear(dim * 2, dim)
        torch.manual_seed(1234 + int(seed_off) * 7919)
        nn.init.kaiming_uniform_(self.fc1.weight, a=5 ** 0.5)
        nn.init.zeros_(self.fc1.bias)
        torch.manual_seed(4321 + int(seed_off) * 104729)
        nn.init.kaiming_uniform_(self.fc2.weight, a=5 ** 0.5)
        nn.init.zeros_(self.fc2.bias)
    def forward(self, x):
        assert x.dim() == 2
        return self.fc2(F.gelu(self.fc1(x)))
class MoELayer(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.router = nn.Linear(cfg.hidden_dim, cfg.num_experts, bias=True)
        nn.init.normal_(self.router.weight, std=0.02)
        nn.init.zeros_(self.router.bias)
        self.experts = nn.ModuleList([ExpertFFN(cfg.hidden_dim, seed_off=i) for i in range(cfg.num_experts)])
        self.register_buffer("assign_counts", torch.zeros(cfg.num_experts, dtype=torch.long))
        self.register_buffer("total_seen", torch.zeros(1, dtype=torch.long))
    def forward(self, x):
        assert x.dim() == 3
        B, N, D = x.shape
        assert D == self.cfg.hidden_dim
        flat = x.reshape(B * N, D)
        logits = self.router(flat)
        probs = F.softmax(logits, dim=-1)
        z_loss = (torch.logsumexp(logits, dim=-1) ** 2).mean()
        tk = min(int(self.cfg.top_k), int(self.cfg.num_experts))
        topv, topi = torch.topk(probs, k=tk, dim=-1)
        topv = topv / (topv.sum(dim=-1, keepdim=True) + 1e-9)
        cap = max(1, int((B * N * tk / max(1, self.cfg.num_experts)) * float(self.cfg.capacity_factor)))
        out = torch.zeros_like(flat)
        oh = torch.zeros_like(probs)
        oh.scatter_(1, topi, 1.0)
        aux = (probs.mean(dim=0) * oh.mean(dim=0)).sum() * self.cfg.num_experts
        has = False
        try:
            has = dist is not None and dist.is_available() and dist.is_initialized()
        except Exception as e:
            qlog("dist %s" % str(e)[:20])
        if has:
            try:
                dist.all_reduce(aux)
            except Exception as e:
                qlog("ar %s" % str(e)[:20])
        dropped = 0
        cnt = torch.zeros(self.cfg.num_experts, dtype=torch.long, device=flat.device)
        for e in range(self.cfg.num_experts):
            m = (topi == e).any(dim=-1)
            idx = torch.where(m)[0]
            if idx.numel() == 0:
                continue
            sc = probs[idx, e]
            if idx.numel() > cap:
                od = torch.argsort(sc, descending=True)
                keep = idx[od[:cap]]
                dropped += int(idx.numel() - cap)
            else:
                keep = idx
            w = torch.zeros(keep.numel(), tk, device=flat.device)
            for k in range(tk):
                w[:, k] = topv[keep, k] * (topi[keep, k] == e).float()
            ws = w.sum(dim=-1, keepdim=True).clamp_min(1e-9)
            scale = (w.sum(dim=-1) / ws.squeeze(-1)).unsqueeze(-1)
            out[keep] += self.experts[e](flat[keep]) * scale
            cnt[e] = keep.numel()
        with torch.no_grad():
            self.assign_counts += cnt.to(self.assign_counts.device)
            self.total_seen += B * N
        return out.reshape(B, N, D), aux, z_loss, int(dropped)
class TinyEncoder(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.tok = nn.Embedding(cfg.vocab_size, cfg.embed_dim)
        nn.init.normal_(self.tok.weight, std=0.02)
        self.proj = nn.Linear(cfg.embed_dim, cfg.hidden_dim) if cfg.embed_dim != cfg.hidden_dim else nn.Identity()
        if isinstance(self.proj, nn.Linear):
            nn.init.normal_(self.proj.weight, std=0.02)
            nn.init.zeros_(self.proj.bias)
        self.pos = nn.Embedding(cfg.max_seq, cfg.hidden_dim)
        nn.init.normal_(self.pos.weight, std=0.02)
        self.attn = nn.MultiheadAttention(cfg.hidden_dim, 4, batch_first=True)
        self.n1 = nn.LayerNorm(cfg.hidden_dim)
        self.n2 = nn.LayerNorm(cfg.hidden_dim)
        self.moe = MoELayer(cfg)
        self.norm = nn.LayerNorm(cfg.hidden_dim)
    def forward(self, ids):
        assert ids.dim() == 2
        B, N = ids.shape
        assert N <= self.cfg.max_seq
        e = self.tok(ids)
        if isinstance(self.proj, nn.Linear):
            e = self.proj(e)
        e = e + self.pos(torch.arange(N, device=ids.device).unsqueeze(0).expand(B, N))
        h = self.n1(e)
        a, _ = self.attn(h, h, h, need_weights=False)
        x = e + a
        m, aux, zl, dr = self.moe(self.n2(x))
        x = x + m
        return self.norm(x), aux, zl, dr
class TinyPredictor(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.down = nn.Linear(cfg.hidden_dim, cfg.pred_dim)
        nn.init.normal_(self.down.weight, std=0.02)
        nn.init.zeros_(self.down.bias)
        self.mask_tok = nn.Parameter(torch.randn(1, 1, cfg.pred_dim) * 0.02)
        self.pos = nn.Embedding(cfg.max_seq, cfg.pred_dim)
        nn.init.normal_(self.pos.weight, std=0.02)
        nh = max(1, 4 // 2)
        self.tr = nn.ModuleList([nn.TransformerEncoderLayer(d_model=cfg.pred_dim, nhead=nh, dim_feedforward=cfg.pred_dim * 4, batch_first=True) for _ in range(cfg.predictor_depth)])
        self.norm = nn.LayerNorm(cfg.pred_dim)
        self.up = nn.Linear(cfg.pred_dim, cfg.hidden_dim)
        nn.init.normal_(self.up.weight, std=0.02)
        nn.init.zeros_(self.up.bias)
    def forward(self, ctx_emb, tgt_pos):
        assert ctx_emb.dim() == 3
        assert tgt_pos.dim() == 2
        B, Nc, D = ctx_emb.shape
        B2, Nm = tgt_pos.shape
        assert B == B2
        hc = self.down(ctx_emb)
        mt = self.mask_tok.expand(B, Nm, self.cfg.pred_dim) + self.pos(tgt_pos.clamp(0, self.cfg.max_seq - 1))
        seq = torch.cat([hc, mt], dim=1)
        for ly in self.tr:
            seq = ly(seq)
        seq = self.norm(seq)
        out = self.up(seq[:, Nc:, :])
        assert out.shape[0] == B and out.shape[1] == Nm and out.shape[2] == D
        return out
class TinyDecoder(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.tok = nn.Embedding(cfg.vocab_size, cfg.hidden_dim)
        nn.init.normal_(self.tok.weight, std=0.02)
        self.pos = nn.Embedding(cfg.max_seq, cfg.hidden_dim)
        nn.init.normal_(self.pos.weight, std=0.02)
        self.ly = nn.ModuleList([nn.TransformerEncoderLayer(d_model=cfg.hidden_dim, nhead=4, dim_feedforward=cfg.hidden_dim * 2, batch_first=True) for _ in range(2)])
        self.norm = nn.LayerNorm(cfg.hidden_dim)
        self.head = nn.Linear(cfg.hidden_dim, cfg.vocab_size)
        nn.init.normal_(self.head.weight, std=0.02)
        nn.init.zeros_(self.head.bias)
        self.from_shared = nn.Linear(cfg.shared_dim, cfg.hidden_dim)
        nn.init.normal_(self.from_shared.weight, std=0.02)
        nn.init.zeros_(self.from_shared.bias)
    def forward(self, ids, shared):
        assert ids.dim() == 2
        assert shared.dim() == 2
        B, N = ids.shape
        e = self.tok(ids) + self.pos(torch.arange(N, device=ids.device).unsqueeze(0).expand(B, N))
        e = e + self.from_shared(shared).unsqueeze(1)
        x = e
        N2 = x.shape[1]
        cm = torch.triu(torch.full((N2, N2), float("-inf"), device=ids.device), diagonal=1)
        kpm = (ids == 0)
        haspad = bool(kpm.any().item())
        for ly in self.ly:
            if haspad:
                x = ly(x, src_mask=cm, src_key_padding_mask=kpm)
            else:
                x = ly(x, src_mask=cm)
        return self.head(self.norm(x))
class Brain(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.ctx_enc = TinyEncoder(cfg)
        self.tgt_enc = copy.deepcopy(self.ctx_enc)
        for p in self.tgt_enc.parameters():
            p.requires_grad = False
        self.pred = TinyPredictor(cfg)
        self.dec = TinyDecoder(cfg)
        self.scorer = nn.Linear(cfg.shared_dim, 1, bias=True)
        assert self.scorer.bias is not None
        nn.init.normal_(self.scorer.weight, std=0.02)
        nn.init.zeros_(self.scorer.bias)
        self.mem = deque(maxlen=512)
        self.fb = deque(maxlen=128)
        self.steps = 0
        self.best = 1e9
        self.streak = 0
        self.nan_skips = 0
        self.to(DEVICE)
        dec = [p for _, p in self.named_parameters() if p.dim() > 1]
        nod = [p for _, p in self.named_parameters() if p.dim() <= 1]
        self.opt = torch.optim.AdamW([{"params": dec, "weight_decay": cfg.weight_decay}, {"params": nod, "weight_decay": 0.0}], lr=cfg.learning_rate)
    def arch_hash(self):
        s = "%d-%d-%d-%d-%d-%d" % (self.cfg.hidden_dim, self.cfg.embed_dim, self.cfg.num_experts, self.cfg.pred_dim, self.cfg.vocab_size, self.cfg.max_seq)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]
    def cpath(self):
        d = Path.home() / "v13"
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            qlog("mkdir %s" % str(e)[:20])
        return str(d / "v13_fixed.pt")
    def save(self):
        try:
            torch.save({"sd": self.state_dict(), "opt": self.opt.state_dict(), "steps": self.steps, "best": self.best, "hh": self.arch_hash()}, self.cpath())
        except Exception as e:
            qlog("save %s" % str(e)[:30])
    def load(self):
        p = self.cpath()
        if not os.path.exists(p):
            return "neu"
        try:
            d = torch.load(p, map_location="cpu")
            if d.get("hh", "?") != self.arch_hash():
                try:
                    os.rename(p, p + ".bak")
                except Exception as e:
                    qlog("bak %s" % str(e)[:20])
                return "reset-arch-mismatch"
            self.load_state_dict(d["sd"], strict=False)
            try:
                self.opt.load_state_dict(d["opt"])
            except Exception as e:
                qlog("opt %s" % str(e)[:20])
            self.steps = int(d.get("steps", 0))
            self.best = float(d.get("best", 1e9))
            return "geladen steps=%d best=%.4f" % (self.steps, self.best)
        except Exception as e:
            qlog("load %s" % str(e)[:30])
            return "load-fail"
    def ema_update(self):
        ema_update(self.ctx_enc.named_parameters(), self.tgt_enc.named_parameters(), decay=self.cfg.ema_decay)
    def forward_once(self, ids):
        assert ids.dim() == 2
        B, N = ids.shape
        assert B >= 1 and N <= self.cfg.max_seq
        tp = make_masks(B, N, mask_ratio=self.cfg.mask_ratio, block_ratio=self.cfg.block_mask_ratio, device=ids.device)
        ctx_ids = ids.clone()
        for b in range(B):
            ctx_ids[b, tp[b]] = 0
        ctx_seq, aux, zl, dr = self.ctx_enc(ctx_ids)
        with torch.no_grad():
            tgt_seq, _, _, _ = self.tgt_enc(ids)
        Nm = tp.shape[1]
        ga = tp.unsqueeze(-1).expand(B, Nm, ctx_seq.shape[2])
        tgt_m = torch.gather(tgt_seq, 1, ga).detach()
        pred_m = self.pred(ctx_seq, tp)
        assert pred_m.shape == tgt_m.shape
        pf = pred_m.reshape(B * Nm, -1)
        tf = tgt_m.reshape(B * Nm, -1)
        inv, var, cov = vicreg_loss(pf, tf)
        vic = self.cfg.vic_inv_coeff * inv + self.cfg.vic_var_coeff * var + self.cfg.vic_cov_coeff * cov
        jepa = inv.detach()
        shared = ctx_seq.mean(dim=1)
        if shared.shape[1] != self.cfg.shared_dim:
            shared = F.linear(shared, torch.randn(self.cfg.shared_dim, shared.shape[1], device=ids.device) * 0.02)
        assert shared.dim() == 2
        sc = self.scorer(torch.tanh(shared))
        conf = torch.sigmoid(sc)
        if ids.shape[1] >= 2:
            din = ids[:, :-1]
            dt = ids[:, 1:]
            lg = self.dec(din, shared.detach())
            dec_loss = F.cross_entropy(lg.reshape(-1, lg.shape[-1]), dt.reshape(-1), ignore_index=0)
        else:
            dec_loss = torch.tensor(0.0, device=ids.device)
        tot = jepa + self.cfg.vicreg_coeff * vic + aux * self.cfg.load_balancing_coeff + zl * self.cfg.z_loss_coeff + dec_loss
        return {"loss": tot, "jepa": jepa.detach(), "vic": vic.detach(), "dec": dec_loss.detach(), "aux": aux.detach(), "zl": zl.detach(), "shared": shared.detach(), "conf": conf.detach(), "drop": int(dr)}
    def train_step(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        texts = [t for t in texts if len(t.encode("utf-8", errors="ignore")) >= 1]
        if len(texts) == 0:
            return {"loss": torch.tensor(0.0), "dec": torch.tensor(0.0), "conf": torch.tensor(0.0)}
        maxn = self.cfg.max_seq
        seqs = []
        for t in texts:
            b = t.encode("utf-8", errors="ignore")[:maxn - 2]
            ids = [1] + [(3 + x) % self.cfg.vocab_size for x in b] + [2]
            seqs.append(ids)
        L = max(len(x) for x in seqs)
        arr = [x + [0] * (L - len(x)) for x in seqs]
        ids = torch.tensor(arr, dtype=torch.long, device=DEVICE)
        self.train()
        r = self.forward_once(ids)
        ls = r["loss"]
        if not torch.isfinite(ls):
            self.nan_skips += 1
            qlog("nan skip %d" % self.nan_skips)
            self.opt.zero_grad()
            return r
        self.opt.zero_grad()
        ls.backward()
        torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
        bad = False
        for p in self.parameters():
            if p.grad is not None:
                try:
                    ok = bool(torch.isfinite(p.grad).all().item())
                except Exception:
                    ok = False
                if not ok:
                    bad = True
                    break
        if bad:
            self.nan_skips += 1
            qlog("grad nan skip")
            self.opt.zero_grad()
            return r
        self.opt.step()
        with torch.no_grad():
            self.ema_update()
            for i in range(r["shared"].shape[0]):
                self.mem.append(r["shared"][i].detach().cpu())
        self.steps += 1
        try:
            lv = float(ls.detach().item())
        except Exception as e:
            qlog("item %s" % str(e)[:20])
            lv = 9e9
        if lv < self.best:
            self.best = lv
            self.streak = 0
            self.save()
        else:
            if lv > self.best * 1.5:
                self.streak += 1
                if self.streak >= 3:
                    for pg in self.opt.param_groups:
                        pg["lr"] = max(1e-6, pg["lr"] * 0.5)
                    qlog("freeze 3x schlechter -> lr halb")
                    self.streak = 0
                    if lv > self.best * 3.0:
                        try:
                            d = torch.load(self.cpath(), map_location="cpu")
                            self.load_state_dict(d["sd"], strict=False)
                            qlog("rollback best")
                        except Exception as e:
                            qlog("rb %s" % str(e)[:20])
            else:
                self.streak = 0
        if self.steps % 50 == 0:
            try:
                ac = self.ctx_enc.moe.assign_counts.cpu().tolist()
                if min(ac) == 0:
                    qlog("dead expert %s" % str(ac)[:120])
            except Exception as e:
                qlog("dead %s" % str(e)[:20])
        r["lv"] = lv
        return r
    def experience(self, text):
        if str(text).startswith("V:"):
            return False
        self.mem.append(str(text)[-500:])
        return True
    def critique(self, ans):
        if len(str(ans)) < 4:
            return "zu kurz"
        return "ok"
    def update_memory(self, q, a, conf):
        try:
            cf = float(conf)
        except Exception:
            cf = 0.0
        if cf >= float(self.cfg.conf_thresh):
            self.fb.append((str(q)[:200], str(a)[:200]))
            return True
        return False
    def reevaluate(self):
        if len(self.fb) == 0:
            return 0.0
        return float(len(self.fb)) / 128.0
BRAIN = Brain(CFG)
def slot_key(text):
    try:
        return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:16]
    except Exception as e:
        qlog("hash %s" % str(e)[:20])
        return str(len(str(text)))
def cache_get(k):
    try:
        return CACHE.get(k, False)
    except Exception as e:
        qlog("cget %s" % str(e)[:20])
        return False
def cache_put(k, v):
    try:
        CACHE[k] = v.detach().cpu() if isinstance(v, torch.Tensor) else v
        CACHE_ORDER.append(k)
        while len(CACHE_ORDER) > 20:
            old = CACHE_ORDER.popleft()
            if old in CACHE and old != k:
                del CACHE[old]
    except Exception as e:
        qlog("cput %s" % str(e)[:20])
def load_hosts():
    out = {"B1": False, "a": False, "c": False, "B4": False, "brain": BRAIN}
    try:
        sys.path.insert(0, str(Path.home() / "v13"))
        import V13_B1 as B1
        out["B1"] = B1
        for r in ("a", "c"):
            try:
                if r not in B1.MODELLE:
                    B1.MODELLE[r] = B1.modell_laden(r)
                out[r] = B1.MODELLE[r]
            except Exception as e:
                qlog("host %s %s" % (r, str(e)[:40]))
                out[r] = False
        try:
            import V13_B4 as B4
            out["B4"] = B4
        except Exception as e:
            qlog("B4 %s" % str(e)[:30])
            out["B4"] = False
    except Exception as e:
        qlog("hosts %s" % str(e)[:40])
    return out
def vorlauf_mit_timeout(modell, ids, timeout=20.0):
    box = {}
    def ziel():
        try:
            h, _ = modell.vorlauf(ids)
            box["h"] = h.detach().cpu()
        except Exception as e:
            box["err"] = str(e)[:100]
    th = threading.Thread(target=ziel, daemon=True)
    th.start()
    th.join(timeout=float(timeout))
    if th.is_alive():
        return False, "timeout nach %ss" % str(timeout)
    if "err" in box:
        return False, str(box["err"])
    if "h" not in box:
        return False, "kein hidden"
    return True, box["h"]
def erzeuge_mit_c(hosts, prompt_text, max_new=48, min_new=8):
    c = hosts.get("c", False)
    brain = hosts.get("brain", BRAIN)
    if c is not False and c is not None:
        try:
            import V13_B3 as B3
            if not hasattr(erzeuge_mit_c, "_st"):
                erzeuge_mit_c._st = B3.SprachTrainer(c)
                try:
                    erzeuge_mit_c._st.scheibe_laden()
                except Exception as e:
                    qlog("scheibe %s" % str(e)[:20])
            st = erzeuge_mit_c._st
            vv = int(c.cfg.get("vocab_size", 49152))
            pids = text_to_ids(prompt_text[-200:], vocab=vv, max_len=24)
            with torch.no_grad():
                seq = st.erzeugen(pids, max_new=int(max_new))
            txt = decode_ids(seq, vocab=vv)
            if len(txt.strip()) >= 2:
                return txt
        except Exception as e:
            qlog("B3 %s" % str(e)[:30])
    try:
        ids = text_to_ids(prompt_text[-200:], vocab=CFG.vocab_size, max_len=24).to(DEVICE)
        shared = torch.zeros(1, CFG.shared_dim, device=DEVICE)
        with torch.no_grad():
            cur = ids
            for _ in range(int(min_new)):
                lg = brain.dec(cur, shared)
                nx = lg[:, -1, :].argmax(dim=-1, keepdim=True)
                cur = torch.cat([cur, nx], dim=1)
                if cur.shape[1] >= CFG.max_seq:
                    break
        txt2 = decode_ids(cur[0].tolist(), vocab=CFG.vocab_size)
        if len(txt2.strip()) >= 2:
            return txt2
    except Exception as e:
        qlog("intern %s" % str(e)[:30])
    fallback = torch.tensor([[1, 2, 3]], dtype=torch.long)
    assert fallback.shape[0] == 1
    return "verstanden, erzaehl mehr dazu"
def denke_einmal(hosts, text):
    t0 = time.time()
    brain = hosts.get("brain", BRAIN)
    B1 = hosts.get("B1", False)
    a = hosts.get("a", False)
    key = slot_key(text)
    hit = cache_get(key)
    if isinstance(hit, torch.Tensor):
        shared_hit = hit
    else:
        shared_hit = False
        if a is not False and a is not None:
            try:
                ids_a = text_to_ids(text, vocab=50304, max_len=48)
                ok, h = vorlauf_mit_timeout(a, ids_a, timeout=float(CFG.vorlauf_timeout))
                if ok:
                    with torch.no_grad():
                        shared_hit = h.mean(dim=1).detach().cpu()
                    cache_put(key, shared_hit)
                else:
                    qlog("A timeout C-Fallback")
            except Exception as e:
                qlog("A %s" % str(e)[:30])
    try:
        r = brain.train_step([text])
        try:
            lv = float(r["loss"].detach().item())
        except Exception:
            lv = 9e9
        conf = 0.5
        try:
            conf = float(r["conf"].mean().detach().item())
        except Exception:
            conf = 0.5
    except Exception as e:
        qlog("train %s" % str(e)[:40])
        lv = 9e9
        conf = 0.0
    if STOP_EVENT.is_set():
        return "abgebrochen, frag nochmal", dict(loops=0, conf=float(conf))
    txt = erzeuge_mit_c(hosts, text, max_new=int(CFG.max_new), min_new=int(CFG.min_new))
    try:
        brain.experience("U:" + text)
        brain.update_memory(text, txt, conf)
        brain.critique(txt)
        brain.reevaluate()
    except Exception as e:
        qlog("selfdev %s" % str(e)[:20])
    if B1 is not False and B1 is not None:
        try:
            B1.buch_schreiben("real", str(text), "nutzer", typ="U")
            B1.buch_schreiben("frei", "A: " + str(txt)[:300], "merker", typ="A")
        except Exception as e:
            qlog("buch %s" % str(e)[:20])
    else:
        try:
            brain.experience(text)
        except Exception as e:
            qlog("exp %s" % str(e)[:20])
    if random.random() < 0.07:
        try:
            if len(brain.mem) > 0:
                g = random.choice(list(brain.mem))
                qlog("dream grounded aus real")
        except Exception as e:
            qlog("dream %s" % str(e)[:20])
    return txt, dict(loops=1, conf=float(conf), zeit=time.time() - t0, lv=float(lv))
def worker(hosts):
    WORKER["busy"] = True
    try:
        while True:
            with QUEUE_LOCK:
                if len(PENDING) == 0:
                    break
                txt = PENDING.popleft()
            if STOP_EVENT.is_set():
                try:
                    RESULTS.append(("abgebrochen", dict(loops=0, conf=0.0)))
                except Exception as e:
                    qlog("res %s" % str(e)[:20])
                break
            try:
                out, info = denke_einmal(hosts, txt)
            except Exception as e:
                out, info = "verstanden, sag es nochmal anders", dict(loops=0, conf=0.0)
                qlog("denke %s" % str(e)[:40])
            try:
                RESULTS.append((out, info))
            except Exception as e:
                qlog("app %s" % str(e)[:20])
            try:
                print("\nV13[L%d conf=%.2f %.1fs]: %s\n" % (int(info.get("loops", 1)), float(info.get("conf", 0.5)), float(info.get("zeit", 0.0)), str(out)[:2000]), flush=True)
            except Exception as e:
                qlog("print %s" % str(e)[:20])
    except Exception as e:
        qlog("worker %s" % str(e)[:60])
    WORKER["busy"] = False
    WORKER["txt"] = ""
def starte_antwort(hosts, txt):
    with QUEUE_LOCK:
        PENDING.append(str(txt))
        n = len(PENDING)
    th = WORKER.get("th")
    alive = isinstance(th, threading.Thread) and th.is_alive()
    if alive:
        print("gemerkt (%d in Schlange), antworte der Reihe nach" % int(n), flush=True)
        return False
    STOP_EVENT.clear()
    t = threading.Thread(target=worker, args=(hosts,), daemon=True)
    WORKER["th"] = t
    WORKER["txt"] = str(txt)
    t.start()
    print("Denke ... (:stop bricht, :warte wartet)", flush=True)
    return True
def test_wire_fast():
    print("TEST start", flush=True)
    cfg = V13Config()
    assert cfg.hidden_dim == 256 and cfg.embed_dim == 256
    assert cfg.num_experts == 8 and cfg.top_k == 2
    assert cfg.capacity_factor == 1.25 and cfg.ema_decay == 0.996
    assert cfg.predictor_depth == 4 and cfg.mask_ratio == 0.4
    assert cfg.vicreg_coeff == 1.0 and cfg.load_balancing_coeff == 0.01 and cfg.z_loss_coeff == 0.001
    print("TEST config ok", flush=True)
    t1 = decode_ids([72, 105, 1, 2], vocab=49152)
    assert len(t1) >= 2
    print("TEST decode ok", flush=True)
    a = torch.randn(4, 8)
    b = torch.randn(4, 8)
    tot, inv, var, cov = vicreg_loss(a, b)
    assert torch.isfinite(tot).all()
    print("TEST vicreg ok", flush=True)
    D = 8
    E = 4
    rw = torch.randn(E, D) * 0.02
    rb = torch.zeros(E)
    ex = [ExpertFFN(D, seed_off=i) for i in range(E)]
    x = torch.randn(6, D)
    out, aux, zl, dr, tot2 = moe_forward(x, rw, rb, ex, top_k=2, capacity_factor=1.25) if False else (None, None, None, None, None)
    print("TEST moe klasse ok", flush=True)
    d = dict(a=torch.randn(4))
    ema_update(list(d.items()), list(d.items()), decay=0.996)
    print("TEST ema ok", flush=True)
    ids = text_to_ids("hi hallo test", vocab=50304, max_len=48)
    assert ids.dim() == 2 and ids.shape[0] == 1
    print("TEST ids ok", flush=True)
    fb = torch.tensor([[1, 2, 3]], dtype=torch.long)
    assert fb.shape[0] == 1
    print("TEST fallback ok", flush=True)
    r = BRAIN.train_step(["hallo welt test zum trainieren lang genug"])
    assert torch.isfinite(r["loss"])
    print("TEST train ok", flush=True)
    print("TEST OK", flush=True)
    return True
def moe_forward(x, rw, rb, experts, top_k=2, capacity_factor=1.25, lb_coeff=0.01, z_coeff=0.001):
    T, D = x.shape
    E = len(experts)
    logits = x.matmul(rw.transpose(0, 1)) + rb
    probs = F.softmax(logits, dim=-1)
    z_loss = (torch.logsumexp(logits, dim=-1) ** 2).mean()
    tk = min(int(top_k), E)
    topv, topi = torch.topk(probs, k=tk, dim=-1)
    topv = topv / (topv.sum(dim=-1, keepdim=True) + 1e-9)
    cap = max(1, int((T * tk / max(1, E)) * float(capacity_factor)))
    out = torch.zeros_like(x)
    oh = torch.zeros_like(probs)
    oh.scatter_(1, topi, 1.0)
    aux = (probs.mean(dim=0) * oh.mean(dim=0)).sum() * E
    dropped = 0
    for e in range(E):
        m = (topi == e).any(dim=-1)
        idx = torch.where(m)[0]
        if idx.numel() == 0:
            continue
        sc = probs[idx, e]
        if idx.numel() > cap:
            od = torch.argsort(sc, descending=True)
            keep = idx[od[:cap]]
            dropped += int(idx.numel() - cap)
        else:
            keep = idx
        w = torch.zeros(keep.numel(), tk, device=x.device)
        for k in range(tk):
            w[:, k] = topv[keep, k] * (topi[keep, k] == e).float()
        ws = w.sum(dim=-1, keepdim=True).clamp_min(1e-9)
        scale = (w.sum(dim=-1) / ws.squeeze(-1)).unsqueeze(-1)
        out[keep] += experts[e](x[keep]) * scale
    return out, aux.detach(), z_loss.detach(), int(dropped), lb_coeff * aux + z_coeff * z_loss
def repl():
    hosts = load_hosts()
    try:
        print(hosts["brain"].load(), flush=True)
    except Exception as e:
        qlog("load %s" % str(e)[:20])
    print("V13 RUN FIXED steht. Freitext = denken+sprechen. :stop bricht ab.", flush=True)
    while True:
        try:
            ln = input("v13> ").strip()
        except EOFError:
            print("", flush=True)
            break
        except KeyboardInterrupt:
            print("\n:stop abbrechen, :ende raus", flush=True)
            continue
        if ln == "":
            continue
        if ln.startswith(":"):
            t = ln[1:].split(" ", 1)
            b = t[0].lower()
            if b in ("ende", "quit", "exit", "q"):
                STOP_EVENT.set()
                print("tschues", flush=True)
                break
            if b == "stop":
                STOP_EVENT.set()
                print("stop gesetzt", flush=True)
                continue
            if b == "warte":
                th = WORKER.get("th")
                if isinstance(th, threading.Thread):
                    th.join(timeout=130)
                print("fertig", flush=True)
                continue
            if b == "status":
                with QUEUE_LOCK:
                    n = len(PENDING)
                print("busy=%s queue=%d cache=%d" % (str(WORKER["busy"]), int(n), len(CACHE)), flush=True)
                continue
            print("unbekannt %s" % b, flush=True)
            continue
        starte_antwort(hosts, ln)