"""Does the 22-25 dB representation gap between 16-bit activation formats show up in
perplexity of a real model on real text? Paired design: identical tokens for every variant.
"""
import json, math, os, sys, time
import numpy as np
import gpt2_np as G

HERE = os.path.dirname(os.path.abspath(__file__))
T, NWIN = 512, 12
STATUS = os.path.join(HERE, "ppl.status")

def log(s):
    open(STATUS, "a").write(f"{time.strftime('%H:%M:%S')} {s}\n")

def tokens(path, start_marker, need):
    tk = G.BPE(os.path.join(HERE, "vocab.json"), os.path.join(HERE, "merges.txt"))
    txt = open(os.path.join(HERE, path), encoding="utf-8", errors="ignore").read()
    i = txt.find(start_marker)
    txt = txt[i if i > 0 else 0:]
    ids = []
    step = 20000
    pos = 0
    while len(ids) < need and pos < len(txt):
        ids += tk.encode(txt[pos:pos + step]); pos += step
    return ids[:need]

def run_corpus(w, ids, variants, tag, out):
    base_logits = {}
    for name, (qact, qw) in variants.items():
        t0 = time.time()
        m = G.GPT2(w, qact=qact, qw=qw)
        tot, cnt, sq_num, sq_den = 0.0, 0, 0.0, 0.0
        for k in range(NWIN):
            seg = ids[k * T:(k + 1) * T + 1]
            if len(seg) < T + 1:
                break
            lg = m.forward(seg[:T])
            tot += G.nll(lg[:-1], np.array(seg[1:T]))
            cnt += T - 1
            if name == "fp32":
                base_logits[k] = lg.copy()
            elif k in base_logits:
                d = lg - base_logits[k]
                sq_num += float(np.sum(base_logits[k] ** 2)); sq_den += float(np.sum(d ** 2))
        ppl = math.exp(tot / cnt)
        sqnr = 10 * math.log10(sq_num / sq_den) if sq_den > 0 else float("inf")
        out.setdefault(tag, {})[name] = dict(ppl=round(ppl, 4), nll_per_token=round(tot / cnt, 6),
                                             tokens=cnt, logit_sqnr_db=(None if sq_den == 0 else round(sqnr, 2)),
                                             seconds=round(time.time() - t0, 1))
        log(f"{tag} {name} ppl={ppl:.4f} logitSQNR={sqnr:.2f} dB {time.time()-t0:.0f}s")
        json.dump(out, open(os.path.join(HERE, "results_ppl.json"), "w"), indent=1)

def main():
    log("start")
    w = G.load_safetensors(os.path.join(HERE, "gpt2_model.safetensors"))
    F = G.FORMATS
    A = {k: (F[k], None) for k in ["fp32", "e2m13_b32", "e3m12_b32", "e5m10", "e6m9_b32_PHI",
                                   "e6m9_PHI", "fixed16_b32", "tnf16_t4m8_b32",
                                   "e2m5_b32", "e4m3", "int8_b32", "e3m4_b32_PHI8"]}
    out = {}
    ids = tokens("pg2701.txt", "CHAPTER 1", (T + 1) * NWIN + 10)
    log(f"moby tokens {len(ids)}")
    run_corpus(w, ids, A, "mobydick_act_only", out)
    # ternary weights + candidate activations
    B = {k: (F[k], G.ternary_weights) for k in ["fp32", "e2m13_b32", "e6m9_b32_PHI",
                                                "tnf16_t4m8_b32", "e2m5_b32", "int8_b32"]}
    run_corpus(w, ids, B, "mobydick_ternary_weights", out)
    ids2 = tokens("input.txt", "First Citizen", (T + 1) * NWIN + 10)
    log(f"shake tokens {len(ids2)}")
    C = {k: (F[k], None) for k in ["fp32", "e2m13_b32", "e6m9_b32_PHI", "tnf16_t4m8_b32",
                                    "e2m5_b32", "int8_b32"]}
    run_corpus(w, ids2, C, "shakespeare_act_only", out)
    log("DONE")

if __name__ == "__main__":
    main()
