#!/usr/bin/env python3
"""Constructive answer: at each activation bit budget, which number wins the ternary-weight
dot product - fixed point, minimal-exponent float, the phi split, or block scaling?"""
import json, math
import numpy as np
from exp_ternary_task import quant_float, sqnr, DISTS, PHI
SEED = 20260819

def q_fixed(x, bits, block=0):
    lo = -(2 ** (bits - 1) - 1); hi = 2 ** (bits - 1) - 1
    if block:
        y = x.copy().reshape(-1)
        n = (len(y) // block) * block
        v = y[:n].reshape(-1, block)
        s = np.max(np.abs(v), axis=1, keepdims=True) / hi
        s[s == 0] = 1.0
        v = np.clip(np.rint(v / s), lo, hi) * s
        out = y.copy(); out[:n] = v.reshape(-1); return out
    s = float(np.max(np.abs(x))) / hi or 1.0
    return np.clip(np.rint(x / s), lo, hi) * s

def q_block_float(x, e, m, block=32):
    y = x.copy().reshape(-1); n = (len(y) // block) * block
    v = y[:n].reshape(-1, block)
    out = np.empty_like(v)
    for i in range(v.shape[0]):
        out[i] = quant_float(v[i], e, m, per_tensor_scale=True)
    z = y.copy(); z[:n] = out.reshape(-1); return z

def run(nvec=150, L=1024):
    res = {}
    for N in (4, 6, 8, 12, 16):
        phi_e = round((N - 1) / PHI ** 2)
        cands = {'fixed_per_tensor': lambda x, N=N: q_fixed(x, N),
                 'fixed_block32': lambda x, N=N: q_fixed(x, N, block=32)}
        for e in (2, 3, 4, phi_e):
            m = N - 1 - e
            if m >= 1:
                cands[f'float_e{e}_m{m}' + ('_PHI' if e == phi_e else '')] = (lambda x, e=e, m=m: quant_float(x, e, m))
                cands[f'float_e{e}_m{m}_block32' + ('_PHI' if e == phi_e else '')] = (lambda x, e=e, m=m: q_block_float(x, e, m))
        table = {}
        for dname, fn in DISTS.items():
            row = {}
            for cname, q in cands.items():
                rng = np.random.default_rng(SEED)
                ex, got = np.empty(nvec), np.empty(nvec)
                for i in range(nvec):
                    x = fn(rng, L)
                    w = rng.choice([-1.0, 0.0, 1.0], size=L, p=[.25, .5, .25])
                    ex[i] = float(np.dot(w, x)); got[i] = float(np.dot(w, q(x)))
                row[cname] = sqnr(ex, got)
            table[dname] = dict(sqnr_db=row, winner=max(row, key=row.get),
                                phi_variant_gap_db=max(row.values()) - max(
                                    (v for k, v in row.items() if k.endswith('PHI') or '_PHI' in k), default=float('nan')))
        res[f'N={N}'] = dict(phi_rule_e=phi_e, per_distribution=table)
    return res

if __name__ == '__main__':
    out = run()
    json.dump(out, open('/home/user/workspace/levelA/results_best_number.json', 'w'), indent=1)
    for N, r in out.items():
        print('==', N, '(phi rule e =', r['phi_rule_e'], ')')
        for d, t in r['per_distribution'].items():
            top = sorted(t['sqnr_db'].items(), key=lambda kv: -kv[1])[:3]
            print('   %-14s winner %-28s %6.2f dB | 2nd %-24s %6.2f | phi gap %5.2f dB'
                  % (d, top[0][0], top[0][1], top[1][0], top[1][1], t['phi_variant_gap_db']))
