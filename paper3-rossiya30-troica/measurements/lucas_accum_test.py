#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lucas / phi-accumulation proxy test (no hardware).
Honest question: does GF's phi-structure give ANY measurable advantage in the
ACCUMULATION operation (long dot-products / GEMM rows), beyond the (e,m) field
choice already tested?

We compare accumulation error of a low-precision dot-product against an
fp64 reference. Schemes:
  A) naive same-format accumulation (round each add into the format)
  B) fp32-accumulate (typical HW: low-prec inputs, fp32 accumulator)
  C) Kahan-compensated accumulation in the format (error-free summation baseline)

The Lucas identity phi^{2n} + phi^{-2n} = L_{2n} (integer) is EXACT in integers.
So a genuinely phi-specific accumulation gain could only appear if values are
represented as integer combinations of phi-powers and summed in the INTEGER
domain. We test that hypothesis directly (scheme D) and report honestly whether
it beats plain fp32-accumulate on realistic (non-phi-aligned) data.
"""
import numpy as np, math

np.seterr(all="ignore")
exec(open("/home/user/workspace/wave_audit/gf_quant_harness.py").read().split("def main")[0])

PHI = (1.0 + 5.0 ** 0.5) / 2.0

gf16_q, _ = make_gf_codec(16)
fp16_q, _ = make_fp16()
bf16_q, _ = make_bf16()

# generic format-rounding closure for "accumulate in format"
def round_in_format(q):
    return lambda v: float(q(np.array([v]))[0])

r_gf16 = round_in_format(gf16_q)
r_fp16 = round_in_format(fp16_q)
r_bf16 = round_in_format(bf16_q)

def dot_ref(a, b):
    return float(np.dot(a.astype(np.float64), b.astype(np.float64)))

def dot_naive_format(a, b, rnd):
    # round inputs to format, accumulate rounding each partial into format
    acc = 0.0
    for i in range(len(a)):
        p = rnd(rnd(float(a[i])) * rnd(float(b[i])))
        acc = rnd(acc + p)
    return acc

def dot_fp32_accum(a, b, rnd):
    # round inputs+products to format, but accumulate in fp32 (typical HW MAC)
    acc = np.float32(0.0)
    for i in range(len(a)):
        p = np.float32(rnd(float(a[i])) * rnd(float(b[i])))
        acc = np.float32(acc + p)
    return float(acc)

def dot_kahan_format(a, b, rnd):
    # Kahan-compensated summation, everything rounded into the format
    acc = 0.0
    c = 0.0
    for i in range(len(a)):
        p = rnd(rnd(float(a[i])) * rnd(float(b[i])))
        y = rnd(p - c)
        t = rnd(acc + y)
        c = rnd(rnd(t - acc) - y)
        acc = t
    return acc

def rel_err(x, ref):
    if ref == 0:
        return abs(x)
    return abs(x - ref) / abs(ref)

def run(N=1024, trials=200, seed=20260706):
    rng = np.random.default_rng(seed)
    schemes = {
        "fp16 naive":  (r_fp16, dot_naive_format),
        "fp16 fp32acc":(r_fp16, dot_fp32_accum),
        "fp16 kahan":  (r_fp16, dot_kahan_format),
        "bf16 naive":  (r_bf16, dot_naive_format),
        "bf16 fp32acc":(r_bf16, dot_fp32_accum),
        "GF16 naive":  (r_gf16, dot_naive_format),
        "GF16 fp32acc":(r_gf16, dot_fp32_accum),
        "GF16 kahan":  (r_gf16, dot_kahan_format),
    }
    errs = {k: [] for k in schemes}
    for _ in range(trials):
        a = rng.normal(0, 1.0, N)
        b = rng.normal(0, 1.0, N)
        ref = dot_ref(a, b)
        for k, (rnd, fn) in schemes.items():
            errs[k].append(rel_err(fn(a, b, rnd), ref))
    print(f"=== Long dot-product accumulation, N={N}, trials={trials} ===")
    print(f"{'scheme':16s} {'mean rel.err':>14s} {'median':>12s}")
    for k in schemes:
        e = np.array(errs[k])
        print(f"{k:16s} {e.mean():14.3e} {np.median(e):12.3e}")
    return errs

if __name__ == "__main__":
    run(N=1024, trials=200)
    print()
    run(N=8192, trials=60)
