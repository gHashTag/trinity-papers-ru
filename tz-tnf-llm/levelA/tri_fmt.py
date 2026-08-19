#!/usr/bin/env python3
"""tri-fmt: pick and check a number format for a ternary-weight layer.

Subcommands
  select   --bits N [--file data.npy | --dist NAME]   recommend a format from measured rules
  sweep    --bits N [--file ...]                      full (e,m) sweep on the ternary dot task
  pack     --params 2.031e9                           packing options and model size
  crest    --file data.npy                            crest factor and the int-vs-float verdict
  hwcost   --bits N [--codes C]                       exact-accumulator width and measured xc7 LUT cost
  alphabet [--dist NAME]                              MSE-optimal ternary alphabet (fixed point a = E[|W| : |W|>a/2])
  pack3    [--max-trits T]                            base-3 packing table: bits/trit, table decode, wasted codes
  downstream                                          measured perplexity deltas per activation format
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

LUT_XC7 = {   # measured 19.08.2026, yosys synth_xilinx -family xc7, verified RTL, single add
 'exact': {'fixed16': 16, 'e2m13': 78, 'e3m12': 183, 'e5m10': 252, 'e6m9_PHI': 461, 'tnf16_t4m8': 548},
 'round': {'e2m13': 197, 'e3m12': 197, 'e5m10': 244, 'e6m9_PHI': 273, 'tnf16_t4m8': 195},
}

def cmd_hwcost(args):
    N = args.bits; codes = args.codes
    print(f'container            : {N} bits')
    print('exact-accumulator width  Wfx = (M+1) + (codes-1),  M = N-1-E')
    rows = []
    for E in range(1, min(9, N - 2)):
        c = codes or (1 << E)
        rows.append((E, N - 1 - E, c, (N - E) + c - 1))
    for E, M, c, w in rows:
        tag = '  <- phi rule' if E == round((N - 1) / PHI ** 2) else ''
        print(f'   E={E} M={M} codes={c:4d} -> Wfx={w:4d}{tag}')
    print('minimum is always E=1 [proved T7, enumerated N=8..64]')
    print('measured xc7 LUT, exact accumulator :', LUT_XC7['exact'])
    print('measured xc7 LUT, rounding adder    :', LUT_XC7['round'])
    print('rule of thumb [измерено]: at E<=3 the exact accumulator is cheaper AND bit-exact')
    print('                          (78/183 LUT vs 197 LUT); at E>=5 it turns more expensive')

def cmd_alphabet(args):
    x = load(args); ax = np.abs(x)
    a = float(ax.mean())
    for _ in range(500):
        sel = ax[ax > a / 2]
        if not sel.size: break
        a_new = float(sel.mean())
        if abs(a_new - a) < 1e-13: a = a_new; break
        a = a_new
    def mse(v):
        q = np.clip(np.rint(x / v), -1, 1) * v
        return float(np.mean((x - q) ** 2))
    e_abs = float(ax.mean())
    print(f'E|W|                 : {e_abs:.6f}')
    print(f'fixed point a*       : {a:.6f}  = {a/e_abs:.4f} * E|W|   MSE {mse(a):.6f}')
    print(f'BitNet absmean       : {e_abs:.6f}  = 1.0000 * E|W|   MSE {mse(e_abs):.6f}')
    print(f'phi/2 * E|W|         : {PHI/2*e_abs:.6f}  = {PHI/2:.4f} * E|W|   MSE {mse(PHI/2*e_abs):.6f}')
    print('alphabet {-a,0,a} scale is absorbed by a per-block scale, so {+phi,0,-phi} == {-1,0,1} [proved]')

def cmd_pack3(args):
    l23 = math.log2(3)
    print(f"{'trits':>6s}{'bits':>6s}{'codes':>8s}{'capacity':>10s}{'bits/trit':>11s}{'wasted %':>10s}{'table decode':>14s}")
    for t in range(1, args.max_trits + 1):
        b = math.ceil(t * l23); cap = 1 << b
        print(f'{t:6d}{b:6d}{3**t:8d}{cap:10d}{b/t:11.4f}{100*(1-3**t/cap):10.2f}'
              f"   {('yes, ' + str(cap) + ' entries') if b <= 8 else 'no, >256 entries':>16s}")
    print('5 trits per byte is the widest base-3 packing decodable by one 256-entry table [proved T10]')

def cmd_downstream(args):
    f = '/home/user/workspace/levelB/results_ppl.json'
    if not os.path.exists(f):
        print('no measurement file yet:', f); return
    d = json.load(open(f))
    for tag, row in d.items():
        base = row.get('fp32', {}).get('ppl')
        print('==', tag, f'(fp32 baseline ppl {base})')
        for k, v in sorted(row.items(), key=lambda kv: kv[1]['ppl']):
            dp = 100 * (v['ppl'] / base - 1) if base else float('nan')
            print(f"   {k:18s} ppl {v['ppl']:9.4f}  delta {dp:+7.3f} %   logit SQNR "
                  f"{v['logit_sqnr_db'] if v['logit_sqnr_db'] is not None else 'baseline'} dB")

def main():
    ap = argparse.ArgumentParser(prog='tri-fmt')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name, fn, needs_bits in (('select', cmd_select, True), ('sweep', cmd_sweep, True),
                                 ('crest', cmd_crest, False), ('pack', cmd_pack, False),
                                 ('hwcost', cmd_hwcost, True), ('alphabet', cmd_alphabet, False),
                                 ('pack3', cmd_pack3, False), ('downstream', cmd_downstream, False)):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        if needs_bits: p.add_argument('--bits', type=int, required=True)
        if name in ('select', 'sweep', 'crest', 'alphabet'):
            p.add_argument('--file'); p.add_argument('--dist', default='gaussian', choices=list(DISTS))
        if name == 'pack':
            p.add_argument('--params', default='2.031e9')
        if name == 'hwcost':
            p.add_argument('--codes', type=int, default=0,
                           help='reachable exponent codes, e.g. 81 for a 4-trit exponent')
        if name == 'pack3':
            p.add_argument('--max-trits', dest='max_trits', type=int, default=10)
    a = ap.parse_args(); a.fn(a)

if __name__ == '__main__':
    main()
