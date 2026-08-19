#!/usr/bin/env python3
"""Level A experiments A01-A03: width rule, underflow policy, subtraction.

All numbers printed by this script are measured by running it. No value here is
quoted from a document.
"""
import json, math, random, sys
from fractions import Fraction
sys.path.insert(0, '/home/user/workspace/levelA')
import tnf_ref as T

OUT = {}

# ---------------- EXP-A01: width rule, arithmetically ----------------
def a01():
    rows = []
    for name, f in sorted(T.LADDER.items()):
        nominal = 1 + f.exp_trits + f.mant_bits          # paper notation
        stored = T.stored_width(f)                        # 1 + ceil(Et log2 3) + M
        rows.append(dict(rung=name, exp_trits=f.exp_trits, mant_bits=f.mant_bits,
                         exp_bits=f.exp_bits, nominal_sum=nominal, stored_width=stored,
                         nominal_ok=(nominal == name), stored_ok=(stored == name),
                         range_decades=round(f.range_decades(), 1)))
    # repair proposal: for each named width N pick the split that keeps >= target
    # decades of range while satisfying the STORED rule exactly.
    repair = []
    for name in sorted(T.LADDER):
        best = None
        for et in range(1, 40):
            eb = (3 ** et - 1).bit_length()
            m = name - 1 - eb
            if m < 1:
                continue
            f = T.TNFFormat(et, m)
            if T.stored_width(f) != name:
                continue
            dec = f.range_decades()
            # prefer the split with the largest mantissa that still covers +-9 decades
            # (the range where a narrow-exponent split was measured to trap values)
            score = (dec >= 9, m)
            if best is None or score > best[0]:
                best = (score, dict(rung=name, exp_trits=et, mant_bits=m,
                                    stored_width=T.stored_width(f),
                                    range_decades=round(dec, 1)))
        if best:
            repair.append(best[1])
    return dict(rows=rows,
                nominal_violations=[r['rung'] for r in rows if not r['nominal_ok']],
                stored_violations=[r['rung'] for r in rows if not r['stored_ok']],
                stored_repair=repair)

# ---------------- EXP-A02: what happens below the smallest normal ----------------
def a02():
    res = []
    for name in (8, 16, 32):
        f = T.LADDER[name]
        min_normal = Fraction(1) * 2 ** (1 - f.exp_offset)   # offset == 1, m == 0
        probes = []
        worst = 0.0
        for k in (1, 2, 5, 10, 40):
            x = min_normal / (2 ** k)
            raw = T.encode(f, x)
            back = T.decode(f, raw)
            rel = float(abs(back - x) / x)
            worst = max(worst, rel)
            probes.append(dict(k=k, x=float(x), decoded=float(back), rel_error=rel,
                               raw=raw, is_zero_code=(raw & ~(1 << f.sign_shift)) == 0))
        # is the map monotone in that region?  distinct inputs -> same code?
        codes = {T.encode(f, min_normal / (2 ** k)) for k in range(1, 20)}
        res.append(dict(rung=name, min_normal=float(min_normal), probes=probes,
                        worst_rel_error=worst, distinct_codes_below_min=len(codes)))
    return dict(current_policy='clamp offset to 1 (flush-to-min-normal, magnitude inflated)',
                measured=res)

def encode_ftz(f, value):
    """Proposed policy 1: flush to zero below the smallest normal."""
    if value == 0:
        return 0
    av = abs(Fraction(value))
    if av < Fraction(1) * 2 ** (1 - f.exp_offset):
        return (1 << f.sign_shift) if value < 0 else 0
    return T.encode(f, value)

def encode_sub(f, value):
    """Proposed policy 2: gradual subnormals at offset 0 (mantissa without hidden 1)."""
    if value == 0:
        return 0
    sign = 1 if value < 0 else 0
    av = abs(Fraction(value))
    min_normal = Fraction(1) * 2 ** (1 - f.exp_offset)
    if av >= min_normal:
        return T.encode(f, value)
    scaled = av / min_normal * f.mant
    fl = int(scaled); rem = scaled - fl
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and (fl & 1)):
        fl += 1
    if fl >= f.mant:                      # rounded up into the normal range
        return T.encode(f, value)
    return (sign << f.sign_shift) | fl    # offset 0, mantissa = subnormal payload

def decode_sub(f, raw):
    offset = (raw >> f.exp_shift) & ((1 << f.exp_bits) - 1)
    if offset != 0:
        return T.decode(f, raw)
    m = raw & (f.mant - 1)
    sign = (raw >> f.sign_shift) & 1
    v = Fraction(m, f.mant) * (Fraction(1) * 2 ** (1 - f.exp_offset))
    return -v if sign else v

def a02b():
    """Measure the three policies on values that live near/below the smallest normal."""
    rnd = random.Random(20260819)
    out = []
    for name in (8, 16):
        f = T.LADDER[name]
        mn = Fraction(1) * 2 ** (1 - f.exp_offset)
        xs = [mn * Fraction(rnd.randint(1, 4000), 4000) for _ in range(2000)]
        stats = {}
        for label, enc, dec in (('clamp(current)', T.encode, T.decode),
                                ('flush_to_zero', encode_ftz, T.decode),
                                ('subnormal', encode_sub, decode_sub)):
            num = den = 0.0
            worst = 0.0
            for x in xs:
                y = dec(f, enc(f, x))
                e = float(x - y) ** 2
                num += e; den += float(x) ** 2
                worst = max(worst, float(abs(x - y) / x))
            stats[label] = dict(sqnr_db=(10 * math.log10(den / num) if num else float('inf')),
                                worst_rel_error=worst)
        out.append(dict(rung=name, n=len(xs), policies=stats))
    return out

# ---------------- EXP-A03: subtraction ----------------
def tef_neg(f, a):
    if T.is_special(f, a):
        return a
    if (a & ~(1 << f.sign_shift)) == 0:
        return a                       # -0 == 0 in this encoding
    return a ^ (1 << f.sign_shift)

def tef_sub(f, a, b):
    if T.is_special(f, a) or T.is_special(f, b):
        return (f.offset_max << f.exp_shift) | 1
    return T.encode(f, T.decode(f, a) - T.decode(f, b))

def a03():
    rnd = random.Random(4242)
    rows = []
    for name, f in sorted(T.LADDER.items()):
        klim = max(1, int(f.exp_offset * 0.29))
        mbits = min(f.mant_bits, 30)
        def rv():
            k = rnd.randint(-klim, klim)
            m = Fraction(rnd.randint(0, 1 << mbits), 1 << mbits)
            s = 1 if rnd.random() < .5 else -1
            return s * (Fraction(1) + m) * (Fraction(2) ** k)
        n = 1500
        bad_neg = bad_self = bad_anti = bad_via_add = 0
        for _ in range(n):
            x, y = rv(), rv()
            a, b = T.encode(f, x), T.encode(f, y)
            if T.decode(f, tef_neg(f, a)) != -T.decode(f, a):
                bad_neg += 1
            if tef_sub(f, a, a) != 0:
                bad_self += 1
            if tef_sub(f, a, b) != tef_neg(f, tef_sub(f, b, a)):
                bad_anti += 1
            if tef_sub(f, a, b) != T.tef_add(f, a, tef_neg(f, b)):
                bad_via_add += 1
        rows.append(dict(rung=name, pairs=n, neg_violations=bad_neg,
                         self_sub_nonzero=bad_self, antisymmetry_violations=bad_anti,
                         sub_ne_add_of_neg=bad_via_add))
    return rows

if __name__ == '__main__':
    OUT['exp_a01_width_rule'] = a01()
    OUT['exp_a02_underflow'] = a02()
    OUT['exp_a02b_policy_comparison'] = a02b()
    OUT['exp_a03_subtraction'] = a03()
    json.dump(OUT, open('/home/user/workspace/levelA/results_a01_a03.json', 'w'),
              indent=1, ensure_ascii=False)
    r = OUT['exp_a01_width_rule']
    print('A01 nominal violations:', r['nominal_violations'])
    print('A01 stored violations :', r['stored_violations'])
    for row in r['rows']:
        print('   TNF%-5d Et=%-2d M=%-4d exp_bits=%-2d nominal=%-5d stored=%-5d dec=%s'
              % (row['rung'], row['exp_trits'], row['mant_bits'], row['exp_bits'],
                 row['nominal_sum'], row['stored_width'], row['range_decades']))
    print('A01 repair (stored rule exact):')
    for row in r['stored_repair']:
        print('   TNF%-5d -> Et=%-2d M=%-4d stored=%-5d dec=%s'
              % (row['rung'], row['exp_trits'], row['mant_bits'], row['stored_width'], row['range_decades']))
    print('A02:', OUT['exp_a02_underflow']['current_policy'])
    for m in OUT['exp_a02_underflow']['measured']:
        print('   TNF%-4d min_normal=%.3e worst_rel_err=%.3f distinct_codes_below=%d'
              % (m['rung'], m['min_normal'], m['worst_rel_error'], m['distinct_codes_below_min']))
    for m in OUT['exp_a02b_policy_comparison']:
        print('   TNF%-4d' % m['rung'], {k: (round(v['sqnr_db'], 2), round(v['worst_rel_error'], 3))
                                         for k, v in m['policies'].items()})
    print('A03:')
    for row in OUT['exp_a03_subtraction']:
        print('   TNF%-5d neg=%d self=%d anti=%d sub!=add(-b)=%d'
              % (row['rung'], row['neg_violations'], row['self_sub_nonzero'],
                 row['antisymmetry_violations'], row['sub_ne_add_of_neg']))
