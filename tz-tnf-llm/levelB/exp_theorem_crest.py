"""T21: the crest-factor threshold of arXiv:2510.25602 is vacuous at MX block size.

Claim. For any real block x of size B, kappa(x) = max|x| / rms(x) <= sqrt(B),
with equality iff exactly one entry is nonzero.
Proof. Let m = max|x|. Then sum x_i^2 >= m^2, so rms = sqrt(sum x^2 / B) >= m/sqrt(B),
hence kappa = m/rms <= sqrt(B). Equality forces sum x^2 = m^2, i.e. every other
entry is zero. Done -- pure algebra, no distributional assumption.

Consequence. A decision rule of the form "INT wins while kappa < kappa*" is
VACUOUS (always true) whenever kappa* >= sqrt(B): no block of that size can
violate it. At the MX-mandated k = 32, sqrt(32) = 5.657, so the reported 8-bit
threshold 7.55 can never fail; the 6-bit threshold 1.96 stays active.
"""
import json, math
import numpy as np
rng = np.random.default_rng(20260819)
THRESH = {"8 bit INT/FP (2510.25602)": 7.55, "6 bit": 1.96, "MXFP4": 2.04, "NVFP4": 2.39}
out = {"bound": {}, "thresholds": {}}
print("empirical check of kappa <= sqrt(B), 200000 random blocks per size, 4 distributions")
for B in (8, 16, 32, 64, 128):
    worst = 0.0
    for dist in ("gauss", "heavy", "uniform", "spike"):
        if dist == "gauss":   x = rng.standard_normal((200000, B))
        elif dist == "heavy": x = rng.standard_t(2.0, size=(200000, B))
        elif dist == "uniform": x = rng.uniform(-1, 1, (200000, B))
        else:
            x = 1e-9 * rng.standard_normal((200000, B)); x[:, 0] = 1.0
        rms = np.sqrt((x ** 2).mean(axis=1)); ok = rms > 0
        worst = max(worst, float((np.abs(x[ok]).max(axis=1) / rms[ok]).max()))
    out["bound"][B] = dict(sqrt_B=round(math.sqrt(B), 4), max_observed=round(worst, 6),
                           holds=bool(worst <= math.sqrt(B) + 1e-9))
    print(f"  B={B:4d}  sqrt(B)={math.sqrt(B):8.4f}  max observed kappa={worst:8.4f}  "
          f"{'bound holds' if worst <= math.sqrt(B)+1e-9 else 'BOUND VIOLATED'}")
print("\nwhen is a published threshold active at all?")
for name, k in THRESH.items():
    bmin = int(math.floor(k * k)) + 1     # smallest B with sqrt(B) > k
    row = dict(threshold=k, vacuous_up_to_block=int(math.floor(k * k)), active_from_block=bmin,
               vacuous_at_mx_block_32=bool(math.sqrt(32) <= k))
    out["thresholds"][name] = row
    print(f"  {name:28s} kappa*={k:5.2f}  vacuous for B <= {row['vacuous_up_to_block']:4d}"
          f"  active from B = {bmin:4d}  at MX k=32: "
          f"{'VACUOUS' if row['vacuous_at_mx_block_32'] else 'active'}")
meas = json.load(open("results_crest.json"))
out["measured_gpt2"] = meas
print(f"\nmeasured on GPT-2 activations, block 32, {meas['n_blocks']} blocks: "
      f"median kappa {meas['median']}, p99 {meas['p99']}, max possible {meas['kappa_max_possible']}")
json.dump(out, open("results_theorem_crest.json", "w"), indent=1)
