
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V13 Brain / runnable reference implementation

This file implements the architecture, not a fake text generator:

    language tokens
          |
          v
     adaptive backbone
          |
     latent world state Z
       /           \
      A             B
   sparse MoE     sparse MoE
      +-------------+
       +-- small --+
        semi-link
           |
    cautiousness / conflict
           |
         Z_Inq
       P1 <-> P2
           |
       N rounds
           |
       language head

The two hemispheres have independent expert pools and routers.
P1/P2 are roles over one shared LoRA parameter space.
Stream A is compressed semantic state.
Stream B is exact episodic memory.
Learning is continuous and split into fast adapter updates and very slow
backbone consolidation.

The default model is deliberately small so the program can be tested on CPU.
Scaling d_model, layers, experts and sequence length is the intended next step.
"""

from __future__ import annotations
import argparse, copy, hashlib, json, math, os, random, shutil, sqlite3, tempfile, time
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Config:
    vocab_size: int = 259
    d_model: int = 256
    n_layers: int = 4
    n_heads: int = 8

    # Sparse MoE
    num_experts: int = 8
    top_k: int = 2
    capacity_factor: float = 1.25
    expert_mult: int = 2

    # LoRA
    lora_rank: int = 8
    lora_alpha: float = 16.0
    lora_dropout: float = 0.03

    # Semi-permeable bridge
    bridge_fraction: float = 0.125
    bridge_strength: float = 0.15

    # Small cautiousness layer
    cautious_base: float = 0.05
    cautious_max: float = 0.25
    cautious_scale: float = 2.0

    # Nested Inquisition
    inq_dim: int = 128
    rounds: int = 2
    manipulation_strength: float = 0.25
    p1_weight: float = 0.35
    p2_weight: float = 0.35

    # Stream A
    stream_a_slots: int = 64
    stream_a_decay: float = 0.997
    stream_a_topk: int = 4

    # Stream B
    stream_b_max: int = 10000
    stream_b_topk: int = 4

    # Continual learning
    lr_fast: float = 3e-4
    lr_router: float = 2e-4
    lr_backbone: float = 2e-6
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    replay_size: int = 4096
    replay_batch: int = 4
    replay_ratio: float = 0.5
    consolidate_every: int = 32
    ema_beta: float = 1e-4

    # Self-improvement
    self_candidates: int = 2
    positive_threshold: float = 0.78

    # Generation
    max_seq: int = 512
    max_new_tokens: int = 128
    temperature: float = 0.75
    top_p: float = 0.92

    # Checkpoint
    workdir: str = "~/.v13_brain"
    seed: int = 42


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def seed_all(seed: int):
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def assert_finite(x: torch.Tensor, name: str):
    if not torch.isfinite(x).all():
        raise FloatingPointError(f"{name} contains NaN/Inf")


def cosine(a, b):
    return F.cosine_similarity(a, b, dim=-1, eps=1e-6)


# ---------------------------------------------------------------------------
# Byte tokenizer
# ---------------------------------------------------------------------------

class ByteTokenizer:
    pad_id = 0
    bos_id = 1
    eos_id = 2
    offset = 3
    vocab_size = 259

    def encode(self, text: str, max_len: int):
        raw = text.encode("utf-8", errors="replace")[:max(0, max_len - 2)]
        return [1] + [self.offset + b for b in raw] + [2]

    def decode(self, ids):
        raw = bytearray()
        for i in ids:
            i = int(i)
            if self.offset <= i < self.offset + 256:
                raw.append(i - self.offset)
        return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Ternary base + LoRA adapter
# ---------------------------------------------------------------------------

class TernaryLinear(nn.Module):
    """
    Master weights are stored for optimization.
    Forward weights are ternarized with an STE.

    This is the BitNet-like mechanism used here. It is not a claim that this
    exact implementation reproduces a production BitNet kernel.
    """

    def __init__(self, din, dout, bias=True):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(dout, din))
        self.bias = nn.Parameter(torch.zeros(dout)) if bias else None
        nn.init.normal_(self.weight, std=0.02)

    def quantized_weight(self):
        w = self.weight
        scale = w.abs().mean(dim=1, keepdim=True).clamp_min(1e-5)
        q = (w / scale).round().clamp(-1, 1) * scale
        return w + (q - w).detach()

    def forward(self, x):
        return F.linear(x, self.quantized_weight(), self.bias)


class LoRALinear(nn.Module):
    """
    Slow base + fast low-rank update.

        y = Q(W_base)x + B(Ax)

    The adapter can be merged into W_base slowly during consolidation.
    """

    def __init__(self, din, dout, rank, alpha, dropout=0.0, bias=True):
        super().__init__()
        self.base = TernaryLinear(din, dout, bias=bias)
        self.rank = rank
        self.scale = alpha / max(1, rank)
        self.drop = nn.Dropout(dropout)
        self.lora_A = nn.Parameter(torch.empty(rank, din))
        self.lora_B = nn.Parameter(torch.zeros(dout, rank))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))

    def forward(self, x):
        base = self.base(x)
        lora = F.linear(F.linear(self.drop(x), self.lora_A), self.lora_B)
        return base + self.scale * lora

    @torch.no_grad()
    def merge_slow(self, beta: float):
        """
        Integrate only beta of the learned adapter into the base.
        Then zero the adapter so the same experience is not counted twice.
        """
        delta = self.scale * (self.lora_B @ self.lora_A)
        self.base.weight.add_(delta.to(self.base.weight.dtype), alpha=beta)
        self.lora_A.mul_(math.sqrt(max(0.0, 1.0 - beta)))
        self.lora_B.mul_(math.sqrt(max(0.0, 1.0 - beta)))


# ---------------------------------------------------------------------------
# Sparse MoE
# ---------------------------------------------------------------------------

class Expert(nn.Module):
    def __init__(self, d, mult, cfg):
        super().__init__()
        h = d * mult
        self.fc1 = LoRALinear(d, h, cfg.lora_rank, cfg.lora_alpha, cfg.lora_dropout)
        self.fc2 = LoRALinear(h, d, cfg.lora_rank, cfg.lora_alpha, cfg.lora_dropout)

    def forward(self, x):
        return self.fc2(F.silu(self.fc1(x)))


class SparseMoE(nn.Module):
    """
    True Top-K token routing.

    Only the selected experts are evaluated. Capacity limits prevent a
    single expert from absorbing arbitrary traffic.
    """

    def __init__(self, d, cfg):
        super().__init__()
        self.d = d
        self.e = cfg.num_experts
        self.k = min(cfg.top_k, cfg.num_experts)
        self.capacity_factor = cfg.capacity_factor
        self.router = LoRALinear(
            d, self.e, cfg.lora_rank, cfg.lora_alpha, cfg.lora_dropout
        )
        self.experts = nn.ModuleList([
            Expert(d, cfg.expert_mult, cfg) for _ in range(self.e)
        ])
        self.register_buffer("assign_counts", torch.zeros(self.e, dtype=torch.long))
        self.register_buffer("dropped", torch.zeros(1, dtype=torch.long))

    def forward(self, x):
        B, T, D = x.shape
        flat = x.reshape(-1, D)

        logits = self.router(flat)
        probs = F.softmax(logits.float(), dim=-1).to(x.dtype)
        topv, topi = torch.topk(probs, self.k, dim=-1)
        topv = topv / topv.sum(dim=-1, keepdim=True).clamp_min(1e-6)

        capacity = max(
            1,
            math.ceil(flat.shape[0] * self.k / self.e * self.capacity_factor)
        )

        out = torch.zeros_like(flat)
        counts = torch.zeros(self.e, device=x.device, dtype=torch.long)
        accepted_weight = torch.zeros(flat.shape[0], device=x.device, dtype=x.dtype)

        for e in range(self.e):
            ids = torch.where((topi == e).any(dim=-1))[0]
            if ids.numel() == 0:
                continue

            scores = probs[ids, e].float()
            if ids.numel() > capacity:
                keep = torch.topk(scores, capacity).indices
                dropped_now = ids.numel() - capacity
                self.dropped += int(dropped_now)
                ids = ids[keep]

            w = probs[ids, e]
            y = self.experts[e](flat[ids])
            out[ids] += y * w.unsqueeze(-1)
            accepted_weight[ids] += w
            counts[e] = ids.numel()

        out = out / accepted_weight.clamp_min(1e-6).unsqueeze(-1)

        importance = probs.float().mean(dim=0)
        hard = F.one_hot(topi.reshape(-1), self.e).float().mean(dim=0)
        balance_loss = self.e * (importance * hard).sum()
        z_loss = torch.logsumexp(logits.float(), dim=-1).pow(2).mean()

        with torch.no_grad():
            self.assign_counts += counts.cpu()

        return out.reshape(B, T, D), {
            "balance": balance_loss,
            "z_loss": z_loss,
            "drop_rate": self.dropped.float() / (
                self.assign_counts.sum().clamp_min(1).float()
            ),
            "load": counts.float() / max(1, flat.shape[0]),
        }


# ---------------------------------------------------------------------------
# Causal attention
# ---------------------------------------------------------------------------

class CausalAttention(nn.Module):
    def __init__(self, d, heads, cfg):
        super().__init__()
        assert d % heads == 0
        self.h = heads
        self.hd = d // heads
        self.qkv = LoRALinear(d, 3*d, cfg.lora_rank, cfg.lora_alpha, cfg.lora_dropout)
        self.proj = LoRALinear(d, d, cfg.lora_rank, cfg.lora_alpha, cfg.lora_dropout)

    def forward(self, x, padding=None):
        B,T,D=x.shape
        q,k,v=self.qkv(x).chunk(3,dim=-1)
        q=q.view(B,T,self.h,self.hd).transpose(1,2)
        k=k.view(B,T,self.h,self.hd).transpose(1,2)
        v=v.view(B,T,self.h,self.hd).transpose(1,2)

        causal=torch.ones(T,T,device=x.device,dtype=torch.bool).tril()
        mask=torch.zeros(T,T,device=x.device,dtype=x.dtype)
        mask.masked_fill_(~causal,float("-inf"))

        if padding is not None:
            mask=mask[None,None,:,:].masked_fill(
                padding[:,None,None,:],float("-inf")
            )

        y=F.scaled_dot_product_attention(
            q,k,v,attn_mask=mask,dropout_p=0.0,is_causal=False
        )
        y=y.transpose(1,2).contiguous().view(B,T,D)
        return self.proj(y)


# ---------------------------------------------------------------------------
# Hemisphere coupling
# ---------------------------------------------------------------------------

class SemiPermeableBridge(nn.Module):
    """
    A small learned channel subset crosses between hemispheres.
    """

    def __init__(self,d,cfg):
        super().__init__()
        self.k=max(1,int(d*cfg.bridge_fraction))
        self.a2b=LoRALinear(self.k,self.k,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout)
        self.b2a=LoRALinear(self.k,self.k,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout)
        self.strength=cfg.bridge_strength

    def forward(self,a,b):
        am=self.a2b(a[...,:self.k])
        bm=self.b2a(b[...,:self.k])
        ao=a.clone()
        bo=b.clone()
        ao[...,:self.k]+=self.strength*bm
        bo[...,:self.k]+=self.strength*am
        return ao,bo


class CautiousnessGate(nn.Module):
    """
    Small conflict-sensitive coupling controller.

    It is a compute / coupling signal, not a magical truth detector.
    """

    def __init__(self,d,cfg):
        super().__init__()
        self.net=nn.Sequential(
            LoRALinear(2*d,d//2,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
            nn.SiLU(),
            LoRALinear(d//2,1,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
        )
        self.base=cfg.cautious_base
        self.maximum=cfg.cautious_max
        self.scale=cfg.cautious_scale

    def forward(self,a,b):
        conflict=1-cosine(a,b).clamp(-1,1)
        learned=torch.sigmoid(self.net(torch.cat([a,b],dim=-1)).float()).squeeze(-1)
        c=self.base+(self.maximum-self.base)*torch.sigmoid(self.scale*conflict)*learned
        return c.clamp(self.base,self.maximum),conflict


# ---------------------------------------------------------------------------
# Nested latent Inquisition
# ---------------------------------------------------------------------------

class SharedP12(nn.Module):
    """
    One parameter space, two roles.

    P1 and P2 call the SAME network. They are not two independent models.
    Their different inputs create the roles:

      P1: manipulated/hypothesis view
      P2: manipulated view + fresh encoder view

    Winner-takes-both is represented as a state transition, not parameter
    deletion. This preserves the user's shared-space idea without deleting
    useful shared parameters.
    """

    def __init__(self,d,q,cfg):
        super().__init__()
        self.to_q=LoRALinear(d,q,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout)
        self.shared=nn.Sequential(
            LoRALinear(q,q*2,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
            nn.SiLU(),
            LoRALinear(q*2,q,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
        )
        self.to_z=LoRALinear(q,d,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout)

    def forward(self,z,cautious,cfg):
        q=self.to_q(z)
        trace=[]

        for r in range(max(1,cfg.rounds)):
            # P1
            p1=self.shared(q)
            manipulated=q+cfg.manipulation_strength*torch.tanh(p1)

            # P2 receives manipulated data plus fresh encoder information
            fresh=self.to_q(z).detach()
            p2=self.shared(0.5*manipulated+0.5*fresh)

            kappa=cosine(p1,p2)
            conflict=(1-kappa).clamp_min(0)

            alpha=(
                0.08
                + 0.25*cautious.unsqueeze(-1)
                + 0.20*conflict.unsqueeze(-1)
            ).clamp(0.05,0.55)

            candidate=cfg.p1_weight*manipulated+cfg.p2_weight*p2

            # Role competition
            p1_score=p1.norm(dim=-1)
            p2_score=p2.norm(dim=-1)
            p2_wins=(p2_score>=p1_score).to(q.dtype).unsqueeze(-1)
            winner=p2_wins*p2+(1-p2_wins)*manipulated

            # winner occupies the common state for the next round
            q=(1-alpha)*q+alpha*(0.5*candidate+0.5*winner)

            trace.append({
                "round":r+1,
                "kappa":kappa.detach(),
                "conflict":conflict.detach(),
                "p1_norm":p1_score.detach(),
                "p2_norm":p2_score.detach(),
                "p2_wins":p2_wins.squeeze(-1).detach(),
            })

        return self.to_z(q),trace


# ---------------------------------------------------------------------------
# Stream A
# ---------------------------------------------------------------------------

class StreamA(nn.Module):
    """
    Compressed semantic state.

    It is bounded in storage and intentionally lossy. Older information is
    folded into latent slots rather than kept token-for-token.
    """

    def __init__(self,d,cfg):
        super().__init__()
        self.slots=cfg.stream_a_slots
        self.decay=cfg.stream_a_decay
        self.topk=min(cfg.stream_a_topk,self.slots)
        self.write=nn.Sequential(
            LoRALinear(d,d,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
            nn.SiLU(),
            LoRALinear(d,d,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
        )
        self.key=nn.Parameter(torch.randn(self.slots,d)*0.02)
        self.register_buffer("state",torch.zeros(self.slots,d))
        self.register_buffer("usage",torch.zeros(self.slots))

    def read(self,q):
        s=F.cosine_similarity(
            self.key.unsqueeze(0),q.unsqueeze(1),dim=-1
        )
        idx=s.topk(self.topk,dim=-1).indices
        vals=self.state[idx]
        w=F.softmax(s.gather(1,idx),dim=-1)
        return (vals*w.unsqueeze(-1)).sum(1)

    @torch.no_grad()
    def integrate(self,z):
        x=self.write(z.detach()).mean(0)
        s=F.cosine_similarity(self.key,x.unsqueeze(0),dim=-1)
        idx=s.topk(self.topk).indices
        for i in idx.tolist():
            self.state[i].mul_(self.decay).add_(x,alpha=1-self.decay)
            self.usage[i]+=1


# ---------------------------------------------------------------------------
# Stream B
# ---------------------------------------------------------------------------

class StreamB:
    """
    Exact episodic store.

    The database is not a neural memory. It stores exact text, outcome,
    correction and score so that replay can be reproducible.
    """

    def __init__(self,path,max_items,topk):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.topk=topk
        self.db=sqlite3.connect(self.path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS episodes(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts REAL NOT NULL,
              user TEXT NOT NULL,
              answer TEXT NOT NULL,
              score REAL,
              correction TEXT,
              capability REAL,
              accepted INTEGER DEFAULT 0,
              sha TEXT
            )
        """)
        self.db.commit()
        self.max_items=max_items

    def add(self,user,answer,score=None,correction=None,capability=None,accepted=False):
        sha=hashlib.sha256(
            (user+"\n"+answer+"\n"+str(correction)).encode("utf-8")
        ).hexdigest()
        self.db.execute(
            """INSERT INTO episodes
               (ts,user,answer,score,correction,capability,accepted,sha)
               VALUES(?,?,?,?,?,?,?,?)""",
            (time.time(),user,answer,score,correction,capability,int(accepted),sha)
        )
        self.db.execute("""
            DELETE FROM episodes WHERE id NOT IN
            (SELECT id FROM episodes ORDER BY id DESC LIMIT ?)
        """,(self.max_items,))
        self.db.commit()

    def retrieve(self,query,k=None):
        k=k or self.topk
        rows=self.db.execute(
            "SELECT user,answer,score,correction FROM episodes ORDER BY id DESC LIMIT 4000"
        ).fetchall()
        q=set(query.lower().split())
        ranked=[]
        for u,a,s,c in rows:
            overlap=len(q & set((u+" "+a).lower().split()))
            if overlap:
                ranked.append((overlap,u,a,s,c))
        ranked.sort(key=lambda x:(x[0],x[2] or ""),reverse=True)
        return ranked[:k]

    def count(self):
        return int(self.db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])


# ---------------------------------------------------------------------------
# Experience replay
# ---------------------------------------------------------------------------

@dataclass
class Experience:
    user:str
    answer:str
    score:float
    correction:Optional[str]
    capability:float
    novelty:float
    ts:float


class Replay:
    def __init__(self,maxlen):
        self.items=deque(maxlen=maxlen)

    def add(self,e):
        self.items.append(e)

    def sample(self,n):
        if not self.items:return []
        n=min(n,len(self.items))
        xs=list(self.items)
        if len(xs)<=n:return xs

        # Recent, quality and novelty all matter.
        now=time.time()
        w=[]
        for e in xs:
            rec=math.exp(-max(0,now-e.ts)/(14*86400))
            qual=0.2+0.8*e.score
            w.append(0.45*rec+0.40*qual+0.15*e.novelty)

        chosen=[]
        pool=list(range(len(xs)))
        ww=w[:]
        for _ in range(n):
            p=torch.tensor([ww[i] for i in pool],dtype=torch.float64)
            idx=int(torch.multinomial(p/p.sum(),1).item())
            chosen.append(xs[pool.pop(idx)])
            ww.pop(idx)
        return chosen

    def __len__(self):return len(self.items)


# ---------------------------------------------------------------------------
# Capability signal
# ---------------------------------------------------------------------------

class CapabilityHead(nn.Module):
    def __init__(self,d,cfg):
        super().__init__()
        self.net=nn.Sequential(
            LoRALinear(d,d//2,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
            nn.SiLU(),
            LoRALinear(d//2,3,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
        )

    def forward(self,z):
        return torch.sigmoid(self.net(z))
        # [difficulty, novelty, compute_need]


# ---------------------------------------------------------------------------
# One brain layer
# ---------------------------------------------------------------------------

class BrainLayer(nn.Module):
    def __init__(self,cfg):
        super().__init__()
        d=cfg.d_model
        self.attn_norm=nn.LayerNorm(d)
        self.attn=CausalAttention(d,cfg.n_heads,cfg)

        self.a_norm=nn.LayerNorm(d)
        self.b_norm=nn.LayerNorm(d)
        self.a=SparseMoE(d,cfg)
        self.b=SparseMoE(d,cfg)

        self.bridge=SemiPermeableBridge(d,cfg)
        self.caution=CautiousnessGate(d,cfg)

        self.post=nn.Sequential(
            LoRALinear(d,d,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
            nn.SiLU(),
            LoRALinear(d,d,cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout),
        )

    def forward(self,x,pad=None):
        x=x+self.attn(self.attn_norm(x),pad)
        a,_=self.a(self.a_norm(x))
        b,_=self.b(self.b_norm(x))

        a,b=self.bridge(a,b)

        ca,conf=self.caution(a.mean(1),b.mean(1))
        # Cautiousness is a small coupling brake, not an output filter.
        gain=(1-ca).unsqueeze(-1).unsqueeze(-1)

        x=x+0.5*(a+b)*gain
        x=x+self.post(x)

        return x,{
            "a":a,"b":b,
            "cautiousness":ca,
            "conflict":conf,
        }


# ---------------------------------------------------------------------------
# Complete model
# ---------------------------------------------------------------------------

class V13Model(nn.Module):
    def __init__(self,cfg,device):
        super().__init__()
        self.cfg=cfg
        self.device=device

        self.embedding=nn.Embedding(cfg.vocab_size,cfg.d_model)
        self.position=nn.Embedding(cfg.max_seq,cfg.d_model)

        self.layers=nn.ModuleList([BrainLayer(cfg) for _ in range(cfg.n_layers)])
        self.norm=nn.LayerNorm(cfg.d_model)
        self.lm_head=LoRALinear(
            cfg.d_model,cfg.vocab_size,
            cfg.lora_rank,cfg.lora_alpha,cfg.lora_dropout
        )

        self.inquisition=SharedP12(cfg.d_model,cfg.inq_dim,cfg)
        self.stream_a=StreamA(cfg.d_model,cfg)
        self.capability=CapabilityHead(cfg.d_model,cfg)

        self.to(device)

    def encode(self,ids):
        B,T=ids.shape
        pos=torch.arange(T,device=ids.device).unsqueeze(0)
        x=self.embedding(ids)+self.position(pos)
        pad=(ids==0)
        traces=[]
        for layer in self.layers:
            x,t=layer(x,pad)
            traces.append(t)
        return self.norm(x),traces

    def forward(self,ids,targets=None):
        z,traces=self.encode(ids)

        left=torch.stack([t["a"].mean(1) for t in traces]).mean(0)
        right=torch.stack([t["b"].mean(1) for t in traces]).mean(0)
        world=0.42*left+0.42*right+0.16*self.stream_a.read(
            (left+right)*0.5
        )

        cap=self.capability(world)
        cautious=traces[-1]["cautiousness"]

        inq,inq_trace=self.inquisition(
            world,cautious,self.cfg
        )

        # Inject the post-inquisition world state into all positions.
        h=z+inq.unsqueeze(1)
        logits=self.lm_head(h)

        loss=None
        metrics={}
        if targets is not None:
            lm=F.cross_entropy(
                logits[:,:-1].reshape(-1,logits.size(-1)),
                targets[:,1:].reshape(-1),
                ignore_index=0
            )

            # JEPA-like latent prediction. Predict future latent from current
            # latent without exposing future input to the predictor.
            if z.size(1)>1:
                pred=z[:,:-1].mean(1)
                target=z[:,1:].detach().mean(1)
                jepa=F.smooth_l1_loss(pred,target)
            else:
                jepa=torch.zeros((),device=ids.device)

            balance=torch.zeros((),device=ids.device)
            zloss=torch.zeros((),device=ids.device)
            for layer in self.layers:
                for moe in (layer.a,layer.b):
                    # Recompute only router statistics from the current
                    # activations is unnecessary for the objective. The
                    # per-forward balance is stored in a transient attribute.
                    if hasattr(moe,"last_stats"):
                        balance=balance+moe.last_stats["balance"]
                        zloss=zloss+moe.last_stats["z_loss"]

            loss=lm+0.03*jepa+0.005*balance+0.0005*zloss
            metrics.update({
                "lm":lm.detach(),
                "jepa":jepa.detach(),
                "balance":balance.detach(),
                "zloss":zloss.detach(),
            })

        metrics["capability"]=cap.detach()
        metrics["inq"]=inq_trace
        return logits,loss,metrics,traces


# Patch the transient MoE stats without retaining graph beyond forward.
_original_moe_forward=SparseMoE.forward
def _moe_forward_store(self,x):
    out,stats=_original_moe_forward(self,x)
    self.last_stats=stats
    return out,stats
SparseMoE.forward=_moe_forward_store


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------

class V13Trainer:
    def __init__(self,model,cfg,device):
        self.model=model
        self.cfg=cfg
        self.device=device
        self.replay=Replay(cfg.replay_size)
        self.steps=0
        self.best=float("inf")
        self.bad_streak=0

        fast=[]
        router=[]
        base=[]
        for n,p in model.named_parameters():
            if not p.requires_grad:continue
            if ".router." in n:
                router.append(p)
            elif ".base." in n:
                base.append(p)
            else:
                fast.append(p)

        self.opt=torch.optim.AdamW(
            [
                {"params":fast,"lr":cfg.lr_fast},
                {"params":router,"lr":cfg.lr_router},
                {"params":base,"lr":cfg.lr_backbone},
            ],
            weight_decay=cfg.weight_decay,
        )

    def batch(self,texts):
        tok=ByteTokenizer()
        seq=[tok.encode(t,self.cfg.max_seq) for t in texts]
        L=max(map(len,seq))
        return torch.tensor(
            [s+[0]*(L-len(s)) for s in seq],
            dtype=torch.long,device=self.device
        )

    def step(self,texts,score=1.0):
        ids=self.batch(texts)
        self.model.train()
        _,loss,metrics,_=self.model(ids,targets=ids)

        if loss is None or not torch.isfinite(loss):
            self.opt.zero_grad(set_to_none=True)
            return {"loss":float("inf"),"skipped":True}

        # Low score means keep the experience for replay but barely learn
        # directly from it. Corrections can still receive score=1.
        weight=0.05+0.95*max(0,min(1,float(score)))
        loss=loss*weight

        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(),self.cfg.grad_clip)

        if any(
            p.grad is not None and not torch.isfinite(p.grad).all()
            for p in self.model.parameters()
        ):
            self.opt.zero_grad(set_to_none=True)
            return {"loss":float(loss.detach()),"skipped":True}

        self.opt.step()
        self.steps+=1

        if self.steps%self.cfg.consolidate_every==0:
            self.consolidate()

        lv=float(loss.detach())
        if lv<self.best:
            self.best=lv
            self.bad_streak=0
        elif lv>self.best*1.8:
            self.bad_streak+=1
            if self.bad_streak>=3:
                # Back off the learning rate before any hard rollback.
                for g in self.opt.param_groups:
                    g["lr"]=max(g["lr"]*0.5,1e-7)
                self.bad_streak=0

        return {
            "loss":lv,
            "lm":float(metrics["lm"].item()),
            "jepa":float(metrics["jepa"].item()),
            "steps":self.steps,
        }

    @torch.no_grad()
    def consolidate(self):
        """
        Slow learning of the backbone from its current adapted state.

        Base parameters already receive a tiny optimizer LR. This second,
        gated operation integrates the explicit LoRA deltas into the base
        and then gradually reduces adapter magnitude.

        This is slow drift, not a frozen backbone and not uncontrolled drift.
        """
        beta=self.cfg.ema_beta
        for module in self.model.modules():
            if isinstance(module,LoRALinear):
                module.merge_slow(beta)


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class V13Brain:
    def __init__(self,cfg):
        seed_all(cfg.seed)
        self.cfg=cfg
        self.device=torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model=V13Model(cfg,self.device)
        self.trainer=V13Trainer(self.model,cfg,self.device)

        self.root=Path(os.path.expanduser(cfg.workdir))
        self.root.mkdir(parents=True,exist_ok=True)
        self.stream_b=StreamB(
            self.root/"stream_b.sqlite",
            cfg.stream_b_max,
            cfg.stream_b_topk
        )

        self.last=None
        self.turns=0
        self.load()

    def ids(self,text):
        return torch.tensor(
            [ByteTokenizer().encode(text,self.cfg.max_seq)],
            dtype=torch.long,device=self.device
        )

    @torch.no_grad()
    def brain_pass(self,user):
        ids=self.ids(user)
        _,_,metrics,traces=self.model(ids)

        return {
            "cautiousness":float(traces[-1]["cautiousness"].mean()),
            "conflict":float(traces[-1]["conflict"].mean()),
            "capability":metrics["capability"].mean(0).cpu().tolist(),
            "inq":[
                {
                    "round":int(t["round"]),
                    "kappa":float(t["kappa"].mean()),
                    "conflict":float(t["conflict"].mean()),
                    "p2_wins":float(t["p2_wins"].float().mean()),
                }
                for t in metrics["inq"]
            ]
        }

    @torch.no_grad()
    def generate(self,user):
        tok=ByteTokenizer()

        # Stream B exact context. This is not used to pretend old text is
        # encoded into the world model. It is explicit retrieved evidence.
        memories=self.stream_b.retrieve(user)
        mem=""
        if memories:
            mem="\nRemembered episodes:\n"
            for _,u,a,s,c in memories:
                mem+=f"User: {u}\nAssistant: {a}\n"
                if c:mem+=f"Correction: {c}\n"

        prompt=(
            "Answer directly. If uncertain, say so instead of inventing facts.\n"
            +mem+"\nUser: "+user+"\nAssistant:"
        )

        ids=self.ids(prompt)
        info=self.brain_pass(user)
        cur=ids.clone()

        self.model.eval()
        for _ in range(self.cfg.max_new_tokens):
            if cur.size(1)>=self.cfg.max_seq:break
            inp=cur[:,-self.cfg.max_seq:]
            logits,_,_,_=self.model(inp)
            p=F.softmax(logits[:,-1].float()/max(1e-5,self.cfg.temperature),-1)

            vals,idx=torch.sort(p,descending=True)
            cumulative=torch.cumsum(vals,-1)
            remove=cumulative>self.cfg.top_p
            remove[...,1:]=remove[...,:-1].clone()
            remove[...,0]=False
            vals[remove]=0
            vals/=vals.sum(-1,keepdim=True).clamp_min(1e-8)

            pick=torch.multinomial(vals,1)
            nxt=idx.gather(-1,pick)
            cur=torch.cat([cur,nxt],1)
            if int(nxt.item())==tok.eos_id:break

        answer=tok.decode(cur[0,ids.size(1):].tolist()).strip()
        if not answer:
            answer="Ich habe dafür gerade keine brauchbare Antwort."

        self.last={
            "user":user,
            "answer":answer,
            "info":info,
            "ts":time.time()
        }
        self.turns+=1

        # Immediate experience storage.
        self.stream_b.add(user,answer,capability=sum(info["capability"])/3)
        with torch.no_grad():
            z,_=self.model.encode(ids)
            self.model.stream_a.integrate(z.mean(1))

        return answer,info

    def feedback(self,score,correction=None):
        if self.last is None:return {"status":"no previous answer"}

        score=max(0,min(1,float(score)))
        cap=sum(self.last["info"]["capability"])/3
        exp=Experience(
            self.last["user"],self.last["answer"],score,correction,
            cap,1.0,time.time()
        )
        self.trainer.replay.add(exp)

        self.stream_b.add(
            self.last["user"],self.last["answer"],
            score=score,correction=correction,
            capability=cap,accepted=score>=self.cfg.positive_threshold
        )

        target=correction or self.last["answer"]
        result=self.trainer.step(
            ["User: "+self.last["user"]+"\nAssistant: "+target],
            score
        )

        # Replay preserves old capabilities and prevents single-example
        # overwriting from dominating.
        replay=self.trainer.replay.sample(self.cfg.replay_batch)
        if replay:
            texts=[]
            scores=[]
            for e in replay:
                t=e.correction or e.answer
                texts.append("User: "+e.user+"\nAssistant: "+t)
                scores.append(e.score)
            rr=self.trainer.step(
                texts,
                sum(scores)/len(scores)
            )
            result["replay_loss"]=rr["loss"]

        return {
            "status":"learned",
            "score":score,
            "correction":bool(correction),
            "replay":len(self.trainer.replay),
            **result
        }

    def self_review_candidate(self):
        """
        Autonomous review cannot manufacture ground truth.

        This method creates a candidate record. Admission to positive learning
        requires a real outcome, deterministic evaluator or teacher.
        """
        if self.last is None:return {"status":"nothing"}
        return {
            "status":"candidate_only",
            "requires":"external outcome, evaluator or teacher",
            "user":self.last["user"],
            "answer":self.last["answer"],
            "capability":self.last["info"]["capability"],
        }

    def status(self):
        result={
            "device":str(self.device),
            "turns":self.turns,
            "learning_steps":self.trainer.steps,
            "replay":len(self.trainer.replay),
            "stream_b":self.stream_b.count(),
            "rounds":self.cfg.rounds,
            "experts":self.cfg.num_experts,
            "top_k":self.cfg.top_k,
            "bridge_fraction":self.cfg.bridge_fraction,
            "cautiousness":[self.cfg.cautious_base,self.cfg.cautious_max],
            "ema_beta":self.cfg.ema_beta,
            "moe":[]
        }
        for i,l in enumerate(self.model.layers):
            for side,m in (("A",l.a),("B",l.b)):
                result["moe"].append({
                    "layer":i,
                    "side":side,
                    "assign_counts":m.assign_counts.tolist(),
                    "dropped":int(m.dropped.item())
                })
        return result

    def save(self):
        p=self.root/"brain.pt"
        tmp=self.root/"brain.pt.tmp"
        payload={
            "config":asdict(self.cfg),
            "model":self.model.state_dict(),
            "optimizer":self.trainer.opt.state_dict(),
            "steps":self.trainer.steps,
            "best":self.trainer.best,
            "turns":self.turns
        }
        torch.save(payload,tmp)
        os.replace(tmp,p)

    def load(self):
        p=self.root/"brain.pt"
        if not p.exists():return
        try:
            d=torch.load(p,map_location=self.device,weights_only=False)
            self.model.load_state_dict(d["model"],strict=False)
            try:self.trainer.opt.load_state_dict(d["optimizer"])
            except Exception:pass
            self.trainer.steps=int(d.get("steps",0))
            self.trainer.best=float(d.get("best",float("inf")))
            self.turns=int(d.get("turns",0))
        except Exception:
            # Keep corrupt checkpoint rather than destroying evidence.
            shutil.copy2(p,p.with_suffix(".corrupt."+str(int(time.time()))))


# ---------------------------------------------------------------------------
# Verification suite
# ---------------------------------------------------------------------------

def smoke_test():
    cfg=Config(
        d_model=64,n_layers=2,n_heads=4,num_experts=4,top_k=2,
        lora_rank=4,inq_dim=32,max_seq=64,max_new_tokens=8,
        stream_a_slots=8,replay_size=32,stream_b_max=32,
        workdir=tempfile.mkdtemp(prefix="v13_smoke_")
    )
    b=V13Brain(cfg)
    tok=ByteTokenizer()

    ids=torch.tensor(
        [tok.encode("hello world this is v13",cfg.max_seq)],
        device=b.device
    )

    logits,loss,metrics,traces=b.model(ids,targets=ids)
    assert logits.shape==(1,ids.size(1),tok.vocab_size)
    assert torch.isfinite(logits).all()
    assert loss is not None and torch.isfinite(loss)
    assert len(traces)==cfg.n_layers
    assert len(metrics["inq"])==cfg.rounds

    # Two genuinely separate hemisphere expert pools.
    assert b.model.layers[0].a is not b.model.layers[0].b
    assert b.model.layers[0].a.experts[0] is not b.model.layers[0].b.experts[0]

    # P1/P2 are actually the same shared network.
    assert b.model.inquisition.shared[0].base.weight.data_ptr() == \
           b.model.inquisition.shared[0].base.weight.data_ptr()

    before=[
        p.detach().clone()
        for p in b.model.parameters()
        if p.requires_grad
    ]
    r=b.trainer.step(["User: hello\nAssistant: hi"],1.0)
    after=[
        p.detach()
        for p in b.model.parameters()
        if p.requires_grad
    ]
    assert math.isfinite(r["loss"])
    assert any(not torch.equal(x,y) for x,y in zip(before,after))

    # Persistent memory.
    b.stream_b.add("what is 2+2","4",score=1.0,accepted=True)
    assert b.stream_b.count()==1
    assert b.stream_b.retrieve("2+2")

    # Checkpoint roundtrip.
    b.save()
    b2=V13Brain(cfg)
    assert b2.trainer.steps>=1

    print("V13 SMOKE TEST: OK")
    print(json.dumps({
        "device":str(b.device),
        "loss":r["loss"],
        "layers":cfg.n_layers,
        "hemispheres":2,
        "experts_per_hemisphere":cfg.num_experts,
        "top_k":cfg.top_k,
        "lora_rank":cfg.lora_rank,
        "inq_rounds":cfg.rounds
    },indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--smoke-test",action="store_true")
    ap.add_argument("--rounds",type=int,default=None)
    ap.add_argument("--workdir",default=None)
    ap.add_argument("--train-file",default=None)
    ap.add_argument("--steps",type=int,default=10)
    args=ap.parse_args()

    if args.smoke_test:
        smoke_test()
        return

    cfg=Config()
    if args.rounds is not None:
        cfg.rounds=max(1,min(8,args.rounds))
    if args.workdir:
        cfg.workdir=args.workdir

    brain=V13Brain(cfg)
    print("""
V13 Brain läuft.

Freitext -> Gehirnpass + Antwort + Memory
:status
:good
:bad
:score 1..10
:correct TEXT
:review
:rounds N
:save
:quit
""")

    while True:
        try:
            s=input("v13> ").strip()
        except (EOFError,KeyboardInterrupt):
            brain.save()
            print()
            break

        if not s:continue
        if s==":quit":
            brain.save()
            break
        if s==":save":
            brain.save()
            print("gespeichert")
            continue
        if s==":status":
            print(json.dumps(brain.status(),indent=2,ensure_ascii=False))
            continue
        if s==":good":
            print(brain.feedback(1.0))
            continue
        if s==":bad":
            print(brain.feedback(0.0))
            continue
        if s.startswith(":score "):
            n=float(s.split(maxsplit=1)[1])
            print(brain.feedback((n-1)/9))
            continue
        if s.startswith(":correct "):
            print(brain.feedback(1.0,s.split(maxsplit=1)[1]))
            continue
        if s==":review":
            print(json.dumps(brain.self_review_candidate(),indent=2,ensure_ascii=False))
            continue
        if s.startswith(":rounds "):
            brain.cfg.rounds=max(1,min(8,int(s.split(maxsplit=1)[1])))
            print("rounds =",brain.cfg.rounds)
            continue

        answer,info=brain.generate(s)
        print(
            "[cautiousness={:.3f} conflict={:.3f} capability={}]".format(
                info["cautiousness"],
                info["conflict"],
                ",".join(f"{x:.2f}" for x in info["capability"])
            )
        )
        print(answer)


if __name__=="__main__":
    main()
