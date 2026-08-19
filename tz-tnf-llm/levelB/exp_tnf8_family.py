"""Two questions in one paired run, 12 windows, same frozen corpus.

(1) The whole physically-exact 8-bit TNF family, not one point. A TNF rung with
    E_t trits packs the offset into ceil(E_t*log2 3) bits, so exactly three rungs
    fit a real 8-bit container: (E_t=1,M=5), (E_t=2,M=3), (E_t=3,M=2).
    The spec rung TNF8 = (E_t=3, M=4) needs 10 physical bits and is therefore NOT
    measurable in 8 bits -- it is excluded by arithmetic, not by preference.
(2) Window policy sensitivity. arXiv:2606.03002 reports the SIGN of a delta-ppl
    flipping between chunked and sliding-window evaluation. We re-measure two
    formats with stride 256 (50 % overlap) against stride 512 (disjoint) and
    check whether our sign survives.
"""
import json, math, os, time
import numpy as np
import gpt2_np as G
HERE = os.path.dirname(os.path.abspath(__file__))
T, NWIN = 512, 12
w = G.load_safetensors(os.path.join(HERE, "gpt2_model.safetensors"))
tk = G.BPE(os.path.join(HERE, "vocab.json"), os.path.join(HERE, "merges.txt"))
txt = open(os.path.join(HERE, "pg2701.txt"), encoding="utf-8", errors="ignore").read()
txt = txt[txt.find("Call me Ishmael"):]
ids, pos = [], 0
while len(ids) < T * NWIN + 600: ids += tk.encode(txt[pos:pos + 20000]); pos += 20000

def qf(ebits, mbits, codes, block=32):
    return lambda x: G._fmt_float(x, ebits, mbits, ecodes=codes, block=block)

VAR = {
    "base":            None,
    "tnf8_t1m5_b32":   qf(2, 5, 3),    # 1 trit  -> 3 codes in a 2-bit field
    "tnf8_t2m3_b32":   qf(4, 3, 9),    # 2 trits -> 9 codes in a 4-bit field (what we measured before)
    "tnf8_t3m2_b32":   qf(5, 2, 27),   # 3 trits -> 27 codes in a 5-bit field
    "int8_b32":        lambda x: G._fmt_fixed(x, 8, block=32),
    "e4m3_b32":        qf(4, 3, 16),
}
def nll_windows(q, stride):
    starts = list(range(0, T * NWIN, stride))[:NWIN if stride == T else 2 * NWIN - 1]
    out = []
    m = G.GPT2(w, qact=q)
    for st in starts:
        seg = ids[st:st + T + 1]
        if len(seg) < T + 1: break
        lg = m.forward(seg[:T])
        out.append(G.nll(lg[:-1], np.array(seg[1:T])) / (T - 1))
    return np.array(out, dtype=np.float64)

res = {}
for stride, tag in ((T, "chunked"), (T // 2, "sliding")):
    base = None
    for name, q in VAR.items():
        if tag == "sliding" and name not in ("base", "tnf8_t2m3_b32", "int8_b32"): continue
        t0 = time.time(); a = nll_windows(q, stride)
        if name == "base": base = a
        d = a - base
        row = dict(policy=tag, n=len(a), ppl=float(math.exp(a.mean())),
                   mean_dnll=float(d.mean()),
                   dppl_pct=float(100 * (math.exp(a.mean()) / math.exp(base.mean()) - 1)),
                   worse_share=float((d > 0).mean()), secs=round(time.time() - t0, 1))
        res[f"{tag}|{name}"] = row
        print(f"{tag:8s} {name:16s} n={row['n']:3d} ppl={row['ppl']:.4f} "
              f"dppl={row['dppl_pct']:+.3f}% worse={row['worse_share']:.2f} {row['secs']}s", flush=True)
json.dump(res, open("results_tnf8_family.json", "w"), indent=1)
