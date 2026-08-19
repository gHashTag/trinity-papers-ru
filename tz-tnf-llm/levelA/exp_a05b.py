#!/usr/bin/env python3
"""A05b: is the Mode D win caused by TNF, or just by blocking?

Isolates two variables the first run confounded:
  1. container width  - TNF(4,9) stores 17 bits, fp16 stores 16;
  2. blocking         - fp32 partial sums inside blocks of 32.
Adds a control where the block boundary rounds to fp16 instead of TNF.
"""
import json, math, sys
from fractions import Fraction
import numpy as np
sys.path.insert(0, '/home/user/workspace/levelA')
import tnf_ref as T
from exp_a01_a03 import tef_neg

SEED, NVEC, L = 20260819, 80, 512
rng = np.random.default_rng(SEED)
F17, F16 = T.LADDER[16], T.TRUE_LADDER[16]          # (4,9)=17 bits, (4,8)=16 bits

def run(fmt, block):
    exact_all, got = [], []
    r = np.random.default_rng(SEED)
    for _ in range(NVEC):
        x = r.standard_normal(L)
        w = r.choice([-1, 0, 1], size=L, p=[.25, .5, .25])
        codes = [T.encode(fmt, Fraction(float(v)).limit_denominator(1 << 30)) for v in x]
        xq = [T.decode(fmt, c) for c in codes]
        exact_all.append(sum(Fraction(int(a)) * b for a, b in zip(w, xq)))
        acc = 0
        if block:
            for b0 in range(0, L, block):
                part = float(sum(int(a) * float(b) for a, b in zip(w[b0:b0+block], xq[b0:b0+block])))
                acc = T.tef_add(fmt, acc, T.encode(fmt, Fraction(part).limit_denominator(1 << 30)))
        else:
            for wi, c in zip(w, codes):
                if wi:
                    acc = T.tef_add(fmt, acc, c if wi > 0 else tef_neg(fmt, c))
        got.append(T.decode(fmt, acc))
    return exact_all, got

def run_fp16_control(fmt, block):
    """Same stored activations, same blocking, fp16 container at the boundary."""
    exact_all, got = [], []
    r = np.random.default_rng(SEED)
    for _ in range(NVEC):
        x = r.standard_normal(L)
        w = r.choice([-1, 0, 1], size=L, p=[.25, .5, .25])
        xq = [T.decode(fmt, T.encode(fmt, Fraction(float(v)).limit_denominator(1 << 30))) for v in x]
        exact_all.append(sum(Fraction(int(a)) * b for a, b in zip(w, xq)))
        acc = np.float16(0)
        if block:
            for b0 in range(0, L, block):
                part = np.float16(float(sum(int(a) * float(b) for a, b in zip(w[b0:b0+block], xq[b0:b0+block]))))
                acc = np.float16(acc + part)
        else:
            for wi, xi in zip(w, xq):
                acc = np.float16(acc + np.float16(int(wi) * float(xi)))
        got.append(Fraction(float(acc)))
    return exact_all, got

def sq(exact, got):
    num = sum(float(a - b) ** 2 for a, b in zip(got, exact))
    den = sum(float(a) ** 2 for a in exact)
    return dict(rel_rms=math.sqrt(num / den), sqnr_db=10 * math.log10(den / num))

res = {}
for label, fmt in (('tnf17_4_9', F17), ('tnf16_true_4_8', F16)):
    for block in (0, 32):
        res[f'{label}_block{block}'] = sq(*run(fmt, block))
    for block in (0, 32):
        res[f'{label}_activations_fp16acc_block{block}'] = sq(*run_fp16_control(fmt, block))
json.dump(res, open('/home/user/workspace/levelA/results_a05b.json', 'w'), indent=1)
for k, v in res.items():
    print('%-42s rel_rms=%.3e sqnr=%6.2f dB' % (k, v['rel_rms'], v['sqnr_db']))
