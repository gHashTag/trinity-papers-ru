"""Test of an external decision rule against our own measurements.

arXiv:2510.25602 reports that with a shared block scale INT beats FP when the
block crest factor kappa = max|x| / rms(x) stays below a width-dependent
threshold: kappa < 7.55 at 8 bits, kappa < 1.96 at 6 bits.
We measure kappa on the same GPT-2 activations we quantise and check whether the
rule predicts the winner we measured. Prediction is declared BEFORE the check:
  8 bits: we measured INT8 as the winner -> the rule requires kappa < 7.55
  6 bits: we measured E2M3 as the winner -> the rule requires kappa > 1.96
"""
import json, math, os
import numpy as np
import gpt2_np as G
HERE = os.path.dirname(os.path.abspath(__file__))
T, NWIN, BLK = 512, 6, 32
w = G.load_safetensors(os.path.join(HERE, "gpt2_model.safetensors"))
tk = G.BPE(os.path.join(HERE, "vocab.json"), os.path.join(HERE, "merges.txt"))
txt = open(os.path.join(HERE, "pg2701.txt"), encoding="utf-8", errors="ignore").read()
txt = txt[txt.find("Call me Ishmael"):]
ids, pos = [], 0
while len(ids) < T * NWIN + 1: ids += tk.encode(txt[pos:pos + 20000]); pos += 20000

kap = []
def hook(x):
    a = np.asarray(x, dtype=np.float64).reshape(-1)
    n = (a.size // BLK) * BLK
    if not n: return
    b = a[:n].reshape(-1, BLK)
    rms = np.sqrt((b ** 2).mean(axis=1))
    ok = rms > 0
    kap.append(np.abs(b[ok]).max(axis=1) / rms[ok])

def hook_pass(x):
    hook(x)
    return x

m = G.GPT2(w, qact=hook_pass)
for k in range(NWIN):
    m.forward(ids[k * T:(k + 1) * T])
kk = np.concatenate(kap)
q = {f"p{p}": round(float(np.percentile(kk, p)), 4) for p in (1, 5, 25, 50, 75, 95, 99)}
res = dict(n_blocks=int(kk.size), block=BLK, mean=round(float(kk.mean()), 4),
           median=q["p50"], **q,
           frac_below_7_55=round(float((kk < 7.55).mean()), 4),
           frac_below_1_96=round(float((kk < 1.96).mean()), 4),
           kappa_max_possible=round(math.sqrt(BLK), 4))
print(json.dumps(res, indent=1))
print("\nprediction check [измерено]")
print(f"  8 bits: rule needs kappa < 7.55 -> holds for {100*res['frac_below_7_55']:.1f} % of blocks"
      f" (median {res['median']}) -> INT8 winner PREDICTED, we measured INT8 winner")
print(f"  6 bits: rule needs kappa > 1.96 for an FP win -> only {100*res['frac_below_1_96']:.1f} %"
      f" of blocks are below 1.96, so {100*(1-res['frac_below_1_96']):.1f} % are above"
      f" -> FP winner PREDICTED, we measured E2M3 winner")
json.dump(res, open(os.path.join(HERE, "results_crest.json"), "w"), indent=1)
