# GoldenFloat representation-accuracy proxy measurements (2026-07-06)

This directory contains the first project-internal, reproducible accuracy
measurements referenced from paper 3 (`rossiya_3_0_troica_ru.md`, section 3a.5).

**Status tags (honesty discipline):** `[measured — SW proxy]`.
These are *representation* accuracy numbers (round-trip quantize -> dequantize,
SQNR in dB), **NOT** downstream model accuracy (perplexity / MMLU), which
remains unmeasured. The distinction is binding — do not overstate.

## Files

| File | What it is |
| --- | --- |
| `gf_quant_harness.py` | SQNR harness. Fixed `seed=20260706`, RNE rounding, 5 synthetic distributions + real GPT-2 weights path. Reproduces the CSVs below. |
| `lucas_accum_test.py` | Long-sum (GEMM-proxy) accumulation test probing a phi-specific (Lucas-identity) error-reduction hypothesis. |
| `gf_accuracy_proxy_2026-07-06.csv` | Synthetic-distribution SQNR results (mean over 5 distributions). |
| `gf_accuracy_realweights_2026-07-06.csv` | Real GPT-2 weights (5 layers) SQNR results. |
| `RESULTS_ru.md` | Full Russian write-up of methodology, results, and boundaries. |

## Headline results (mean SQNR, dB)

16-bit: **GF16 = 67.8**, fp16 = 73.8, bf16 = 55.7.
8-bit:  GF8 ~= 29, fp8_e4m3 ~= 31, int8 ~= 32.
Real GPT-2 weights reproduce the same pattern (GF16 ~= 67.7 / fp16 ~= 73.6 / bf16 ~= 55.5).

## What the numbers mean — and do NOT mean (binding)

- Two honest "win windows" for GoldenFloat, and only two: (1) **GF16 beats bf16
  by ~+12 dB** (more mantissa bits, 9 vs 7); (2) **GF8 beats linear int8 on
  heavy-tailed / wide-dynamic-range layers** (e.g. a GPT-2 layer with an outlier
  max ~= 8.88 where int8 collapses to ~20.4 dB). This is the well-known advantage
  of a floating scheme over linear int8 on outlier layers — not a phi effect.
- **GF16 is consistently ~-6 dB below fp16** (fp16 has one extra mantissa bit).
  Claiming "GoldenFloat is more accurate than fp16/fp8" is not supported.
- The GF16-over-bf16 advantage is due to the **field split (9m vs 7m), not the
  irrational constant phi**: a control run shows GF16(6e/9m) is bit-identical to a
  plain float of the same fields (max abs diff = 0.0). So **phi is a
  field-SELECTION rule, not a different arithmetic** `[proven — control]`.
- The phi-specific accumulation hypothesis (dot-product, Lucas identity
  `phi^{2n} + phi^{-2n} = L_{2n}`) is **tested and refuted**: GF16 accumulates
  like a plain 6e/9m float; an fp32 accumulator is mandatory for all 16-bit
  formats `[measured]`.
- These are not energy / area / speed numbers, and not a peer-reviewed result —
  an internal starting point only.

## Reproduce

```
python gf_quant_harness.py       # synthetic + (optional) real-weights SQNR
python lucas_accum_test.py       # accumulation / Lucas-identity probe (~2 min)
```

Requires `numpy` (2.x). Real-weights path additionally uses `safetensors` +
`huggingface_hub` to fetch GPT-2 weights; if unavailable, the harness runs the
synthetic path only.
