// V13 keyed sparse memory hook (WP-S3), shared by scripts/native_memory_hook.cpp and the patched llama-server
// (v13/memory_server.py patches tools/server). Header-only; needs llama.h/ggml.h/ggml-backend.h.
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <set>
#include <string>
#include <vector>

struct Memory {
    int layer = 0, hidden = 0, n = 0, ent_w = 0, topk = 32; float tau = .01f, scale = 1.f;
    std::vector<float> mu, keys, theta, values; std::vector<int32_t> ent;
    std::set<int32_t> ctx; std::vector<float> x; int64_t x_rows = 0; bool use_guard = true, track_ctx = false, debug = false; long fired = 0, writes = 0; int64_t last_n = 1; bool explicit_ctx = false;
    // Opt-in observations only. Row indices are bound to the separately hashed memory artifact.
    bool audit = false; unsigned long audit_request = 0;
    long audit_rows = 0, audit_batches = 0;
    std::vector<long> audit_applied, audit_guard_blocked;
};

inline void v13_audit_begin(Memory & m) {
    if (!m.audit) return;
    ++m.audit_request; m.audit_rows = 0; m.audit_batches = 0;
    m.audit_applied.assign(m.n, 0); m.audit_guard_blocked.assign(m.n, 0);
    std::fprintf(stderr, "V13_MEMORY_AUDIT {\"schema\":\"v13-native-firing-v1\",\"event\":\"begin\",\"request\":%lu,\"slots\":%d,\"layer\":%d}\n", m.audit_request, m.n, m.layer);
}

inline void v13_audit_batch(Memory & m, int64_t rows) {
    if (!m.audit || !m.audit_request || m.audit_applied.size() != (size_t)m.n || m.audit_guard_blocked.size() != (size_t)m.n) return;
    m.audit_rows += rows; ++m.audit_batches;
    std::fprintf(stderr, "V13_MEMORY_AUDIT {\"schema\":\"v13-native-firing-v1\",\"event\":\"batch\",\"request\":%lu,\"rows\":%ld,\"batches\":%ld,\"applied\":[", m.audit_request, m.audit_rows, m.audit_batches);
    for (int i = 0; i < m.n; ++i) std::fprintf(stderr, "%s%ld", i ? "," : "", m.audit_applied[i]);
    std::fprintf(stderr, "],\"guard_blocked\":[");
    for (int i = 0; i < m.n; ++i) std::fprintf(stderr, "%s%ld", i ? "," : "", m.audit_guard_blocked[i]);
    std::fprintf(stderr, "]}\n");
}

inline bool load_memory(const char * path, Memory & m) {
    std::ifstream f(path, std::ios::binary); if (!f) return false;
    char magic[8]; f.read(magic, 8); if (std::memcmp(magic, "V13SMEM1", 8) != 0) return false;
    int32_t h[6]; f.read((char *) h, sizeof h); m.layer = h[0]; m.hidden = h[1]; m.n = h[2]; m.ent_w = h[3]; m.topk = h[4]; m.use_guard = h[5] != 0;
    float fh[2]; f.read((char *) fh, sizeof fh); m.tau = fh[0]; m.scale = fh[1];
    auto rd = [&](std::vector<float> & v, size_t k) { v.resize(k); f.read((char *) v.data(), k * 4); };
    rd(m.mu, m.hidden); rd(m.keys, (size_t) m.n * m.hidden); rd(m.theta, m.n); rd(m.values, (size_t) m.n * m.hidden);
    m.ent.resize((size_t) m.n * m.ent_w); f.read((char *) m.ent.data(), m.ent.size() * 4);
    return bool(f);
}

inline bool ends_with(const char * s, const std::string & suf) { size_t n = std::strlen(s); return n >= suf.size() && suf == s + n - suf.size(); }

inline bool hook(ggml_tensor * t, bool ask, void * ud) {
    auto & m = *(Memory *) ud; const char * name = ggml_get_name(t);
    const bool audit_active = m.audit && m.audit_request && m.audit_applied.size() == (size_t)m.n && m.audit_guard_blocked.size() == (size_t)m.n;
    const std::string L = "-" + std::to_string(m.layer);
    const bool is_x = t->op == GGML_OP_MUL && t->ne[0] == m.hidden && (ends_with(name, "ffn_norm" + L) || ends_with(name, "ffn_out" + L));
    const bool is_out = ends_with(name, "l_out" + L) && t->ne[0] == m.hidden;
    const bool is_emb = m.track_ctx && t->op == GGML_OP_GET_ROWS && t->src[0] && t->src[1] && t->src[1]->type == GGML_TYPE_I32 && ends_with(ggml_get_name(t->src[0]), "token_embd.weight");
    if (m.debug && ask && (is_x || is_out || is_emb)) std::fprintf(stderr, "v13 memory: node %s op=%s\n", name, ggml_op_name(t->op));
    if (ask) return is_x || is_out || is_emb;
    if (is_emb && t->src[1]->buffer && ggml_backend_buffer_is_host(t->src[1]->buffer)) {
        const int32_t * ids = (const int32_t *) t->src[1]->data; const int64_t n = ggml_nelements(t->src[1]);
        // A multi-token batch after a single-token (generation) batch starts a new prompt. The server splits one prompt into
        // several chunks (hybrid-model checkpoints), so consecutive chunks accumulate. Needs one sequence (-np 1). Tokens of a
        // reused cached prefix are not seen again: the guard then fails closed (no recall), never open.
        if (!m.explicit_ctx && n > 1 && m.last_n == 1) m.ctx.clear();  // explicit_ctx: the server set the full prompt
        m.last_n = n; m.ctx.insert(ids, ids + n); return true;
    }
    if (!t->buffer || !ggml_backend_buffer_is_host(t->buffer) || t->type != GGML_TYPE_F32) return true;
    const int64_t rows = t->ne[1]; float * d = (float *) t->data;
    if (is_x) { m.x.assign(d, d + rows * m.hidden); m.x_rows = rows; return true; }
    if (!is_out || m.x_rows != rows || m.n == 0) return true;
    std::vector<float> q(m.hidden), c(m.n); std::vector<int> idx(m.n);
    for (int64_t r = 0; r < rows; ++r) {
        double nrm = 0; for (int i = 0; i < m.hidden; ++i) { q[i] = m.x[r * m.hidden + i] - m.mu[i]; nrm += (double) q[i] * q[i]; }
        const float inv = 1.f / (float) std::max(std::sqrt(nrm), 1e-12);
        for (int s = 0; s < m.n; ++s) { const float * k = &m.keys[(size_t) s * m.hidden]; double dot = 0; for (int i = 0; i < m.hidden; ++i) dot += (double) q[i] * k[i]; c[s] = (float) dot * inv; idx[s] = s; }
        const int k = std::min(m.topk, m.n);
        std::partial_sort(idx.begin(), idx.begin() + k, idx.end(), [&](int a, int b) { return c[a] > c[b]; });
        for (int j = 0; j < k; ++j) {
            const int s = idx[j]; float g = 1.f / (1.f + std::exp(-(c[s] - m.theta[s]) / m.tau));
            if (g < 1e-4f) continue;
            if (m.use_guard) {
                bool has = false, any = false;
                for (int e = 0; e < m.ent_w; ++e) { int32_t tok = m.ent[(size_t) s * m.ent_w + e]; if (tok < 0) continue; any = true; if (m.ctx.count(tok)) { has = true; break; } }
                if (any && !has) { if (audit_active) ++m.audit_guard_blocked[s]; continue; }
            }
            const float * v = &m.values[(size_t) s * m.hidden]; float * o = d + r * m.hidden;
            if (audit_active) {
                bool changed = false;
                for (int i = 0; i < m.hidden; ++i) {
                    const float before = o[i]; o[i] += m.scale * g * v[i];
                    changed = changed || o[i] != before;
                }
                if (changed) ++m.audit_applied[s];
            } else {
                for (int i = 0; i < m.hidden; ++i) o[i] += m.scale * g * v[i];
            }
            ++m.fired;
        }
    }
    ++m.writes;
    v13_audit_batch(m, rows);
    if (m.debug) std::fprintf(stderr, "v13 memory: rows=%lld ctx=%zu fired=%ld writes=%ld\n", (long long) rows, m.ctx.size(), m.fired, m.writes);
    return true;
}


#ifdef V13_MEMORY_SERVER
// llama-server: V13_MEMORY_FILE=<memory.bin> attaches the memory; without it the server is unchanged.
#include "arg.h"
inline Memory *& v13_mem() { static Memory * p = nullptr; return p; }
inline bool v13_parse_and_attach(int argc, char ** argv, common_params & params, llama_example ex) {
    if (!common_params_parse(argc, argv, params, ex)) return false;
    const char * f = std::getenv("V13_MEMORY_FILE");
    if (!f || !*f) return true;
    static Memory mem; mem.track_ctx = true; mem.debug = std::getenv("V13_MEMORY_DEBUG") != nullptr;
    mem.audit = std::getenv("V13_MEMORY_AUDIT") != nullptr;
    if (!load_memory(f, mem)) { std::fprintf(stderr, "V13_MEMORY_FILE unreadable: %s\n", f); return false; }
    params.cb_eval = hook; params.cb_eval_user_data = &mem;
    v13_mem() = &mem; mem.explicit_ctx = true;
    std::fprintf(stderr, "v13 memory attached: %d slots at layer %d\n", mem.n, mem.layer);
    return true;
}
// Called by the patched server when a slot starts a new prompt: the guard context is the whole prompt, including a
// prefix the prompt cache reuses (those tokens are not decoded again, so the embedding hook would not see them).
template <typename T> inline void v13_new_prompt(const T & tokens) {
    Memory * m = v13_mem(); if (!m) return;
    v13_audit_begin(*m);
    m->ctx.clear(); for (size_t i = 0; i < tokens.size(); ++i) if (tokens[i] >= 0) m->ctx.insert(tokens[i]);
}
#endif
