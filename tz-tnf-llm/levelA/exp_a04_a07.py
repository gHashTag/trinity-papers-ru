#!/usr/bin/env python3
"""Level A experiments A04-A07: FMA, accumulator modes, packing, format selector."""
import json, math, random, sys, time
from fractions import Fraction
import numpy as np
sys.path.insert(0, '/home/user/workspace/levelA')
import tnf_ref as T
from exp_a01_a03 import tef_neg, tef_sub

SEED = 20260819
OUT = {}

# ---------------- EXP-A04: fused vs separate ----------------
def tef_fma(f, a, b, c):
    if T.is_special(f, a) or T.is_special(f, b) or T.is_special(f, c):
        return (f.offset_max << f.exp_shift) | 1
    return T.encode(f, T.decode(f, a) * T.decode(f, b) + T.decode(f, c))

def a04():
    rnd = random.Random(SEED)
    rows = []
    for name in (8, 16, 32, 64):
        f = T.LADDER[name]
        klim = max(1, int(f.exp_offset * 0.10))
        mb = min(f.mant_bits, 30)
        def rv():
            k = rnd.randint(-klim, klim)
            m = Fraction(rnd.randint(0, 1 << mb), 1 << mb)
            s = 1 if rnd.random() < .5 else -1
            return s * (Fraction(1) + m) * (Fraction(2) ** k)
        n, diff, worst = 3000, 0, 0.0
        for _ in range(n):
            a, b, c = (T.encode(f, rv()) for _ in range(3))
            fused = tef_fma(f, a, b, c)
            split = T.tef_add(f, T.tef_mul(f, a, b), c)
            if fused != split:
                diff += 1
                exact = T.decode(f, a) * T.decode(f, b) + T.decode(f, c)
                if exact != 0:
                    ef = abs(T.decode(f, fused) - exact) / abs(exact)
                    es = abs(T.decode(f, split) - exact) / abs(exact)
                    worst = max(worst, float(es - ef))
        rows.append(dict(rung=name, triples=n, disagreements=diff,
                         disagreement_rate=diff / n,
                         worst_extra_error_of_split=worst))
    return rows

# ---------------- EXP-A05: four accumulator modes ----------------
def a05(nvec=80, L=512, rung=16):
    f = T.LADDER[rung]
    rng = np.random.default_rng(SEED)
    rows = {}
    # activations: TNF-encoded standard normal; weights: ternary {-1,0,+1}
    exact_all, modes = [], {k: [] for k in ('A_fp16', 'B_int32_int8act', 'C_tnf_acc', 'D_hybrid_block32')}
    for _ in range(nvec):
        x = rng.standard_normal(L)
        w = rng.choice([-1, 0, 1], size=L, p=[0.25, 0.5, 0.25])
        codes = [T.encode(f, Fraction(float(v)).limit_denominator(1 << 30)) for v in x]
        xq = [T.decode(f, c) for c in codes]              # what the format actually stores
        exact = sum(Fraction(int(wi)) * xi for wi, xi in zip(w, xq))
        exact_all.append(exact)
        # Mode A: fp16 accumulator over the same stored values
        acc = np.float16(0)
        for wi, xi in zip(w, xq):
            acc = np.float16(acc + np.float16(int(wi) * float(xi)))
        modes['A_fp16'].append(Fraction(float(acc)))
        # Mode B: int8-quantised activations, exact int32 accumulation
        s = float(np.max(np.abs([float(v) for v in xq]))) / 127.0 or 1.0
        q = np.round(np.array([float(v) for v in xq]) / s).astype(np.int32)
        modes['B_int32_int8act'].append(Fraction(int(np.dot(q, w.astype(np.int32)))) * Fraction(s).limit_denominator(1 << 40))
        # Mode C: TNF accumulator, re-encoded after every add
        acc = 0
        for wi, c in zip(w, codes):
            if wi == 0:
                continue
            term = c if wi > 0 else tef_neg(f, c)
            acc = T.tef_add(f, acc, term)
        modes['C_tnf_acc'].append(T.decode(f, acc))
        # Mode D: fp32 inside blocks of 32, re-encoded to TNF at block boundaries
        acc = 0
        for b0 in range(0, L, 32):
            part = float(sum(int(wi) * float(xi) for wi, xi in zip(w[b0:b0+32], xq[b0:b0+32])))
            acc = T.tef_add(f, acc, T.encode(f, Fraction(part).limit_denominator(1 << 30)))
        modes['D_hybrid_block32'].append(T.decode(f, acc))
    den = sum(float(e) ** 2 for e in exact_all)
    for k, v in modes.items():
        num = sum(float(a - b) ** 2 for a, b in zip(v, exact_all))
        rows[k] = dict(rel_rms_error=math.sqrt(num / den) if den else None,
                       sqnr_db=(10 * math.log10(den / num) if num else float('inf')))
    return dict(vectors=nvec, length=L, rung=rung, weights='ternary p(0)=0.5',
                reference='exact rational dot product of stored activations', modes=rows)

# ---------------- EXP-A06: packing and the price of decoding ----------------
def a06():
    LOG2_3 = math.log2(3)
    table = []
    for t in range(1, 65):
        bits = math.ceil(t * LOG2_3)
        loss = 2 ** bits - 3 ** t
        table.append(dict(trits=t, bits=bits, loss=loss, loss_odd=bool(loss % 2),
                          utilisation=3 ** t / 2 ** bits, bits_per_trit=bits / t))
    best = sorted(table, key=lambda r: (-r['utilisation'], r['trits']))[:5]
    # measured decode cost: 5 trits per byte (243/256) via a 256-entry LUT vs 2 bits/trit
    rng = np.random.default_rng(SEED)
    N = 5_000_000
    trits = rng.integers(0, 3, size=N, dtype=np.uint8)
    g = trits[: (N // 5) * 5].reshape(-1, 5).astype(np.uint16)
    packed = (g[:, 0] + 3 * g[:, 1] + 9 * g[:, 2] + 27 * g[:, 3] + 81 * g[:, 4]).astype(np.uint8)
    lut = np.zeros((256, 5), dtype=np.uint8)
    for v in range(243):
        x = v
        for j in range(5):
            lut[v, j] = x % 3
            x //= 3
    t0 = time.perf_counter(); out5 = lut[packed].reshape(-1); t1 = time.perf_counter()
    assert np.array_equal(out5, trits[: out5.size])
    two = trits.astype(np.uint8)
    p2 = (two[0::4] | (two[1::4] << 2) | (two[2::4] << 4) | (two[3::4] << 6))
    t2 = time.perf_counter()
    out2 = np.stack([p2 & 3, (p2 >> 2) & 3, (p2 >> 4) & 3, (p2 >> 6) & 3], axis=1).reshape(-1)
    t3 = time.perf_counter()
    assert np.array_equal(out2, trits[: out2.size])
    params = 2_031_000_000
    return dict(table_head=table[:12], best_utilisation=best,
                theoretical_bits_per_trit=LOG2_3,
                decode_ns_per_trit_base3_lut=(t1 - t0) * 1e9 / out5.size,
                decode_ns_per_trit_2bit=(t3 - t2) * 1e9 / out2.size,
                model_bytes_2bit=params * 2 / 8, model_bytes_base3=params * 1.6 / 8,
                model_bytes_theoretical=params * LOG2_3 / 8)

# ---------------- EXP-A07: format selector over a candidate catalogue ----------------
def q_int(x, bits):
    s = np.max(np.abs(x)) / (2 ** (bits - 1) - 1)
    if s == 0: return x.copy()
    return np.clip(np.round(x / s), -(2 ** (bits - 1) - 1), 2 ** (bits - 1) - 1) * s

def q_ternary(x):
    s = np.mean(np.abs(x))
    if s == 0: return x.copy()
    return np.clip(np.round(x / s), -1, 1) * s

def fp8_table(e_bits, m_bits):
    vals = set([0.0])
    bias = 2 ** (e_bits - 1) - 1
    for e in range(0, 2 ** e_bits - 1):
        for m in range(2 ** m_bits):
            sig = (1 + m / 2 ** m_bits) if e > 0 else (m / 2 ** m_bits)
            ex = (e - bias) if e > 0 else (1 - bias)
            v = sig * 2.0 ** ex
            vals.add(v); vals.add(-v)
    return np.array(sorted(vals))

def q_table(x, tab):
    idx = np.searchsorted(tab, x)
    idx = np.clip(idx, 1, len(tab) - 1)
    lo, hi = tab[idx - 1], tab[idx]
    return np.where(np.abs(x - lo) <= np.abs(hi - x), lo, hi)

def q_tnf(x, fmt):
    out = np.empty_like(x)
    for i, v in enumerate(x):
        out[i] = float(T.decode(fmt, T.encode(fmt, Fraction(float(v)).limit_denominator(1 << 40))))
    return out

def sqnr(x, y):
    num = float(np.sum((x - y) ** 2)); den = float(np.sum(x ** 2))
    return 10 * math.log10(den / num) if num > 0 else float('inf')

def a07(n=4096):
    rng = np.random.default_rng(SEED)
    dists = dict(
        uniform=rng.uniform(-1, 1, n),
        gaussian=rng.standard_normal(n),
        heavy_t3=rng.standard_t(3, n),
        laplace_weightlike=rng.laplace(0, 0.05, n),
    )
    e4m3, e5m2 = fp8_table(4, 3), fp8_table(5, 2)
    cands = {
        'ternary_1.585b': (math.log2(3), q_ternary),
        'int4': (4.0, lambda x: q_int(x, 4)),
        'int8': (8.0, lambda x: q_int(x, 8)),
        'fp8_e4m3': (8.0, lambda x: q_table(x, e4m3)),
        'fp8_e5m2': (8.0, lambda x: q_table(x, e5m2)),
        'bfloat16': (16.0, lambda x: bf16(x)),
        'float16': (16.0, lambda x: x.astype(np.float16).astype(np.float64)),
        'tnf16_true_4_8': (16.0, lambda x: q_tnf(x, T.TNFFormat(4, 8))),
        'tnf17_named16_4_9': (17.0, lambda x: q_tnf(x, T.TNFFormat(4, 9))),
        'int16': (16.0, lambda x: q_int(x, 16)),
    }
    res = {}
    for dname, x in dists.items():
        row = {}
        for cname, (bits, fn) in cands.items():
            y = np.asarray(fn(x), dtype=np.float64)
            row[cname] = dict(bits=bits, sqnr_db=sqnr(x, y))
        # Pareto front: minimise bits, maximise sqnr
        items = sorted(row.items(), key=lambda kv: (kv[1]['bits'], -kv[1]['sqnr_db']))
        front, best = [], -1e9
        for cname, r in items:
            if r['sqnr_db'] > best:
                front.append(cname); best = r['sqnr_db']
        res[dname] = dict(formats=row, pareto_front=front,
                          winner_at_8b=max((c for c in row if row[c]['bits'] <= 8),
                                           key=lambda c: row[c]['sqnr_db']),
                          winner_at_16b=max((c for c in row if row[c]['bits'] <= 16),
                                            key=lambda c: row[c]['sqnr_db']))
    return res

def bf16(x):
    # round-to-nearest-even to 8 explicit mantissa bits
    u = np.ascontiguousarray(x, dtype=np.float32).view(np.uint32).astype(np.uint64)
    lsb = (u >> 16) & 1
    rounded = (u + 0x7FFF + lsb) & 0xFFFF0000
    return rounded.astype(np.uint32).view(np.float32).astype(np.float64)

if __name__ == '__main__':
    OUT['exp_a04_fma'] = a04(); print('A04 done')
    OUT['exp_a05_accumulator'] = a05(); print('A05 done')
    OUT['exp_a06_packing'] = a06(); print('A06 done')
    OUT['exp_a07_selector'] = a07(); print('A07 done')
    json.dump(OUT, open('/home/user/workspace/levelA/results_a04_a07.json', 'w'), indent=1)
    for r in OUT['exp_a04_fma']:
        print('A04 TNF%-5d disagree %5d/%d = %.3f  worst extra error of split: %.3e'
              % (r['rung'], r['disagreements'], r['triples'], r['disagreement_rate'],
                 r['worst_extra_error_of_split']))
    for k, v in OUT['exp_a05_accumulator']['modes'].items():
        print('A05 %-18s rel_rms=%.3e  sqnr=%.2f dB' % (k, v['rel_rms_error'], v['sqnr_db']))
    p = OUT['exp_a06_packing']
    print('A06 best utilisation:', [(b['trits'], b['bits'], round(b['utilisation'], 4)) for b in p['best_utilisation']])
    print('A06 decode ns/trit  base3-LUT=%.3f  2bit=%.3f' % (p['decode_ns_per_trit_base3_lut'], p['decode_ns_per_trit_2bit']))
    print('A06 model MB 2bit=%.1f base3=%.1f theory=%.1f' % (p['model_bytes_2bit']/1e6, p['model_bytes_base3']/1e6, p['model_bytes_theoretical']/1e6))
    for d, r in OUT['exp_a07_selector'].items():
        print('A07 %-18s <=8b winner: %-14s <=16b winner: %-18s front: %s'
              % (d, r['winner_at_8b'], r['winner_at_16b'], ','.join(r['pareto_front'])))
