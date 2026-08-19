#!/usr/bin/env python3
"""tri-fmt: pick and check a number format for a ternary-weight layer.

Subcommands
  select   --bits N [--file data.npy | --dist NAME]   recommend a format from measured rules
  sweep    --bits N [--file ...]                      full (e,m) sweep on the ternary dot task
  pack     --params 2.031e9                           packing options and model size
  crest    --file data.npy                            crest factor and the int-vs-float verdict
Rules are calibrated on measurements in results_*.json of this directory; every printed
number is either recomputed here or labelled as a calibrated threshold.
"""
import argparse, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp_ternary_task import quant_float, sqnr, DISTS, PHI
from exp_best_number import q_fixed, q_block_float

CREST_THRESHOLD_DB = 22.0     # calibrated 19.08.2026, 7/7 on the fair scaled comparison

def load(args):
    if getattr(args, 'file', None):
        x = np.load(args.file).astype(np.float64).reshape(-1)
    else:
        x = DISTS[args.dist](np.random.default_rng(20260819), 200_000)
    return x

def crest_db(x):
    return 20 * math.log10(float(np.max(np.abs(x))) / float(np.sqrt(np.mean(x ** 2))))

def cmd_crest(args):
    x = load(args); cf = crest_db(x)
    print(f'crest factor      : {cf:.2f} dB')
    print(f'threshold         : {CREST_THRESHOLD_DB:.1f} dB [calibrated]')
    print('verdict           :', 'fixed point / int wins' if cf < CREST_THRESHOLD_DB else 'float with an exponent wins')

def ternary_dot_sqnr(x, q, nvec=60, L=1024, seed=20260819):
    rng = np.random.default_rng(seed)
    ex, got = np.empty(nvec), np.empty(nvec)
    n = min(L, len(x))
    for i in range(nvec):
        v = x[rng.integers(0, len(x), n)]
        w = rng.choice([-1.0, 0.0, 1.0], size=n, p=[.25, .5, .25])
        ex[i] = float(np.dot(w, v)); got[i] = float(np.dot(w, q(v)))
    return sqnr(ex, got)

def cmd_sweep(args):
    x = load(args); N = args.bits
    rows = {'fixed_per_tensor': ternary_dot_sqnr(x, lambda v: q_fixed(v, N)),
            'fixed_block32': ternary_dot_sqnr(x, lambda v: q_fixed(v, N, block=32))}
    for e in range(1, min(N - 1, 9)):
        m = N - 1 - e
        if m < 1: continue
        rows[f'float_e{e}_m{m}'] = ternary_dot_sqnr(x, lambda v, e=e, m=m: quant_float(v, e, m))
        rows[f'float_e{e}_m{m}_block32'] = ternary_dot_sqnr(x, lambda v, e=e, m=m: q_block_float(v, e, m))
    phi_e = round((N - 1) / PHI ** 2)
    for k, v in sorted(rows.items(), key=lambda kv: -kv[1]):
        tag = '  <- phi rule' if k.startswith(f'float_e{phi_e}_') else ''
        print(f'{k:34s} {v:7.2f} dB{tag}')
    best = max(rows, key=rows.get)
    print(f'\nwinner: {best} ({rows[best]:.2f} dB); phi-rule split e={phi_e}')

def cmd_select(args):
    x = load(args); cf = crest_db(x); N = args.bits
    if cf < CREST_THRESHOLD_DB:
        rec = f'block-scaled fixed point, {N} bits, block 32'
    else:
        rec = f'block-scaled float e=2 m={N-3}, block 32'
    print(f'bits              : {N}')
    print(f'crest factor      : {cf:.2f} dB')
    print(f'recommendation    : {rec}')
    print(f'phi-rule split    : e={round((N-1)/PHI**2)} - measured 4.9-25.0 dB worse at N>=8 [измерено 19.08.2026]')
    print('note              : with ternary weights the multiply is a sign select, so only decode and add cost anything')

def cmd_pack(args):
    p = float(args.params); l23 = math.log2(3)
    best = max(((t, math.ceil(t * l23)) for t in range(1, 65)), key=lambda tb: 3 ** tb[0] / 2 ** tb[1])
    print(f'theoretical      : {l23:.4f} bits/trit  -> {p * l23 / 8 / 1e6:.1f} MB')
    print(f'5 trits per byte : 1.6000 bits/trit  -> {p * 1.6 / 8 / 1e6:.1f} MB  [prior art: ACL 2025 TQ1]')
    print(f'2 bits per trit  : 2.0000 bits/trit  -> {p * 2 / 8 / 1e6:.1f} MB')
    print(f'best t<=64       : t={best[0]} in {best[1]} bits, utilisation {3**best[0]/2**best[1]:.4f}')

def main():
    ap = argparse.ArgumentParser(prog='tri-fmt')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name, fn, needs_bits in (('select', cmd_select, True), ('sweep', cmd_sweep, True),
                                 ('crest', cmd_crest, False), ('pack', cmd_pack, False)):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if needs_bits: p.add_argument('--bits', type=int, required=True)
        if name != 'pack':
            p.add_argument('--file'); p.add_argument('--dist', default='gaussian', choices=list(DISTS))
        else:
            p.add_argument('--params', default='2.031e9')
    a = ap.parse_args(); a.fn(a)

if __name__ == '__main__':
    main()
