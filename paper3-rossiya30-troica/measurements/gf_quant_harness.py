#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GF accuracy proxy harness (SQNR/MSE), no hardware.
Honest scope: quantize->dequantize round-trip error on a FIXED tensor set.
This is a PROXY (representation error), NOT downstream model accuracy.

Codecs compared:
  - GF16, GF8  (phi-rule static field split, spec arXiv:2606.05017)
  - IEEE fp16  (5 exp / 10 man)
  - bf16       (8 exp / 7 man)
  - fp8_e4m3   (4 exp / 3 man, OCP-style, saturate)
  - int8       (per-tensor symmetric, absmax scale)

All formats use Round-to-Nearest-Even where applicable.
"""
import numpy as np
import json, csv, math

np.seterr(all="ignore")

# ---------------------------------------------------------------------------
# phi-rule field split for GF_N  (spec: e = round((N-1)/phi^2), m = N-1-e,
#                                 bias = 2^(e-1)-1 ; 1 sign bit)
# ---------------------------------------------------------------------------
PHI = (1.0 + 5.0 ** 0.5) / 2.0
PHI2 = PHI * PHI  # phi^2 = phi + 1

def gf_fields(N):
    e = round((N - 1) / PHI2)
    m = (N - 1) - e
    bias = 2 ** (e - 1) - 1
    return e, m, bias

# ---------------------------------------------------------------------------
# Generic sign/exp/mantissa float codec with RNE (used for GF, fp16, bf16, fp8)
#   fields: e exponent bits, m mantissa bits, bias, has_subnormals, has_inf/nan
#   We implement a clean IEEE-style interpretation:
#     value = (-1)^s * 2^(E-bias) * (1.f)   for normals
#             (-1)^s * 2^(1-bias) * (0.f)   for subnormals (E==0)
# We saturate to max finite on overflow (no inf) for GF/fp8; fp16/bf16 use inf.
# ---------------------------------------------------------------------------
def make_float_codec(e_bits, m_bits, bias, use_inf=True, saturate=True):
    emax = (2 ** e_bits) - 1            # all-ones exponent
    max_E = emax - (1 if use_inf else 0)  # reserve all-ones for inf/nan if use_inf
    # largest finite: E=max_E, mantissa all ones
    if use_inf:
        big_E = emax - 1
    else:
        big_E = emax
    max_frac = 2.0 - 2.0 ** (-m_bits)
    max_finite = (2.0 ** (big_E - bias)) * max_frac
    # smallest positive subnormal
    min_sub = (2.0 ** (1 - bias)) * (2.0 ** (-m_bits))

    def quant(x):
        x = np.asarray(x, dtype=np.float64)
        out = np.empty_like(x)
        flat = x.reshape(-1)
        o = out.reshape(-1)
        for i, v in enumerate(flat):
            if v == 0.0 or not np.isfinite(v):
                o[i] = 0.0 if v == 0.0 else (np.sign(v) * max_finite)
                continue
            s = math.copysign(1.0, v)
            a = abs(v)
            if a >= max_finite:
                o[i] = s * max_finite
                continue
            # find exponent
            E = math.floor(math.log2(a)) + bias
            if E < 1:
                # subnormal region
                scale = 2.0 ** (1 - bias)
                # mantissa step
                q = round(a / (scale * 2.0 ** (-m_bits)))
                val = q * scale * 2.0 ** (-m_bits)
                if val < min_sub / 2:
                    val = 0.0
                o[i] = s * val
                continue
            if E > big_E:
                o[i] = s * max_finite
                continue
            # normal: mantissa 1.f with m_bits, RNE
            frac = a / (2.0 ** (E - bias))  # in [1,2)
            q = round((frac - 1.0) * (2 ** m_bits))
            if q == (2 ** m_bits):
                q = 0
                E += 1
                if E > big_E:
                    o[i] = s * max_finite
                    continue
            val = (2.0 ** (E - bias)) * (1.0 + q / (2 ** m_bits))
            o[i] = s * val
        return out.reshape(x.shape)
    meta = dict(e_bits=e_bits, m_bits=m_bits, bias=bias,
                max_finite=max_finite, min_sub=min_sub, use_inf=use_inf)
    return quant, meta

# GF codecs (no inf, saturate)
def make_gf_codec(N):
    e, m, bias = gf_fields(N)
    q, meta = make_float_codec(e, m, bias, use_inf=False, saturate=True)
    meta.update(name=f"GF{N}", fields=f"1s/{e}e/{m}m bias={bias}")
    return q, meta

# IEEE fp16 (5e/10m bias15, inf), bf16 (8e/7m bias127, inf)
def make_fp16():
    q, meta = make_float_codec(5, 10, 15, use_inf=True)
    meta.update(name="fp16", fields="1s/5e/10m bias=15")
    return q, meta

def make_bf16():
    q, meta = make_float_codec(8, 7, 127, use_inf=True)
    meta.update(name="bf16", fields="1s/8e/7m bias=127")
    return q, meta

# fp8 e4m3 (4e/3m bias7, no inf, saturate to 448 OCP-style)
def make_fp8_e4m3():
    q, meta = make_float_codec(4, 3, 7, use_inf=False, saturate=True)
    meta.update(name="fp8_e4m3", fields="1s/4e/3m bias=7")
    return q, meta

# int8 per-tensor symmetric absmax
def make_int8_codec():
    def quant(x):
        x = np.asarray(x, dtype=np.float64)
        amax = np.max(np.abs(x))
        if amax == 0:
            return np.zeros_like(x)
        scale = amax / 127.0
        qi = np.clip(np.round(x / scale), -127, 127)
        return qi * scale
    return quant, dict(name="int8", fields="per-tensor sym absmax, 127 levels")

# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------
def sqnr_db(x, xq):
    sig = np.sum(x.astype(np.float64) ** 2)
    noise = np.sum((x.astype(np.float64) - xq.astype(np.float64)) ** 2)
    if noise == 0:
        return float("inf")
    return 10.0 * math.log10(sig / noise)

def mse(x, xq):
    return float(np.mean((x.astype(np.float64) - xq.astype(np.float64)) ** 2))

# ---------------------------------------------------------------------------
# tensor set (fixed seed) — representative of NN weights/activations
# ---------------------------------------------------------------------------
def build_tensors(seed=20260706, n=200000):
    rng = np.random.default_rng(seed)
    sets = {}
    # 1. Gaussian weights (typical linear-layer weights, std 0.02..0.05)
    sets["gauss_w(std0.02)"] = rng.normal(0.0, 0.02, n)
    # 2. Gaussian activations (std 1.0)
    sets["gauss_act(std1.0)"] = rng.normal(0.0, 1.0, n)
    # 3. Heavy-tail (Student-t df=3) — outlier-rich, hardest for low-exp formats
    sets["heavy_tail(t df3)"] = rng.standard_t(3, n) * 0.1
    # 4. Uniform [-1,1]
    sets["uniform[-1,1]"] = rng.uniform(-1.0, 1.0, n)
    # 5. LogNormal magnitudes (wide dynamic range)
    sets["lognormal(wide DR)"] = rng.lognormal(0.0, 1.5, n) * rng.choice([-1, 1], n) * 0.01
    return sets

def main():
    codecs = {}
    for cq, cm in [make_gf_codec(16), make_gf_codec(8),
                   make_fp16(), make_bf16(), make_fp8_e4m3()]:
        codecs[cm["name"]] = (cq, cm)
    iq, im = make_int8_codec()
    codecs["int8"] = (iq, im)

    order = ["GF16", "fp16", "bf16", "GF8", "fp8_e4m3", "int8"]
    tensors = build_tensors()

    print("=== Field definitions ===")
    for name in order:
        print(f"  {name:10s} {codecs[name][1].get('fields','')}")

    rows = []
    print("\n=== SQNR (dB) — higher is better ===")
    header = f"{'tensor':22s} " + " ".join(f"{n:>10s}" for n in order)
    print(header)
    sqnr_table = {}
    mse_table = {}
    for tname, x in tensors.items():
        line = f"{tname:22s} "
        for name in order:
            q, meta = codecs[name]
            xq = q(x)
            s = sqnr_db(x, xq)
            m = mse(x, xq)
            sqnr_table[(tname, name)] = s
            mse_table[(tname, name)] = m
            rows.append(dict(tensor=tname, format=name, bits=(16 if name in ("GF16","fp16","bf16") else 8),
                             sqnr_db=round(s, 3), mse=m))
            line += f"{s:10.2f} "
        print(line)

    # averages per format
    print("\n=== Mean SQNR (dB) across all tensor sets ===")
    for name in order:
        vals = [sqnr_table[(t, name)] for t in tensors if np.isfinite(sqnr_table[(t, name)])]
        print(f"  {name:10s} {np.mean(vals):8.2f} dB")

    # save CSV + JSON
    with open("/home/user/workspace/wave_audit/gf_accuracy_proxy_2026-07-06.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tensor", "format", "bits", "sqnr_db", "mse"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open("/home/user/workspace/wave_audit/gf_accuracy_proxy_2026-07-06.json", "w") as f:
        json.dump({"sqnr_db": {f"{t}|{n}": sqnr_table[(t, n)] for t in tensors for n in order},
                   "mse": {f"{t}|{n}": mse_table[(t, n)] for t in tensors for n in order},
                   "fields": {n: codecs[n][1].get("fields", "") for n in order}},
                  f, indent=2)
    print("\nSaved CSV + JSON to wave_audit/")

if __name__ == "__main__":
    main()
