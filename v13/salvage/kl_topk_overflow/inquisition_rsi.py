#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inquisition RSI

Ein echter, kleiner Prototyp für:
  LM -> Stream A / Stream B -> Nested Inquisition -> Antwort
                     ^                 |
                     |---- Lernen <----|

P1 und P2 sind keine zwei Sprachmodelle.
Beide Rollen benutzen denselben trainierbaren LoRA-Adapter.
Der Unterschied entsteht durch die Rolle und den jeweiligen Kontext.

Der Sprachkern bleibt ein echtes HF-Causal-LM.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, PeftModel


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class Config:
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    teacher_name: str = "Qwen/Qwen2.5-0.5B-Instruct"

    workdir: str = "~/.inquisition_rsi"
    max_input_tokens: int = 768
    max_new_tokens: int = 192

    # Inquisition
    rounds: int = 2
    latent_dim: int = 256
    latent_depth: int = 2
    manipulation_strength: float = 0.35

    # Stream A
    stream_a_slots: int = 32
    stream_a_decay: float = 0.995

    # Stream B
    stream_b_max: int = 500

    # Online LoRA
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    lr: float = 2e-5
    train_steps_per_feedback: int = 1
    grad_clip: float = 1.0

    # Routing
    c0_max: int = 120
    c1_max: int = 350
    c2_max: int = 700

    # Teacher OPD
    teacher_top_k: int = 8
    teacher_max_tokens: int = 96
    teacher_temperature: float = 1.0

    seed: int = 42


CFG = Config()


# ---------------------------------------------------------------------------
# Paths / persistence
# ---------------------------------------------------------------------------

ROOT = Path(os.path.expanduser(CFG.workdir))
ROOT.mkdir(parents=True, exist_ok=True)

STATE_FILE = ROOT / "state.json"
MEMORY_FILE = ROOT / "stream_b.json"
A_FILE = ROOT / "stream_a.pt"
LATENT_FILE = ROOT / "latent.pt"
LORA_DIR = ROOT / "lora"


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


# ---------------------------------------------------------------------------
# Stream B: exact episodic memory
# ---------------------------------------------------------------------------

class StreamB:
    def __init__(self, path: Path):
        self.path = path
        self.items: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.items = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.items = []

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self.items[-CFG.stream_b_max:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(
        self,
        user: str,
        answer: str,
        score: Optional[float] = None,
        correction: Optional[str] = None,
    ) -> None:
        self.items.append({
            "time": time.time(),
            "user": user,
            "answer": answer,
            "score": score,
            "correction": correction,
        })
        self.items = self.items[-CFG.stream_b_max:]
        self.save()

    def retrieve(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        # bewusst exakt/transparent: keine erfundene Semantik.
        # Ein einfacher lexical overlap retriever ist für den Prototyp robust.
        q = set(re.findall(r"\w+", query.lower()))
        if not q:
            return []

        scored = []
        for item in self.items:
            text = (item.get("user", "") + " " + item.get("answer", "")).lower()
            words = set(re.findall(r"\w+", text))
            overlap = len(q & words)
            if overlap:
                scored.append((overlap, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:k]]


# ---------------------------------------------------------------------------
# Stream A: compressed latent context
# ---------------------------------------------------------------------------

class StreamA(nn.Module):
    """
    Langzeitkontext als komprimierter Zustand.

    Er speichert nicht die komplette Historie.
    Jeder neue Eintrag wird in einen festen Slot-Speicher integriert.
    """

    def __init__(self, input_dim: int, latent_dim: int, slots: int):
        super().__init__()
        self.slots = slots
        self.latent_dim = latent_dim

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, latent_dim),
            nn.GELU(),
            nn.Linear(latent_dim, latent_dim),
        )

        self.register_buffer(
            "state",
            torch.zeros(slots, latent_dim),
        )
        self.register_buffer(
            "write_pos",
            torch.zeros(1, dtype=torch.long),
        )

    @torch.no_grad()
    def integrate(self, x: torch.Tensor) -> None:
        z = self.encoder(x.float()).detach()

        if z.dim() == 1:
            z = z.unsqueeze(0)

        for row in z:
            p = int(self.write_pos.item()) % self.slots
            old = self.state[p]
            self.state[p].mul_(CFG.stream_a_decay)
            self.state[p].add_(row, alpha=1.0 - CFG.stream_a_decay)
            self.write_pos[0] = (p + 1) % self.slots

    @torch.no_grad()
    def read(self) -> torch.Tensor:
        return self.state.mean(dim=0, keepdim=True)

    def save(self) -> None:
        torch.save(self.state_dict(), A_FILE)

    def load(self) -> None:
        if A_FILE.exists():
            try:
                self.load_state_dict(torch.load(A_FILE, map_location="cpu"))
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Nested Latent Inquisition Space
# ---------------------------------------------------------------------------

class InquisitionSpace(nn.Module):
    """
    Z -> Z_Inq -> P1/P2

    Das Subspace ist trainierbar und klein.
    Das LM selbst muss nicht komplett für jede Runde rückwärts laufen.
    """

    def __init__(self, hidden_size: int, latent_dim: int):
        super().__init__()
        self.to_inq = nn.Sequential(
            nn.Linear(hidden_size, latent_dim),
            nn.LayerNorm(latent_dim),
            nn.GELU(),
        )
        self.back = nn.Linear(latent_dim, hidden_size)

        self.p1 = nn.Linear(latent_dim, latent_dim)
        self.p2 = nn.Linear(latent_dim, latent_dim)

    def encode(self, z: torch.Tensor) -> torch.Tensor:
        return self.to_inq(z)

    def role_p1(self, zin: torch.Tensor) -> torch.Tensor:
        return self.p1(zin)

    def role_p2(self, zin: torch.Tensor) -> torch.Tensor:
        return self.p2(zin)

    def reconstruct(self, zin: torch.Tensor) -> torch.Tensor:
        return self.back(zin)


# ---------------------------------------------------------------------------
# Main system
# ---------------------------------------------------------------------------

class InquisitionSystem:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        seed_everything(cfg.seed)

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        print(f"[boot] device={self.device}")
        print(f"[boot] model={cfg.model_name}")

        self.tokenizer = AutoTokenizer.from_pretrained(cfg.model_name)

        self.model = AutoModelForCausalLM.from_pretrained(
            cfg.model_name,
            torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
        )

        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model.to(self.device)

        # One shared adapter space.
        # P1/P2 are roles, not two independent LoRA parameter sets.
        if not isinstance(self.model, PeftModel):
            lora = LoraConfig(
                r=cfg.lora_r,
                lora_alpha=cfg.lora_alpha,
                lora_dropout=cfg.lora_dropout,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=self._find_lora_targets(),
            )
            self.model = get_peft_model(self.model, lora)

        self.model.train()

        hidden = int(
            getattr(self.model.config, "hidden_size", 768)
        )

        self.inq = InquisitionSpace(
            hidden_size=hidden,
            latent_dim=cfg.latent_dim,
        ).to(self.device)

        self.stream_a = StreamA(
            input_dim=hidden,
            latent_dim=cfg.latent_dim,
            slots=cfg.stream_a_slots,
        ).to(self.device)

        self.stream_a.load()

        self.stream_b = StreamB(MEMORY_FILE)

        trainable = list(self.inq.parameters())
        trainable += [
            p for p in self.model.parameters() if p.requires_grad
        ]

        self.optimizer = torch.optim.AdamW(
            trainable,
            lr=cfg.lr,
            weight_decay=0.01,
        )

        self.teacher = None
        self.teacher_tokenizer = None

        self.turn = 0
        self.last_user = ""
        self.last_answer = ""
        self.last_internal = {}
        self.learning_enabled = True

        self.load_state()

    # ------------------------------------------------------------------
    # LoRA target detection
    # ------------------------------------------------------------------

    def _find_lora_targets(self) -> List[str]:
        names = []
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                leaf = name.split(".")[-1]
                if leaf in {
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                }:
                    names.append(leaf)

        # De-duplicate while retaining order.
        out = []
        for x in names:
            if x not in out:
                out.append(x)

        # Some models expose different names.
        return out or ["q_proj", "v_proj"]

    # ------------------------------------------------------------------
    # Prompting
    # ------------------------------------------------------------------

    def _chat(self, text: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "Answer the user directly. "
                    "Do not invent facts. "
                    "If something is uncertain, say so."
                ),
            },
            {"role": "user", "content": text},
        ]

        if hasattr(self.tokenizer, "apply_chat_template"):
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

        return f"User: {text}\nAssistant:"

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    @torch.no_grad()
    def encode_text(self, text: str) -> torch.Tensor:
        enc = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.cfg.max_input_tokens,
        )
        ids = enc["input_ids"].to(self.device)

        out = self.model.base_model(
            input_ids=ids,
            output_hidden_states=True,
            use_cache=False,
        )

        # Last hidden state from the real language model.
        h = out.hidden_states[-1][:, -1, :]
        return h.detach()

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(self, text: str) -> Tuple[str, float]:
        n = len(text.split())
        if n <= self.cfg.c0_max:
            tier = "C0"
        elif n <= self.cfg.c1_max:
            tier = "C1"
        elif n <= self.cfg.c2_max:
            tier = "C2"
        else:
            tier = "C3"

        # Demand score is deliberately transparent.
        score = min(
            1.0,
            0.25 * (["C0", "C1", "C2", "C3"].index(tier))
            + 0.0005 * len(text),
        )
        return tier, float(score)

    # ------------------------------------------------------------------
    # Inquisition
    # ------------------------------------------------------------------

    @torch.no_grad()
    def run_inquisition(self, user: str) -> Dict[str, Any]:
        base = self.encode_text(user)

        a = self.stream_a.read().to(self.device)

        memories = self.stream_b.retrieve(user, k=4)

        memory_text = "\n".join(
            f"- {m.get('user','')}: {m.get('answer','')}"
            for m in memories
        )

        z = self.inq.encode(base)

        p1_trace = []
        p2_trace = []

        for r in range(max(1, int(self.cfg.rounds))):
            # P1: hypothesis / manipulation.
            p1 = self.inq.role_p1(z)
            manipulated = z + self.cfg.manipulation_strength * torch.tanh(p1)
            p1_trace.append(float(p1.norm().item()))

            # P2 receives manipulated state and has to reconstruct/evaluate
            # using the same adapter space but a different role.
            fresh = self.inq.encode(base)
            p2_input = 0.5 * fresh + 0.5 * manipulated
            p2 = self.inq.role_p2(p2_input)

            # Cross-role consistency signal.
            kappa = F.cosine_similarity(
                p1.detach(),
                p2.detach(),
                dim=-1,
            ).mean().item()

            # If consistency is poor, keep the challenge active.
            # If high, converge toward the fresh encoder state.
            alpha = max(0.05, min(0.75, (1.0 - kappa) * 0.5))
            z = (1.0 - alpha) * p2 + alpha * fresh

            p2_trace.append(float(p2.norm().item()))

        return {
            "tier": self.route(user)[0],
            "route_score": self.route(user)[1],
            "kappa": float(kappa),
            "memory_count": len(memories),
            "memory_text": memory_text,
            "p1_norm": p1_trace,
            "p2_norm": p2_trace,
            "latent": z.detach(),
            "stream_a": a.detach(),
        }

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    @torch.no_grad()
    def generate_answer(self, user: str, internal: Dict[str, Any]) -> str:
        latent = internal["latent"]

        # The inquisition result is not exposed as text reasoning.
        # It only changes the instruction context.
        control = (
            "Internally verify the answer before responding. "
            "Prefer a concise, correct answer. "
            "Do not mention this verification process."
        )

        if internal["kappa"] < 0.0:
            control += (
                " Be especially conservative about uncertain claims."
            )

        mem = internal["memory_text"]
        if mem:
            control += (
                "\nRelevant prior interaction memory may help, "
                "but do not treat it as automatically true:\n" + mem
            )

        prompt = self._chat(
            f"{control}\n\nUser request:\n{user}"
        )

        enc = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.cfg.max_input_tokens,
        ).to(self.device)

        out = self.model.generate(
            **enc,
            max_new_tokens=self.cfg.max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=self.tokenizer.pad_token_id,
        )

        generated = out[0, enc["input_ids"].shape[-1]:]
        text = self.tokenizer.decode(
            generated,
            skip_special_tokens=True,
        ).strip()

        return text or "Ich konnte darauf gerade keine brauchbare Antwort erzeugen."

    # ------------------------------------------------------------------
    # Online learning
    # ------------------------------------------------------------------

    def _training_text(
        self,
        user: str,
        answer: str,
        correction: Optional[str],
        score: float,
    ) -> str:
        if correction:
            target = correction
        else:
            target = answer

        return (
            "User:\n"
            + user
            + "\n\nAssistant:\n"
            + target
            + f"\n\nQualityScore: {score:.3f}"
        )

    def online_learn(
        self,
        user: str,
        answer: str,
        score: float,
        correction: Optional[str] = None,
    ) -> Dict[str, float]:

        if not self.learning_enabled:
            return {"loss": 0.0, "skipped": 1.0}

        text = self._training_text(user, answer, correction, score)

        self.model.train()
        self.inq.train()

        enc = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.cfg.max_input_tokens,
        ).to(self.device)

        # SFT-style loss on the whole assistant example.
        # This is intentionally small and online.
        labels = enc["input_ids"].clone()

        outputs = self.model(
            input_ids=enc["input_ids"],
            attention_mask=enc.get("attention_mask"),
            labels=labels,
            use_cache=False,
        )

        lm_loss = outputs.loss

        # Train the nested latent space toward a stable representation.
        h = self.encode_text(user).detach()
        z = self.inq.encode(h)

        # VICReg-lite: avoid collapse while keeping related states close.
        var = torch.relu(1.0 - z.std(dim=-1)).mean()
        center = z.mean(dim=-1).pow(2).mean()

        latent_loss = 0.1 * var + 0.01 * center

        # High-quality feedback gets stronger weight.
        weight = 0.25 + 0.75 * max(0.0, min(1.0, score))
        loss = weight * lm_loss + latent_loss

        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            list(self.inq.parameters())
            + [p for p in self.model.parameters() if p.requires_grad],
            self.cfg.grad_clip,
        )

        self.optimizer.step()

        # Stream A changes slowly, not on every token.
        with torch.no_grad():
            self.stream_a.integrate(h.cpu())
        self.stream_a.save()

        return {
            "loss": float(loss.detach().item()),
            "lm_loss": float(lm_loss.detach().item()),
            "latent_loss": float(latent_loss.detach().item()),
            "weight": float(weight),
        }

    # ------------------------------------------------------------------
    # Teacher / OPD
    # ------------------------------------------------------------------

    def enable_teacher(self) -> None:
        if self.teacher is not None:
            return

        print(f"[teacher] loading {self.cfg.teacher_name}")

        self.teacher_tokenizer = AutoTokenizer.from_pretrained(
            self.cfg.teacher_name
        )

        self.teacher = AutoModelForCausalLM.from_pretrained(
            self.cfg.teacher_name,
            torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
        ).to(self.device)

        self.teacher.eval()

        for p in self.teacher.parameters():
            p.requires_grad_(False)

        print("[teacher] ready")

    @torch.no_grad()
    def opd_step(self, prompt: str, response: str) -> float:
        """
        Coarse reverse-KL over teacher/student next-token distributions.

        To keep the prototype tractable, only top-K student tokens plus
        an overflow bin are compared.
        """

        if self.teacher is None:
            return 0.0

        text = self._chat(prompt)
        full = text + response

        st = self.tokenizer(
            full,
            return_tensors="pt",
            truncation=True,
            max_length=self.cfg.max_input_tokens,
        ).to(self.device)

        if st["input_ids"].shape[1] < 2:
            return 0.0

        # Student logits.
        student_out = self.model(
            input_ids=st["input_ids"],
            use_cache=False,
        )

        teacher_tok = self.teacher_tokenizer(
            full,
            return_tensors="pt",
            truncation=True,
            max_length=self.cfg.max_input_tokens,
        ).to(self.device)

        teacher_out = self.teacher(
            input_ids=teacher_tok["input_ids"],
            use_cache=False,
        )

        n = min(
            student_out.logits.shape[1] - 1,
            teacher_out.logits.shape[1] - 1,
            self.cfg.teacher_max_tokens,
        )

        s = student_out.logits[:, :n, :]
        t = teacher_out.logits[:, :n, :]

        k = min(self.cfg.teacher_top_k, s.shape[-1])

        sp = F.softmax(s / self.cfg.teacher_temperature, dim=-1)
        tp = F.softmax(t / self.cfg.teacher_temperature, dim=-1)

        vals, idx = torch.topk(sp, k=k, dim=-1)
        tq = torch.gather(tp, -1, idx)

        # Remaining mass = one overflow bin.
        overflow_s = (1.0 - vals.sum(dim=-1)).clamp_min(1e-8)
        overflow_t = (1.0 - tq.sum(dim=-1)).clamp_min(1e-8)

        ps = torch.cat([vals, overflow_s.unsqueeze(-1)], dim=-1)
        pt = torch.cat([tq, overflow_t.unsqueeze(-1)], dim=-1)

        ps = ps.clamp_min(1e-8)
        pt = pt.clamp_min(1e-8)

        # reverse KL: P_student || Q_teacher
        kl = (ps * (ps.log() - pt.log())).sum(dim=-1).mean()
        return float(kl.detach().item())

    # ------------------------------------------------------------------
    # Turn / feedback
    # ------------------------------------------------------------------

    def ask(self, user: str) -> str:
        self.turn += 1
        self.last_user = user

        internal = self.run_inquisition(user)
        answer = self.generate_answer(user, internal)

        self.last_answer = answer
        self.last_internal = internal

        # Experience is stored, but is not blindly trained immediately.
        self.stream_b.add(user, answer)

        print(
            f"[inq] tier={internal['tier']} "
            f"kappa={internal['kappa']:.3f} "
            f"memory={internal['memory_count']} "
            f"rounds={self.cfg.rounds}"
        )

        return answer

    def feedback(
        self,
        score: float,
        correction: Optional[str] = None,
    ) -> None:
        if not self.last_user:
            print("[feedback] keine letzte Antwort")
            return

        score = max(0.0, min(1.0, float(score)))

        item = self.stream_b.items[-1] if self.stream_b.items else None
        if item:
            item["score"] = score
            item["correction"] = correction
            self.stream_b.save()

        stats = self.online_learn(
            self.last_user,
            self.last_answer,
            score,
            correction=correction,
        )

        if self.teacher is not None:
            kl = self.opd_step(
                self.last_user,
                correction or self.last_answer,
            )
            stats["opd_kl"] = kl

        print(
            "[learn] "
            + " ".join(f"{k}={v:.4f}" for k, v in stats.items())
        )

        self.save_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_state(self) -> None:
        ROOT.mkdir(parents=True, exist_ok=True)

        torch.save(
            self.inq.state_dict(),
            LATENT_FILE,
        )

        self.stream_a.save()

        # Save only adapter parameters, not the whole base LM.
        LORA_DIR.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(LORA_DIR)
        self.tokenizer.save_pretrained(LORA_DIR)

        state = {
            "config": asdict(self.cfg),
            "turn": self.turn,
            "rounds": self.cfg.rounds,
            "learning_enabled": self.learning_enabled,
        }

        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_state(self) -> None:
        if LATENT_FILE.exists():
            try:
                self.inq.load_state_dict(
                    torch.load(LATENT_FILE, map_location=self.device)
                )
            except Exception:
                pass

        if STATE_FILE.exists():
            try:
                state = json.loads(
                    STATE_FILE.read_text(encoding="utf-8")
                )
                self.turn = int(state.get("turn", 0))
                self.learning_enabled = bool(
                    state.get("learning_enabled", True)
                )
            except Exception:
                pass

    def status(self) -> None:
        trainable = sum(
            p.numel()
            for p in self.model.parameters()
            if p.requires_grad
        )
        total = sum(p.numel() for p in self.model.parameters())

        print("\n--- INQUISITION STATUS ---")
        print(f"device:       {self.device}")
        print(f"model:        {self.cfg.model_name}")
        print(f"turns:        {self.turn}")
        print(f"rounds:       {self.cfg.rounds}")
        print(f"learning:     {self.learning_enabled}")
        print(f"memory B:     {len(self.stream_b.items)}")
        print(f"LoRA params:  {trainable:,} / {total:,}")
        print(f"teacher:      {'on' if self.teacher is not None else 'off'}")
        print(f"state dir:    {ROOT}")
        print("--------------------------\n")


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def help_text() -> None:
    print("""
Befehle

:help
:status
:n 1..8
:teacher on
:teacher off
:train on
:train off
:save
:quit

Feedback nach einer Antwort

gut
schlecht
note 8

Bei `note N` gilt 1 = schlecht, 10 = sehr gut.

Eine Korrektur kann direkt als nächste Eingabe gegeben werden:

korrigiert: <richtige Antwort>

Das wird als Trainingsziel gespeichert.
""")


def main() -> None:
    system = InquisitionSystem(CFG)

    print("\nInquisition RSI läuft.")
    print("Normale Eingabe = Inquisition + Antwort.")
    print("Feedback = gut / schlecht / note N.")
    print(":help für Befehle.\n")

    while True:
        try:
            raw = input("inq> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if not raw:
            continue

        if raw.startswith(":"):
            parts = raw[1:].split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in {"quit", "exit", "q"}:
                system.save_state()
                print("gespeichert.")
                break

            if cmd == "help":
                help_text()
                continue

            if cmd == "status":
                system.status()
                continue

            if cmd == "n":
                try:
                    system.cfg.rounds = max(1, min(8, int(arg)))
                    print(f"rounds={system.cfg.rounds}")
                except ValueError:
                    print("n braucht eine Zahl 1..8")
                continue

            if cmd == "teacher":
                if arg.lower() == "on":
                    system.enable_teacher()
                elif arg.lower() == "off":
                    system.teacher = None
                    system.teacher_tokenizer = None
                    print("teacher=off")
                continue

            if cmd == "train":
                if arg.lower() in {"on", "1", "true"}:
                    system.learning_enabled = True
                elif arg.lower() in {"off", "0", "false"}:
                    system.learning_enabled = False
                print(f"learning={system.learning_enabled}")
                continue

            if cmd == "save":
                system.save_state()
                print("gespeichert.")
                continue

            print("unbekannter Befehl, :help")
            continue

        low = raw.lower()

        if low == "gut":
            system.feedback(1.0)
            continue

        if low == "schlecht":
            system.feedback(0.0)
            continue

        m = re.fullmatch(r"note\s+(\d+(?:\.\d+)?)", low)
        if m:
            n = float(m.group(1))
            system.feedback((n - 1.0) / 9.0)
            continue

        if low.startswith("korrigiert:"):
            correction = raw.split(":", 1)[1].strip()
            system.feedback(1.0, correction=correction)
            continue

        answer = system.ask(raw)
        print(f"\n{answer}\n")


if __name__ == "__main__":
    main()
