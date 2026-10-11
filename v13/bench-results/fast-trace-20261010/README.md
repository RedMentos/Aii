# Blueprint §9.1 Parametric Fast Trace vs exact episodic retrieval (C3 = LFM2.5-350M Q4, llama-server HTTP, 2026-10-10)

Prompt = system message of runtime._turn in a fresh chat (`memory_trainer.live_system`). Script `code/scripts/fast_trace_compare.py`.
8 invented facts, 6 paraphrases, 5 near-miss questions, 12 retention probes (`code/scripts/lora_bench.py`).

| condition | facts | paraphrase | near-miss leak | probes | prompt tokens |
|---|---|---|---|---|---|
| base | 0/8 | 0/6 | 0 | .75 | 193 |
| exact retrieval only | 8/8 | 4/6 | .6 | .83 | 227 |
| trace only, keys written in live context | 8/8 | 5/6 | .6 | .75 | 193 |
| exact + trace (live-written) | 7/8 | 3/6 | .8 | .83 | 227 |
| trace only, keys written on bare user turn | 1/8 | 0/6 | 0 | .75 | 193 |

Verdict (blueprint rule "trace wins only if recall/transfer/latency/memory together better"): the trace does not win
in combination with exact retrieval, which the runtime always runs. Trace alone is on par (+1 paraphrase, -15 % prompt
tokens). Keys must be written in the live context (`cfg.system`), a bare-turn trace barely fires in the chat.
Consequence: AG6 `auto` never picks the sparse trainer; `:growth trainer sparse` stays explicit.
Open idea: serve a fact either as trace or as exact block, not both (dedupe), then measure again.
