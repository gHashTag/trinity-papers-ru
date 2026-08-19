"""Paired per-window test: is the 16-bit format delta distinguishable from zero?
Stores per-window nll so a sign test / paired statistic can be computed honestly.
"""
import json, math, os, time
import numpy as np
import gpt2_np as G
from exp_ppl import tokens, T, NWIN
HERE = os.path.dirname(os.path.abspath(__file__))
w = G.load_safetensors(os.path.join(HERE, "gpt2_model.safetensors"))
ids = tokens("pg2701.txt", "CHAPTER 1", T * NWIN + 1)
V = ["fp32", "e6m9_b32_PHI", "tnf16_t4m8_b32", "e2m13_b32", "e2m5_b32"]
per = {}
for name in V:
    m = G.GPT2(w, qact=G.FORMATS[name], qw=None)
    rows = []
    for k in range(NWIN):
        seg = ids[k * T:(k + 1) * T + 1]
        if len(seg) < T + 1: break
        lg = m.forward(seg[:T])
        rows.append(G.nll(lg[:-1], np.array(seg[1:T])) / (T - 1))
    per[name] = rows
    print(name, "mean nll", round(float(np.mean(rows)), 6), "ppl", round(math.exp(float(np.mean(rows))), 4), flush=True)
res = {"per_window_nll": per, "windows": len(per["fp32"])}
b = np.array(per["fp32"])
res["window_ppl_fp32"] = [round(math.exp(x), 3) for x in b]
res["window_ppl_spread"] = {"min": round(math.exp(b.min()), 3), "max": round(math.exp(b.max()), 3)}
for name in V[1:]:
    a = np.array(per[name]); d = a - b
    pos = int(np.sum(d > 0)); n = len(d)
    # exact two-sided sign test
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(pos, n - pos) + 1)) / 2 ** n)
    tstat = float(np.mean(d) / (np.std(d, ddof=1) / math.sqrt(n))) if np.std(d, ddof=1) > 0 else float("inf")
    res[name] = {"mean_nll_delta": float(np.mean(d)), "worse_windows": pos, "windows": n,
                 "sign_test_p": round(p, 4), "paired_t": round(tstat, 3),
                 "ppl_delta_pct": round(100 * (math.exp(float(np.mean(a))) / math.exp(float(np.mean(b))) - 1), 4)}
    print(name, res[name], flush=True)
json.dump(res, open(os.path.join(HERE, "results_ppl_paired.json"), "w"), indent=1)
print("window ppl spread", res["window_ppl_spread"])
