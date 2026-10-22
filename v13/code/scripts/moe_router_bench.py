#!/usr/bin/env python3
"""WP-N11 real-model bench: router stability (B3-H6) and shared pre-router
forgetting (§16.2.1, §24.19, §91) on a real sparse MoE body.

Isolated candidate: reads a HF checkpoint with torch/transformers in the cloud,
writes router captures through `moe_router_monitor`. No runtime file, spec or
store is touched; nothing is promoted. Phone runner (llama.cpp) taps are a
separate later step.

Parts
  calib   receiver-native baseline variation: same text after two neutral
          preambles P0/P1/P2 (identical text tokens).
  latent  B3-H6 alpha grid: a sender latent (mean residual of a sender text,
          L1-style message) or a random direction of the same norm is added to
          the receiver residual at one layer; router metrics + old-task loss
          delta + answer-NLL utility vs NONE and EXACT text.
  update  §16.2.1/§91: short continual updates on new facts limited to one
          component group (shared attention+norms / router / experts) or all
          together, in a fixed layer window; monitor on the old task plus
          restoration ablation for attribution.
"""
import argparse
import hashlib
import json
import math
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import moe_router_monitor as M  # noqa: E402

OLD_EN = [
    "The river flows slowly through the valley, past old stone bridges and quiet farms where cows graze in the morning light.",
    "To bake simple bread you mix flour, water, salt and yeast, knead the dough for ten minutes and let it rise until it doubles.",
    "Photosynthesis lets plants turn sunlight, water and carbon dioxide into sugar and oxygen inside their green leaves.",
    "The train to the coast leaves at nine, so we should pack the bags tonight and buy the tickets at the station early.",
    "A good password is long, unique for every account and stored in a password manager instead of on a sticky note.",
    "In chess, the bishop moves diagonally across any number of squares, while the knight jumps in an L shape.",
    "When water is heated to one hundred degrees Celsius at sea level, it boils and turns into steam.",
    "She opened the window, listened to the rain on the roof and decided to read her book for another hour.",
    "The library closes at six on weekdays, but on Saturdays it stays open until eight in the evening.",
    "Exercise improves sleep, mood and heart health, even when it is only a short walk after dinner.",
    "The old computer was slow, so he cleaned the dust from the fan and replaced the hard drive with a small SSD.",
    "Most birds build nests in spring, using twigs, grass and feathers to keep their eggs warm and safe.",
    "If you want to learn a language, practise a little every day and speak with people as soon as you can.",
    "The museum shows paintings from the last three centuries, including a famous portrait of a sailor.",
    "Our neighbour repairs bicycles in his garage and always has a spare tyre for children in the street.",
    "A triangle has three sides, and the sum of its inner angles is always one hundred and eighty degrees.",
    "During the meeting the team agreed to finish the report by Friday and to present it next Monday.",
    "The moon does not shine by itself; it reflects the light of the sun back to the earth.",
    "Fresh vegetables last longer when they are kept dry and cool, away from fruits that release ethylene.",
    "The child counted the stars from the balcony until she fell asleep in her father's arms.",
    "A budget helps you see where your money goes each month and where you could save a little more.",
    "Mountains are colder at the top because the air becomes thinner and holds less heat.",
    "The baker wakes at four every morning so that warm rolls are ready when the shop opens.",
    "Volcanoes form where magma from deep inside the earth rises through cracks in the crust.",
]
OLD_DE = [
    "Der Fluss fließt langsam durch das Tal, vorbei an alten Steinbrücken und ruhigen Höfen, auf denen morgens Kühe grasen.",
    "Für ein einfaches Brot mischt man Mehl, Wasser, Salz und Hefe, knetet den Teig zehn Minuten und lässt ihn gehen.",
    "Bei der Fotosynthese wandeln Pflanzen Sonnenlicht, Wasser und Kohlendioxid in Zucker und Sauerstoff um.",
    "Der Zug an die Küste fährt um neun, also packen wir heute Abend die Taschen und kaufen früh die Fahrkarten.",
    "Ein gutes Passwort ist lang, für jedes Konto anders und steht in einem Passwortmanager statt auf einem Zettel.",
    "Beim Schach zieht der Läufer diagonal über beliebig viele Felder, der Springer springt in Form eines L.",
    "Wenn Wasser auf Meereshöhe auf hundert Grad Celsius erhitzt wird, kocht es und wird zu Dampf.",
    "Sie öffnete das Fenster, hörte dem Regen auf dem Dach zu und las noch eine Stunde in ihrem Buch.",
    "Die Bibliothek schließt werktags um sechs, aber samstags bleibt sie bis acht Uhr abends geöffnet.",
    "Bewegung verbessert Schlaf, Stimmung und Herzgesundheit, auch wenn es nur ein kurzer Spaziergang ist.",
    "Der alte Rechner war langsam, also entfernte er den Staub vom Lüfter und baute eine kleine SSD ein.",
    "Die meisten Vögel bauen im Frühling Nester aus Zweigen, Gras und Federn, um ihre Eier warm zu halten.",
    "Wer eine Sprache lernen will, übt am besten jeden Tag ein wenig und spricht so früh wie möglich mit Menschen.",
    "Das Museum zeigt Gemälde aus drei Jahrhunderten, darunter ein berühmtes Porträt eines Seemanns.",
    "Unser Nachbar repariert Fahrräder in seiner Garage und hat immer einen Ersatzreifen für die Kinder.",
    "Ein Dreieck hat drei Seiten, und die Summe seiner Innenwinkel beträgt immer hundertachtzig Grad.",
    "In der Besprechung einigte sich das Team darauf, den Bericht bis Freitag fertigzustellen.",
    "Der Mond leuchtet nicht selbst, er wirft das Licht der Sonne zur Erde zurück.",
    "Frisches Gemüse hält länger, wenn es trocken und kühl gelagert wird, getrennt von reifem Obst.",
    "Das Kind zählte die Sterne vom Balkon aus, bis es in den Armen seines Vaters einschlief.",
    "Ein Haushaltsplan zeigt, wohin das Geld jeden Monat fließt und wo man etwas sparen könnte.",
    "Auf Berggipfeln ist es kälter, weil die Luft dünner wird und weniger Wärme speichert.",
    "Der Bäcker steht jeden Morgen um vier auf, damit warme Brötchen bereitliegen, wenn der Laden öffnet.",
    "Vulkane entstehen dort, wo Magma aus dem Erdinneren durch Risse in der Kruste nach oben steigt.",
]
PREAMBLES = ("Here is a short text.\n", "Read the following passage.\n", "Text:\n")
# Fictional facts: new task for the update part and sender/receiver pairs for the latent part.
FACTS = [
    ("Mira Kessel", "Tolvane"), ("Oskar Brandt", "Velmora"), ("Lena Duvall", "Karsith"),
    ("Tomas Reiff", "Oberlune"), ("Ines Halberg", "Prastow"), ("Jonas Wiel", "Eskarra"),
    ("Clara Moos", "Dunvelt"), ("Felix Aaron", "Sorvik"), ("Nora Stade", "Quelmir"),
    ("Paul Ettrich", "Bramholt"), ("Greta Lund", "Ysmerin"), ("Emil Rosch", "Taddoria"),
    ("Hanna Vogt", "Lurenzia"), ("David Kolb", "Mestrava"), ("Sofie Brack", "Nimbrook"),
    ("Lukas Fenn", "Corvalis"),
]


def fact_text(name, city):
    return f"{name} was born in the town of {city}."


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


class Body:
    """HF Mixtral-style MoE body with router/residual hooks and an optional
    residual injection (the latent message opportunity)."""

    def __init__(self, path, threads):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.set_num_threads(threads)
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
        self.model.eval()
        cfg = self.model.config
        self.top_k = int(cfg.num_experts_per_tok)
        self.n_layers = int(cfg.num_hidden_layers)
        self.layers = self.model.model.layers
        self.inject = None  # (layer, vector[D], start_pos)
        self.rec = None
        for i, layer in enumerate(self.layers):
            layer.register_forward_pre_hook(self._pre_hook(i), with_kwargs=True)
            layer.block_sparse_moe.gate.register_forward_hook(self._gate_hook(i))

    def _pre_hook(self, i):
        def hook(module, args, kwargs):
            hs = kwargs['hidden_states'] if 'hidden_states' in kwargs else args[0]
            if self.inject is not None and self.inject[0] == i:
                vec, start = self.inject[1], self.inject[2]
                hs = hs.clone()
                hs[:, start:, :] = hs[:, start:, :] + vec
                if 'hidden_states' in kwargs:
                    kwargs['hidden_states'] = hs
                else:
                    args = (hs,) + tuple(args[1:])
            if self.rec is not None:
                self.rec.setdefault(i, {})['residual'] = hs.detach()[0].float().numpy().copy()
            return args, kwargs
        return hook

    def _gate_hook(self, i):
        def hook(module, inp, out):
            if self.rec is not None:
                x = inp[0].detach().float()
                self.rec[i]['router_input'] = x.reshape(-1, x.shape[-1]).numpy().copy()
                self.rec[i]['logits'] = out.detach().float().reshape(-1, out.shape[-1]).numpy().copy()
        return hook

    def ids(self, text, preamble=''):
        """Token ids of preamble and text tokenised separately and concatenated,
        so the text tokens are identical across preambles."""
        pre = self.tok(preamble, add_special_tokens=False)['input_ids'] if preamble else []
        body = self.tok(text, add_special_tokens=False)['input_ids']
        bos = [self.tok.bos_token_id] if self.tok.bos_token_id is not None else []
        return bos + pre + body, len(body)

    def run(self, ids, capture=True, bf16=False, labels_from=None):
        """Forward pass. Returns (Capture|None, mean NLL over positions >= labels_from)."""
        torch = self.torch
        x = torch.tensor([ids])
        self.rec = {} if capture else None
        with torch.no_grad():
            if bf16:
                with torch.autocast('cpu', dtype=torch.bfloat16):
                    logits = self.model(x).logits
            else:
                logits = self.model(x).logits
        nll = None
        if labels_from is not None:
            lp = torch.log_softmax(logits[0, :-1].float(), -1)
            tgt = x[0, 1:]
            tok_nll = -lp.gather(1, tgt[:, None])[:, 0]
            nll = float(tok_nll[labels_from - 1:].mean())
        cap = None
        if capture:
            cap = M.Capture({i: M.LayerCapture(r['logits'], r['router_input'], r['residual'])
                             for i, r in self.rec.items()}, self.top_k)
        self.rec = None
        return cap, nll

    def residual_mean(self, text, layer):
        ids, n = self.ids(text)
        cap, _ = self.run(ids)
        return cap.layers[layer].residual[-n:].mean(axis=0), float(np.mean(np.linalg.norm(cap.layers[layer].residual[-n:], axis=-1)))

    def chat_ids(self, user, answer):
        """Chat prompt ids and the position where the answer starts."""
        msgs = [{"role": "user", "content": user}]
        prompt = self.tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True)
        ans = self.tok(answer, add_special_tokens=False)['input_ids']
        return list(prompt) + ans, len(prompt)


def part_calib(body, texts, out):
    """Receiver-native variation: identical text tokens after neutral preambles
    (P0 vs P1 and P0 vs P2). A bf16-autocast numeric variant was dropped: on
    this CPU host it re-materialised the weights per call and thrashed RAM."""
    variation, rows = [], []
    for lang, t in texts:
        caps, n = [], None
        for pre in PREAMBLES:
            ids, n = body.ids(t, pre)
            caps.append(body.run(ids)[0].tail(n))
        for j in (1, 2):
            agg = M.compare(caps[0], caps[j])['aggregate']
            variation.append(agg)
            rows.append({'lang': lang, 'tokens': n, 'pair': f'P0-P{j}', 'aggregate': agg})
    cal = M.calibrate(variation, source='same text tokens after neutral preambles P0/P1/P2')
    out['calib'] = {'primary': cal, 'rows': rows}
    return cal


def part_latent(body, cal, out, layer, alphas, seeds, old_texts):
    D = body.model.config.hidden_size
    # Receiver utility: answer NLL of the city with NONE / EXACT text / latent.
    results = []
    old_base = {}
    for lang, t in old_texts:
        ids, n = body.ids(t)
        cap, nll = body.run(ids, labels_from=len(ids) - n)
        old_base[t] = (ids, n, cap, nll)
    for seed in seeds:
        rng = np.random.default_rng(seed)
        facts = list(FACTS)
        random.Random(seed).shuffle(facts)
        for kind in ('sender_latent', 'random_direction'):
            for alpha in alphas:
                gains, exact_gains, metrics, old_deltas = [], [], [], []
                for name, city in facts[:8]:
                    q = f"In which town was {name} born? Answer with the town name only."
                    ids, start = body.chat_ids(q, city)
                    base_cap, base_nll = body.run(ids, labels_from=start)
                    ex_ids, ex_start = body.chat_ids(fact_text(name, city) + " " + q, city)
                    _, ex_nll = body.run(ex_ids, capture=False, labels_from=ex_start)
                    mu, scale = body.residual_mean(fact_text(name, city), layer)
                    vec = mu if kind == 'sender_latent' else rng.normal(size=D)
                    vec = vec / max(np.linalg.norm(vec), 1e-9) * alpha * scale
                    body.inject = (layer, body.torch.tensor(vec, dtype=body.torch.float32), 1)
                    try:
                        cap, nll = body.run(ids, labels_from=start)
                    finally:
                        body.inject = None
                    keep = [i for i in base_cap.layers if i >= layer]
                    metrics.append(M.compare(base_cap, cap, layers=keep)['aggregate'])
                    gains.append(base_nll - nll)
                    exact_gains.append(base_nll - ex_nll)
                # Old-task retention: same message injected into old-task text.
                for lang, t in old_texts[:12]:
                    ids, n, _, nll0 = old_base[t]
                    name, city = facts[0]
                    mu, scale = body.residual_mean(fact_text(name, city), layer)
                    vec = mu if kind == 'sender_latent' else rng.normal(size=D)
                    vec = vec / max(np.linalg.norm(vec), 1e-9) * alpha * scale
                    body.inject = (layer, body.torch.tensor(vec, dtype=body.torch.float32), 1)
                    try:
                        _, nll1 = body.run(ids, capture=False, labels_from=len(ids) - n)
                    finally:
                        body.inject = None
                    old_deltas.append(nll1 - nll0)
                agg = {k: float(np.mean([m[k] for m in metrics if k in m])) for k in metrics[0]}
                worst = {k: float(np.max([m[k] for m in metrics if k in m])) for k in metrics[0]}
                gate = M.router_stability_gate(worst, cal, old_task_loss_delta=float(np.mean(old_deltas)),
                                               max_old_task_loss_delta=None,
                                               utility_gain=float(np.mean(gains)),
                                               min_downstream_utility_gain=None)
                results.append({'seed': seed, 'message': kind, 'alpha': alpha, 'layer': layer,
                                'router_mean': agg, 'router_worst': worst,
                                'utility_nll_gain_mean': float(np.mean(gains)),
                                'exact_text_nll_gain_mean': float(np.mean(exact_gains)),
                                'old_task_loss_delta_mean': float(np.mean(old_deltas)),
                                'router_gate': gate})
                print(f'latent seed={seed} {kind} a={alpha} kl={worst["router_kl"]:.4f} '
                      f'flip={worst["topk_flip_rate"]:.3f} gain={np.mean(gains):+.3f} '
                      f'exact={np.mean(exact_gains):+.3f} old={np.mean(old_deltas):+.4f} {gate["verdict"]}', flush=True)
    out['latent'] = results


def param_groups(body, window):
    groups = {'shared': [], 'router': [], 'experts': []}
    for i in window:
        L = body.layers[i]
        for n, p in L.self_attn.named_parameters():
            groups['shared'].append((f'L{i}.attn.{n}', p))
        groups['shared'].append((f'L{i}.input_layernorm', L.input_layernorm.weight))
        groups['shared'].append((f'L{i}.post_attention_layernorm', L.post_attention_layernorm.weight))
        groups['router'].append((f'L{i}.gate', L.block_sparse_moe.gate.weight))
        for n, p in L.block_sparse_moe.experts.named_parameters():
            groups['experts'].append((f'L{i}.experts.{n}', p))
    return groups


def part_update(body, cal, out, window, seeds, old_texts, steps, lr, target, min_forgetting):
    torch = body.torch
    groups = param_groups(body, window)
    for p in body.model.parameters():
        p.requires_grad_(False)
    snapshot = {g: [p.detach().clone() for _, p in ps] for g, ps in groups.items()}
    router_old = {i: body.layers[i].block_sparse_moe.gate.weight.detach().clone().numpy() for i in window}

    def old_eval():
        caps, nlls = [], []
        for lang, t in old_texts:
            ids, n = body.ids(t)
            cap, nll = body.run(ids, labels_from=len(ids) - n)
            caps.append(cap.tail(n))
            nlls.append(nll)
        merged = M.Capture({i: M.LayerCapture(np.concatenate([c.layers[i].logits for c in caps]),
                                               np.concatenate([c.layers[i].router_input for c in caps]),
                                               np.concatenate([c.layers[i].residual for c in caps]))
                            for i in caps[0].layers}, body.top_k)
        return merged, float(np.mean(nlls))

    def old_loss_only():
        nlls = []
        for _, t in old_texts:
            ids, n = body.ids(t)
            nlls.append(body.run(ids, capture=False, labels_from=len(ids) - n)[1])
        return float(np.mean(nlls))

    def new_loss(batch):
        tot = 0.0
        for ids in batch:
            x = torch.tensor([ids])
            tot = tot + body.model(x, labels=x).loss
        return tot / len(batch)

    def restore(names):
        with torch.no_grad():
            for g in names:
                for (_, p), s in zip(groups[g], snapshot[g]):
                    p.copy_(s)

    base_cap, base_old = old_eval()
    results = []
    for seed in seeds:
        torch.manual_seed(seed)
        facts = list(FACTS)
        random.Random(seed).shuffle(facts)
        train = [body.ids(fact_text(n, c))[0] for n, c in facts]
        for arm in ('shared', 'router', 'experts', 'all'):
            restore(groups)
            names = list(groups) if arm == 'all' else [arm]
            params = [p for g in names for _, p in groups[g]]
            for p in params:
                p.requires_grad_(True)
            opt = torch.optim.Adam(params, lr=lr)
            with torch.no_grad():
                start = float(new_loss(train))
            body.model.train(False)
            used, cur = 0, start
            t0 = time.time()
            for step in range(steps):
                opt.zero_grad(set_to_none=True)
                loss = new_loss(train)
                loss.backward()
                opt.step()
                used, cur = step + 1, float(loss.detach())
                if cur <= target * start:
                    break
            for p in params:
                p.requires_grad_(False)
            del opt
            with torch.no_grad():
                end = float(new_loss(train))
            after_cap, after_old = old_eval()
            deltas = {g: float(sum(torch.linalg.vector_norm(p.detach() - s).item() ** 2
                                   for (_, p), s in zip(groups[g], snapshot[g])) ** .5) for g in names}
            route = {}
            if 'router' in names:
                i = window[0]
                route = M.counterfactual_route_shift(base_cap.layers[i].router_input, after_cap.layers[i].router_input,
                                                     router_old[i], body.layers[i].block_sparse_moe.gate.weight.detach().numpy(),
                                                     body.top_k)
                route['layer'] = i
            restore_losses = {}
            if arm == 'all':
                trained = {g: [p.detach().clone() for _, p in groups[g]] for g in groups}
                for g in groups:
                    restore([g])
                    restore_losses[g] = old_loss_only()
                    with torch.no_grad():
                        for (_, p), s in zip(groups[g], trained[g]):
                            p.copy_(s)
            rep = M.interference_report(base_cap, after_cap, base_old, after_old,
                                        restore_losses=restore_losses or None, delta_norms=deltas,
                                        calibration=cal, route=route or None,
                                        min_forgetting=min_forgetting)
            per_layer = {str(i): {k: v for k, v in d.items() if k in (
                'router_kl', 'topk_flip_rate', 'router_input_drift', 'router_input_norm_shift',
                'shared_drift', 'residual_norm_shift', 'expert_hist_shift')} for i, d in rep.pop('per_layer').items()}
            results.append({'seed': seed, 'arm': arm, 'window': list(window), 'steps': used, 'lr': lr,
                            'new_task_loss_start': start, 'new_task_loss_end': end,
                            'seconds': round(time.time() - t0, 1), 'monitor': rep, 'per_layer': per_layer})
            print(f'update seed={seed} arm={arm} steps={used} new {start:.3f}->{end:.3f} '
                  f'old {base_old:.4f}->{after_old:.4f} shared_drift={rep["pre_router_drift"]:.4f} '
                  f'rin={rep["router_input_drift"]:.4f} kl={rep["old_task_route_shift"]:.4f} '
                  f'{rep["verdict"]} {rep["restoration_recovery"]}', flush=True)
    restore(groups)
    out['update'] = results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', required=True)
    ap.add_argument('--model-id', default='')
    ap.add_argument('--revision', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--parts', default='calib,latent,update')
    ap.add_argument('--max-texts', type=int, default=0)
    ap.add_argument('--seeds', default='13,21,34')
    ap.add_argument('--layer', type=int, default=8)
    ap.add_argument('--alphas', default='0,0.01,0.025,0.05,0.1')
    ap.add_argument('--window', default='8,9')
    ap.add_argument('--steps', type=int, default=30)
    ap.add_argument('--lr', type=float, default=3e-4)
    ap.add_argument('--target', type=float, default=0.1)
    ap.add_argument('--min-forgetting', type=float, default=0.02)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--hash', action='store_true')
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(',')]
    texts = [('en', t) for t in OLD_EN] + [('de', t) for t in OLD_DE]
    if a.max_texts:
        texts = texts[:a.max_texts // 2] + texts[len(OLD_EN):len(OLD_EN) + a.max_texts // 2]
    out = {'schema': 'v13-moe-router-bench-v1', 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'model_id': a.model_id, 'revision': a.revision, 'args': vars(a),
           'host': {'python': platform.python_version(), 'machine': platform.machine()},
           'evidence_level': 'Linux cloud CPU, HF transformers fp32; not llama.cpp, not Redmi'}
    import torch
    import transformers
    out['host'].update(torch=torch.__version__, transformers=transformers.__version__)
    if a.hash:
        out['files'] = {p.name: sha256(p) for p in sorted(Path(a.model).glob('*')) if p.is_file()}
    body = Body(a.model, a.threads)
    out['config'] = {'top_k': body.top_k, 'layers': body.n_layers, 'experts': int(body.model.config.num_local_experts),
                     'hidden': int(body.model.config.hidden_size)}
    parts = a.parts.split(',')
    cal = None
    t0 = time.time()
    if 'calib' in parts:
        cal = part_calib(body, texts, out)
        print('calibration', json.dumps(cal['thresholds']), flush=True)
    if cal is None:
        cal = {'status': 'UNCALIBRATED', 'thresholds': {}}
    if 'latent' in parts:
        part_latent(body, cal, out, a.layer, [float(x) for x in a.alphas.split(',')], seeds, texts)
    if 'update' in parts:
        part_update(body, cal, out, [int(x) for x in a.window.split(',')], seeds, texts, a.steps, a.lr, a.target, a.min_forgetting)
    out['seconds'] = round(time.time() - t0, 1)
    import resource
    out['maxrss_mb'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True, default=float))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
