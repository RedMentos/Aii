#!/usr/bin/env python3
"""WP-BP1: train and evaluate a LoRA that makes C3 (LFM2.5-350M master) consume the bodies' offers.

  train  --master DIR --out DIR --mode offers|no_offers [--per-family N --epochs E --seed S]
  eval   --master DIR --adapter DIR|none --out FILE [--per-family N --seed S]

`no_offers` trains the SAME questions and answers with the offer layer removed (control: memorisation/guessing, not use).
Eval runs one test set (held-out templates) under offers real / removed / shuffled (offers of another item) and, for
an adapter, also with the adapter off (base). Reuses the master-fp32 LoRA recipe of v13/lora_trainer.py (targets, no q/k);
evidence level: HF fp32 master on Linux CPU, not the quantized GGUF on the Redmi.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13 import offer_consumer as oc
from v13.lora_trainer import DEFAULT_TARGETS

# Generic prompts for self-distillation replay (base model's own answers); disjoint from specs/drift-probes.json.
GENERIC = ['What is the capital of Italy?', 'Name three primary colors.', 'How many minutes are in two hours?', 'Explain what a noun is in one sentence.',
           'What is 12 plus 30?', 'Translate "thank you" into French.', 'Which planet is closest to the sun?', 'Give one tip for sleeping well.',
           'What does a thermometer measure?', 'Say hello briefly.', 'Spell the word "garden" backwards.', 'Is a tomato a fruit or a vegetable?',
           'What is the opposite of "heavy"?', 'How many legs does a spider have?', 'Name a river in Germany.', 'What is the past tense of "run"?',
           'Write a short greeting for a friend.', 'What color do you get by mixing blue and yellow?', 'How many days are in a week?',
           'Explain what rain is in one sentence.', 'What is half of 50?', 'Name one season of the year.', 'What language is spoken in Spain?',
           'Why do we use umbrellas?', 'What is the plural of "child"?', 'How many months have 30 days? Answer briefly.', 'What is a synonym for "big"?',
           'What is 9 times 8?', 'Name a mammal that lives in the sea.', 'What do bees make?']


def load(master, adapter=None, trainable=False, rank=16, alpha=32):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(4)
    tok = AutoTokenizer.from_pretrained(master)
    model = AutoModelForCausalLM.from_pretrained(master, dtype=torch.float32)
    if trainable:
        from peft import LoraConfig, get_peft_model
        model = get_peft_model(model, LoraConfig(r=rank, lora_alpha=alpha, lora_dropout=0., target_modules=list(DEFAULT_TARGETS), bias='none'))
    elif adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return torch, tok, model


def encode(tok, msgs, target):
    p = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    pid = tok(p, add_special_tokens=False)['input_ids']
    tid = tok(target + '<|im_end|>', add_special_tokens=False)['input_ids']
    return pid + tid, [-100] * len(pid) + tid


def generate(torch, tok, model, msg_lists, max_new=48, batch=16):
    out = []
    tok.padding_side = 'left'
    for i in range(0, len(msg_lists), batch):
        prompts = [tok.apply_chat_template(m, add_generation_prompt=True, tokenize=False) for m in msg_lists[i:i + batch]]
        enc = tok(prompts, return_tensors='pt', padding=True, add_special_tokens=False)
        with torch.no_grad():
            g = model.generate(**enc, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.pad_token_id)
        out += [tok.decode(r[enc['input_ids'].shape[1]:], skip_special_tokens=True).strip() for r in g]
    return out


def cmd_train(a):
    t0 = time.time()
    torch, tok, model = load(a.master, trainable=True)
    items = oc.build(a.seed, 0, a.per_family)
    data = []
    for it in items:
        msgs = oc.messages(it, [] if a.mode == 'no_offers' else None)
        data.append(encode(tok, msgs, it['target']))
    # self-distillation replay on generic prompts: the base model's own greedy answers (adapter is still zero-initialised)
    rng = random.Random(a.seed)
    gen = rng.sample(GENERIC, min(len(GENERIC), max(4, len(items) // 10)))
    gm = [[{'role': 'system', 'content': oc.system_prompt([])}, {'role': 'user', 'content': q}] for q in gen]
    with model.disable_adapter():
        ga = generate(torch, tok, model, gm, max_new=40)
    data += [encode(tok, m, x) for m, x in zip(gm, ga)]
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.)
    steps = a.epochs * ((len(data) + a.batch - 1) // a.batch)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1., (s + 1) / 10) * max(.05, 1 - s / steps))
    g = torch.Generator().manual_seed(a.seed)
    model.train()
    step = 0
    hist = []
    for ep in range(a.epochs):
        order = torch.randperm(len(data), generator=g).tolist()
        for i in range(0, len(order), a.batch):
            chunk = [data[k] for k in order[i:i + a.batch]]
            n = max(len(c[0]) for c in chunk)
            ids = torch.tensor([c[0] + [tok.pad_token_id] * (n - len(c[0])) for c in chunk])
            lab = torch.tensor([c[1] + [-100] * (n - len(c[1])) for c in chunk])
            att = torch.tensor([[1] * len(c[0]) + [0] * (n - len(c[0])) for c in chunk])
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step(); opt.zero_grad(); step += 1
            hist.append(round(float(loss.detach()), 4))
            if step % 5 == 0 or step == 1:
                print('step %d/%d loss %.4f %.0fs' % (step, steps, hist[-1], time.time() - t0), flush=True)
            if a.max_steps and step >= a.max_steps:
                break
        if a.max_steps and step >= a.max_steps:
            break
    model.save_pretrained(a.out)
    Path(a.out, 'train_report.json').write_text(json.dumps({'mode': a.mode, 'seed': a.seed, 'per_family': a.per_family, 'epochs': a.epochs, 'lr': a.lr,
                                                           'batch': a.batch, 'examples': len(data), 'replay': len(gm), 'steps': step, 'loss_first': hist[:3], 'loss_last': hist[-5:],
                                                           'seconds': round(time.time() - t0), 'revision': oc.REVISION}, indent=1))
    print('saved', a.out, 'steps', step, 'seconds', round(time.time() - t0))


def cmd_eval(a):
    t0 = time.time()
    adapter = None if a.adapter == 'none' else a.adapter
    torch, tok, model = load(a.master, adapter)
    items = oc.build(a.seed, 1, a.per_family)
    rng = random.Random(a.seed + 99)
    shuf = [rng.choice([x for x in items if x['offers'] and x is not it] or items)['offers'] for it in items]
    arms = {'offers': [oc.messages(i) for i in items], 'removed': [oc.messages(i, []) for i in items],
            'shuffled': [oc.messages(i, o) for i, o in zip(items, shuf)]}
    res = {'adapter': a.adapter, 'seed': a.seed, 'n': len(items), 'revision': oc.REVISION, 'arms': {}, 'answers': {}}
    runs = [('adapter' if adapter else 'base', None)] + ([('base_adapter_off', 'off')] if adapter and not a.skip_base else [])
    for tag, mode in runs:
        for arm, ml in arms.items():
            if mode == 'off':
                with model.disable_adapter():
                    ans = generate(torch, tok, model, ml)
            else:
                ans = generate(torch, tok, model, ml)
            key = tag + ':' + arm
            res['arms'][key] = oc.summarize(items, ans)
            res['answers'][key] = ans
            print(key, res['arms'][key]['overall'], res['arms'][key]['wrong_commit'], res['arms'][key]['per_family'], '%.0fs' % (time.time() - t0), flush=True)
    res['items'] = [{k: it[k] for k in ('id', 'family', 'must', 'forbid', 'hedge', 'abstain')} for it in items]
    if adapter:  # general drift on the frozen probe set: teacher-forced KL(base || adapter) over the base's own 24-token continuation
        probes = [p['prompt'] for p in json.loads((Path(__file__).resolve().parents[1] / 'specs/drift-probes.json').read_text())['probes']]
        pm = [[{'role': 'system', 'content': oc.system_prompt([])}, {'role': 'user', 'content': q}] for q in probes]
        with model.disable_adapter():
            off = generate(torch, tok, model, pm, max_new=24)
        on = generate(torch, tok, model, pm, max_new=24)
        kls = []
        for m, cont in zip(pm, off):
            pid = tok(tok.apply_chat_template(m, add_generation_prompt=True, tokenize=False), add_special_tokens=False)['input_ids']
            cid = tok(cont, add_special_tokens=False)['input_ids']
            ids = torch.tensor([pid + cid])
            with torch.no_grad():
                with model.disable_adapter():
                    lb = torch.log_softmax(model(ids).logits[0, len(pid) - 1:-1].float(), -1)
                la = torch.log_softmax(model(ids).logits[0, len(pid) - 1:-1].float(), -1)
            kls.append(float((lb.exp() * (lb - la)).sum(-1).mean()))
        res['drift'] = {'n': len(probes), 'mean_kl': round(sum(kls) / len(kls), 5), 'max_kl': round(max(kls), 5), 'identical_greedy': sum(x == y for x, y in zip(on, off)), 'on': on, 'off': off}
        print('drift mean KL', res['drift']['mean_kl'], 'identical', res['drift']['identical_greedy'], '/', len(probes))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print('wrote', a.out, 'seconds', round(time.time() - t0))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('train')
    t.add_argument('--master', required=True); t.add_argument('--out', required=True)
    t.add_argument('--mode', choices=['offers', 'no_offers'], default='offers')
    t.add_argument('--per-family', type=int, default=60); t.add_argument('--epochs', type=int, default=2)
    t.add_argument('--seed', type=int, default=1); t.add_argument('--lr', type=float, default=3e-4)
    t.add_argument('--batch', type=int, default=8); t.add_argument('--max-steps', type=int, default=0)
    e = sub.add_parser('eval')
    e.add_argument('--master', required=True); e.add_argument('--adapter', default='none'); e.add_argument('--out', required=True)
    e.add_argument('--per-family', type=int, default=30); e.add_argument('--seed', type=int, default=101); e.add_argument('--skip-base', action='store_true')
    a = ap.parse_args()
    {'train': cmd_train, 'eval': cmd_eval}[a.cmd](a)
