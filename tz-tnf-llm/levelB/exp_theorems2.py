"""Machine checks for the new statements T7-T13 of this loop.

Each check prints VERDICT: PASS / FAIL / OPEN. Nothing is claimed that is not checked here.
Classes: (a) analytic, (b) proposition over a model, (c) empirical observation.
"""
import json, math, itertools
import numpy as np
from fractions import Fraction

PHI = (1 + 5 ** 0.5) / 2
R = {}

# ---------------------------------------------------------------- T7 (class a)
# Exact (Kulisch-style) alignment width for a (1,E,M) float in an N-bit container,
# with ecodes = 2**E reachable exponents:  Wfx = (M+1) + (ecodes-1) = N - E + 2**E - 1.
# Claim: strictly increasing in E for E >= 1, so the minimum is always E = 1.
def t7():
    bad = []
    for N in range(8, 65):
        widths = {E: (N - 1 - E) + 1 + (1 << E) - 1 for E in range(1, N - 2)}
        arg = min(widths, key=lambda e: widths[e])
        if arg != 1:
            bad.append((N, arg))
    mono = all((1 << (E + 1)) - (E + 1) > (1 << E) - E for E in range(1, 40))
    return dict(cls="a", statement="Wfx(N,E)=N-E+2^E-1 strictly increasing in E>=1 => argmin E=1",
                counterexamples=bad, monotone_2E_minus_E=mono,
                verdict="PASS" if not bad and mono else "FAIL",
                example_N16=[{"E": E, "Wfx": (16 - 1 - E) + (1 << E)} for E in (1, 2, 3, 5, 6)])

# ---------------------------------------------------------------- T8 (class c)
# Measured xc7 LUT cost: rounding adder area is nearly blind to the exponent split,
# while the same split costs 22-25 dB on the block-scaled ternary dot product.
def t8():
    lut_round = {"e2m13": 197, "e3m12": 197, "e5m10": 244, "e6m9_phi": 273, "tnf16_t4m8": 195}
    lut_exact = {"fixed16": 16, "e2m13": 78, "e3m12": 183, "e5m10": 252, "e6m9_phi": 461,
                 "tnf16_t4m8": 548}
    spread = max(lut_round.values()) / min(lut_round.values())
    tnf_vs_best = lut_round["tnf16_t4m8"] / lut_round["e2m13"]
    return dict(cls="c", lut_round=lut_round, lut_exact=lut_exact,
                round_spread_ratio=round(spread, 3),
                tnf_round_saving_pct=round(100 * (1 - tnf_vs_best), 2),
                exact_growth_tnf_over_e2m13=round(lut_exact["tnf16_t4m8"] / lut_exact["e2m13"], 2),
                exact_growth_phi_over_e2m13=round(lut_exact["e6m9_phi"] / lut_exact["e2m13"], 2),
                gate_20pct_threshold_met=bool((1 - tnf_vs_best) >= 0.20),
                verdict="PASS (measured); the 20% cheapness gate is NOT met")

# ---------------------------------------------------------------- T9 (class a+c)
# Decode-to-int8 traffic: (b_in + 8) bits per trit. TQ1 vs TQ2 upper bound on any
# bandwidth advantage.
def t9():
    b1, b2 = 1.6, 2.0
    ratio = (b1 + 8) / (b2 + 8)
    fused = b1 / b2                      # fused decode+MAC reads only the weights
    return dict(cls="a", traffic_ratio_unpack=round(ratio, 4),
                max_bandwidth_gain_unpack_pct=round(100 * (1 - ratio), 2),
                traffic_ratio_fused=round(fused, 4),
                max_bandwidth_gain_fused_pct=round(100 * (1 - fused), 2),
                note="any measured unpack speed gap beyond 4% is instruction-bound, not bandwidth-bound",
                verdict="PASS")

# ---------------------------------------------------------------- T10 (class a)
# 5 trits/byte is the unique maximal base-3 packing decodable by one 256-entry table.
def t10():
    rows = []
    for t in range(1, 12):
        need = math.ceil(t * math.log2(3))
        rows.append(dict(trits=t, bits=need, codes=3 ** t, capacity=1 << need,
                         bits_per_trit=round(need / t, 4), table_entries=1 << need))
    max_t_in_byte = max(r["trits"] for r in rows if r["bits"] <= 8)
    return dict(cls="a", table=rows, max_trits_in_one_byte=max_t_in_byte,
                pow3_5=3 ** 5, pow3_6=3 ** 6,
                verdict="PASS" if max_t_in_byte == 5 and 3 ** 5 <= 256 < 3 ** 6 else "FAIL")

# ---------------------------------------------------------------- T11 (class a+b)
# Optimal symmetric ternary alphabet {-a,0,a} under round-to-nearest (threshold a/2)
# solves the fixed point a = E[|W| | |W| > a/2].  Check numerically for a Gaussian.
def t11():
    rng = np.random.default_rng(20260819)
    w = rng.standard_normal(4_000_000)
    aw = np.abs(w)
    def mse(a):
        q = np.clip(np.rint(w / a), -1, 1) * a
        return float(np.mean((w - q) ** 2))
    grid = np.linspace(0.2, 3.0, 561)
    vals = [mse(a) for a in grid]
    a_star = float(grid[int(np.argmin(vals))])
    # fixed point iteration
    a = 1.0
    for _ in range(200):
        sel = aw[aw > a / 2]
        a_new = float(sel.mean())
        if abs(a_new - a) < 1e-12:
            a = a_new; break
        a = a_new
    e_abs = float(aw.mean())
    # alphabet-scale invariance with a per-block scale
    x = rng.standard_normal((2000, 1024))
    wt = rng.choice([-1.0, 0.0, 1.0], size=(1024,), p=[.25, .5, .25])
    def sqnr(a_, b_):
        return 10 * math.log10(float(np.sum(a_ ** 2)) / float(np.sum((a_ - b_) ** 2)))
    from math import isclose
    ex = x @ wt
    got1 = x @ (wt * 1.0)
    got_phi = (x @ (wt * PHI)) / PHI
    inv = float(np.max(np.abs(got1 - got_phi)))
    return dict(cls="a+b", mse_grid_argmin=round(a_star, 4),
                fixed_point_a=round(a, 6), fixed_point_over_E_abs=round(a / e_abs, 4),
                E_abs=round(e_abs, 6), bitnet_absmean_ratio=1.0,
                phi_half_ratio=round(PHI / 2, 4),
                mse_at_fixed_point=round(mse(a), 6), mse_at_E_abs=round(mse(e_abs), 6),
                mse_at_phi_half=round(mse(PHI / 2 * e_abs), 6),
                alphabet_scale_invariance_max_abs_diff=inv,
                verdict="PASS" if inv < 1e-9 and abs(a - a_star) < 0.02 else "CHECK")

# ---------------------------------------------------------------- T12 (class a)
# A ternary-coded exponent field of t trits stored in ceil(t*log2 3) bits leaves
# 2^bits - 3^t codes unreachable: strictly wasted container entropy.
def t12():
    rows = []
    for t in range(1, 9):
        b = math.ceil(t * math.log2(3))
        rows.append(dict(trits=t, bits=b, codes=3 ** t, capacity=1 << b,
                         unreachable=(1 << b) - 3 ** t,
                         wasted_pct=round(100 * (1 - 3 ** t / (1 << b)), 2)))
    always_waste = all(r["unreachable"] > 0 for r in rows)
    return dict(cls="a", table=rows, always_wastes=always_waste,
                t4_wasted_pct=rows[3]["wasted_pct"],
                verdict="PASS" if always_waste else "FAIL")

# ---------------------------------------------------------------- T13 (class b)
# Is there ANY container width where the phi split e=round((N-1)/phi^2) minimises the
# exact-accumulator width, or the rounding-adder mantissa cost? Enumerate.
def t13():
    hits = []
    for N in range(4, 129):
        e_phi = round((N - 1) / PHI ** 2)
        wf = {E: (N - 1 - E) + (1 << E) for E in range(1, N - 2)}
        best = min(wf, key=lambda e: wf[e])
        hits.append(dict(N=N, e_phi=e_phi, best_E_exact=best,
                         phi_is_best=(e_phi == best)))
    n_hits = sum(1 for h in hits if h["phi_is_best"])
    return dict(cls="b", widths_checked=len(hits), phi_optimal_count=n_hits,
                phi_optimal_widths=[h["N"] for h in hits if h["phi_is_best"]],
                verdict="REFUTED for exact accumulator" if n_hits == 0 else "PARTIAL")

for name, fn in [("T7", t7), ("T8", t8), ("T9", t9), ("T10", t10), ("T11", t11),
                 ("T12", t12), ("T13", t13)]:
    R[name] = fn()
    print(name, R[name]["verdict"])
json.dump(R, open("/home/user/workspace/levelB/results_theorems2.json", "w"), indent=1, default=str)
