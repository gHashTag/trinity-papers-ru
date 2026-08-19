#!/usr/bin/env python3
"""The right benchmark: a format is judged on the ternary-weight dot product, where
multiplication is a sign select and only decode + add cost anything.

Answers three questions:
  Q1  which (e, m) split of a given width is best for THIS task, and does the phi rule win?
  Q2  is the GFTernary alphabet {+phi, 0, -phi} different from {+1, 0, -1}?
  Q3  what does a base-phi (Zeckendorf) mantissa cost per bit?
"""
import json, math, sys
import numpy as np
PHI = (1 + 5 ** 0.5) / 2
SEED = 20260819
OUT = {}

# ---------- arbitrary (e, m) binary float with subnormals, round-to-nearest-even ----------
def quant_float(x, e, m, per_tensor_scale=True):
    bias = 2 ** (e - 1) - 1
    emin, emax = 1 - bias, 2 ** e - 1 - bias
    if emax > 1000:
        emax, vmax = 1000, float('inf')
    else:
        vmax = (2 - 2.0 ** -m) * 2.0 ** emax
    s = (float(np.max(np.abs(x))) / vmax) if (per_tensor_scale and np.isfinite(vmax)) else 1.0
    s = s or 1.0
    y = np.asarray(x, dtype=np.float64) / s
    ay = np.abs(y)
    with np.errstate(divide='ignore'):
        ex = np.floor(np.log2(np.where(ay > 0, ay, 1.0)))
    ex = np.clip(ex, emin, emax)
    step = 2.0 ** (ex - m)
    q = np.rint(ay / step)                      # numpy rint = round-half-to-even
    out = np.sign(y) * (q * step if not np.isfinite(vmax) else np.minimum(q * step, vmax))
    return out * s

def sqnr(a, b):
    num = float(np.sum((a - b) ** 2))
    return 10 * math.log10(float(np.sum(a ** 2)) / num) if num > 0 else float('inf')

# ---------- the task: ternary weights, activations in the candidate format ----------
def dot_task(dist_fn, e, m, nvec=200, L=1024, rng=None, per_tensor_scale=True, alphabet=1.0):
    rng = rng or np.random.default_rng(SEED)
    ex, got = np.empty(nvec), np.empty(nvec)
    for i in range(nvec):
        x = dist_fn(rng, L)
        w = rng.choice([-1.0, 0.0, 1.0], size=L, p=[.25, .5, .25]) * alphabet
        xq = quant_float(x, e, m, per_tensor_scale)
        ex[i] = float(np.dot(w, x))              # exact, unquantised activations
        got[i] = float(np.dot(w, xq))            # multiplication is a sign select: free
    return sqnr(ex, got)

DISTS = {
 'gaussian':      lambda r, n: r.standard_normal(n),
 'relu_halfnorm': lambda r, n: np.maximum(r.standard_normal(n), 0),
 'laplace':       lambda r, n: r.laplace(0, 1, n),
 'heavy_t3':      lambda r, n: r.standard_t(3, n),
 'logit_outlier': lambda r, n: np.concatenate([r.standard_normal(n - max(1, n // 128)), r.standard_normal(max(1, n // 128)) * 50]),
}

def q1(widths=(8, 16)):
    res = {}
    for N in widths:
        phi_e = round((N - 1) / PHI ** 2)
        for scale in (True, False):
            key = f'N={N},per_tensor_scale={scale}'
            rows = {}
            for dname, fn in DISTS.items():
                per_e = {}
                for e in range(2, min(N - 2, 9)):
                    m = N - 1 - e
                    if m < 1: break
                    per_e[e] = dot_task(fn, e, m, nvec=120, L=1024,
                                        rng=np.random.default_rng(SEED), per_tensor_scale=scale)
                best_e = max(per_e, key=per_e.get)
                rows[dname] = dict(sqnr_by_exponent_bits={str(k): v for k, v in per_e.items()},
                                   best_e=best_e, best_m=N - 1 - best_e, best_sqnr_db=per_e[best_e],
                                   phi_rule_e=phi_e, phi_rule_sqnr_db=per_e.get(phi_e),
                                   phi_rule_penalty_db=(per_e[best_e] - per_e[phi_e]) if phi_e in per_e else None,
                                   crest_factor_db=None)
            res[key] = rows
    # crest factors for reference
    rng = np.random.default_rng(SEED)
    cf = {d: 20 * math.log10(float(np.max(np.abs(fn(rng, 200000)))) /
                             float(np.sqrt(np.mean(fn(np.random.default_rng(SEED), 200000) ** 2))))
          for d, fn in DISTS.items()}
    return dict(phi_rule='e = round((N-1)/phi^2)', crest_factors_db=cf, results=res)

def q2(nvec=200, L=1024, e=5, m=10):
    """Alphabet {+phi,0,-phi} versus {+1,0,-1}, and the MSE-optimal alphabet scale."""
    rng = np.random.default_rng(SEED)
    a = dot_task(DISTS['gaussian'], e, m, nvec=nvec, L=L, rng=np.random.default_rng(SEED), alphabet=1.0)
    b = dot_task(DISTS['gaussian'], e, m, nvec=nvec, L=L, rng=np.random.default_rng(SEED), alphabet=PHI)
    # optimal ternary alphabet scale for weight reconstruction
    W = rng.standard_normal(200000)
    sweep = {}
    for ratio in np.arange(0.30, 2.01, 0.02):
        s = ratio * float(np.mean(np.abs(W)))
        Tq = np.clip(np.rint(W / s), -1, 1)
        sweep[round(float(ratio), 2)] = float(np.mean((W - s * Tq) ** 2))
    best_ratio = min(sweep, key=sweep.get)
    return dict(sqnr_alphabet_1_db=a, sqnr_alphabet_phi_db=b,
                difference_db=b - a,
                statement='a per-tensor scale absorbs any global alphabet factor, so +-phi cannot differ from +-1',
                optimal_scale_over_mean_abs=best_ratio,
                mse_at_optimal=sweep[best_ratio], mse_at_mean_abs=sweep[1.0],
                mse_at_phi_over_2=sweep[min(sweep, key=lambda r: abs(r - PHI / 2))],
                phi_over_2=PHI / 2, sweep={str(k): v for k, v in sweep.items()})

def q3(nmax=32, m_bits=10, n=200000):
    """Base-phi / Zeckendorf mantissa: capacity per digit and measured SQNR per bit."""
    F = [1, 1]
    while len(F) < nmax + 4: F.append(F[-1] + F[-2])
    cap = [dict(digits=k, valid_strings=F[k + 2], bits_of_entropy=math.log2(F[k + 2]),
                bits_per_digit=math.log2(F[k + 2]) / k) for k in range(1, nmax + 1)]
    # Zeckendorf mantissa on [1,2): digits d_i in {0,1}, no two adjacent, value = 1 + sum d_i phi^-i
    def zeck_levels(k):
        levels, stack = [], [(0, 0.0, False)]
        while stack:
            i, v, prev = stack.pop()
            if i == k:
                levels.append(v); continue
            stack.append((i + 1, v, False))
            if not prev: stack.append((i + 1, v + PHI ** -(i + 1), True))
        return np.array(sorted(set(levels)))
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(n)
    rows = {}
    for k in (10, 14, 15):
        lv = 1.0 + zeck_levels(k)
        lv = lv / lv[-1] * 2.0                              # normalise to [., 2)
        # quantise |x| mantissa against the Zeckendorf level set, exponent handled in binary
        ax = np.abs(x); ex = np.floor(np.log2(np.where(ax > 0, ax, 1.0)))
        man = ax / 2.0 ** ex
        idx = np.clip(np.searchsorted(lv, man), 1, len(lv) - 1)
        lo, hi = lv[idx - 1], lv[idx]
        mq = np.where(np.abs(man - lo) <= np.abs(hi - man), lo, hi)
        y = np.sign(x) * mq * 2.0 ** ex
        rows[f'zeck_{k}_digits'] = dict(digits=k, levels=int(len(lv)),
                                        equivalent_binary_bits=math.log2(len(lv)),
                                        sqnr_db=sqnr(x, y))
    for mb in (7, 8, 10):
        y = quant_float(x, 5, mb, per_tensor_scale=False)
        rows[f'binary_{mb}_mantissa_bits'] = dict(digits=mb, levels=2 ** mb,
                                                  equivalent_binary_bits=mb, sqnr_db=sqnr(x, y))
    return dict(capacity=cap[:16], log2_phi=math.log2(PHI),
                waste_fraction=1 - math.log2(PHI), measured=rows,
                phi_multiply='multiplication by phi is a Fibonacci shift-add: phi^k = F(k)phi + F(k-1)')

if __name__ == '__main__':
    OUT['Q1_best_split_for_ternary_dot'] = q1(); print('Q1 ok')
    OUT['Q2_alphabet_phi'] = q2(); print('Q2 ok')
    OUT['Q3_base_phi_cost'] = q3(); print('Q3 ok')
    json.dump(OUT, open('/home/user/workspace/levelA/results_ternary_task.json', 'w'), indent=1)
    r = OUT['Q1_best_split_for_ternary_dot']
    print('\ncrest factors dB:', {k: round(v, 1) for k, v in r['crest_factors_db'].items()})
    for key, rows in r['results'].items():
        print('--', key, ' (phi rule e =', list(rows.values())[0]['phi_rule_e'], ')')
        for d, v in rows.items():
            print('   %-14s best e=%d m=%-2d %7.2f dB | phi-rule %7s dB | penalty %s'
                  % (d, v['best_e'], v['best_m'], v['best_sqnr_db'],
                     ('%.2f' % v['phi_rule_sqnr_db']) if v['phi_rule_sqnr_db'] is not None else 'n.a.',
                     ('%.2f dB' % v['phi_rule_penalty_db']) if v['phi_rule_penalty_db'] is not None else 'n.a.'))
    q = OUT['Q2_alphabet_phi']
    print('Q2 alphabet 1 = %.4f dB, alphabet phi = %.4f dB, difference = %.2e dB' % (q['sqnr_alphabet_1_db'], q['sqnr_alphabet_phi_db'], q['difference_db']))
    print('Q2 optimal scale / mean|W| = %.2f (BitMSE %.6f) vs 1.00 (%.6f) vs phi/2=%.3f (%.6f)'
          % (q['optimal_scale_over_mean_abs'], q['mse_at_optimal'], q['mse_at_mean_abs'], q['phi_over_2'], q['mse_at_phi_over_2']))
    q = OUT['Q3_base_phi_cost']
    print('Q3 log2(phi) = %.4f bits/digit, waste = %.1f%%' % (q['log2_phi'], 100 * q['waste_fraction']))
    for k, v in q['measured'].items():
        print('   %-26s levels=%6d  equiv bits=%5.2f  sqnr=%6.2f dB' % (k, v['levels'], v['equivalent_binary_bits'], v['sqnr_db']))
