"""Second, independent implementation of the block-scaled ternary dot-product SQNR.
Purpose: check the 22-25 dB gap claim of the previous loop with a different quantiser
code path (gpt2_np.FORMATS) instead of levelA/exp_ternary_task.quant_float.
"""
import json, math, sys
import numpy as np
sys.path.insert(0, "/home/user/workspace/levelA")
import gpt2_np as G
from exp_ternary_task import quant_float, DISTS
SEED = 20260819

def sqnr(a, b):
    return 10 * math.log10(float(np.sum(a ** 2)) / float(np.sum((a - b) ** 2)))

cands16 = ["e2m13_b32", "e3m12_b32", "e5m10", "e6m9_b32_PHI", "e6m9_PHI",
           "fixed16_b32", "tnf16_t4m8_b32"]
cands8 = ["e2m5_b32", "e4m3", "int8_b32", "e3m4_b32_PHI8"]
out = {}
for dname, fn in DISTS.items():
    row = {}
    for cname in cands16 + cands8:
        rng = np.random.default_rng(SEED)
        ex, got = np.empty(150), np.empty(150)
        for i in range(150):
            x = fn(rng, 1024).astype(np.float32)
            w = rng.choice([-1.0, 0.0, 1.0], size=1024, p=[.25, .5, .25]).astype(np.float32)
            ex[i] = float(np.dot(w.astype(np.float64), x.astype(np.float64)))
            got[i] = float(np.dot(w.astype(np.float64), G.FORMATS[cname](x).astype(np.float64)))
        row[cname] = round(sqnr(ex, got), 2)
    out[dname] = row
json.dump(out, open("/home/user/workspace/levelB/results_xcheck.json", "w"), indent=1)
hdr = cands16 + cands8
print(f"{'dist':16s}" + "".join(f"{c[:13]:>15s}" for c in hdr))
for d, r in out.items():
    print(f"{d:16s}" + "".join(f"{r[c]:15.2f}" for c in hdr))
g16 = {d: round(max(r[c] for c in cands16) - r["e6m9_b32_PHI"], 2) for d, r in out.items()}
print("phi gap at 16 bit (best16 - e6m9_b32_PHI):", g16)
print("tnf16 gap:", {d: round(max(r[c] for c in cands16) - r["tnf16_t4m8_b32"], 2) for d, r in out.items()})
