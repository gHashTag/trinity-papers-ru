# arXiv:2606.09686 — English upload package (v2, erratum 84 → 83)

**Paper 2 — numeric-format catalog + conformance vectors.** This file is the
English metadata + change-log for the next arXiv replacement. The compiled PDF
is `statya2_ru.pdf` (Russian body with a full English abstract inside; the
English abstract below is the same text). Paste the *Title* and *Abstract*
fields into the arXiv "replace" form; attach the recompiled PDF.

> The single substantive change is the **erratum: 84 → 83 formats.** The v1 arXiv
> listing said "84-format"; the single source of truth
> (`conformance/vectors/INDEX_all_formats.json`, catalog invariant CI-01
> `sum(cluster_counts) == 83`) is **83**. This upload corrects the count
> everywhere and records the SW conformance-pack recount.

---

## Title

Trinity Golden Vectors (TGV): an 83-format numeric catalog with catalog-wide
conformance vectors

## Authors

D. V. Vasilev — Independent researcher, Trinity S³AI — admin@t27.ai —
ORCID 0009-0008-4294-6159 — github.com/gHashTag

## Abstract (arXiv abstract field)

The proliferation of numeric formats in machine-learning hardware — FP8 (E4M3
and E5M2), BF16, MXFP4, block microscaling formats and dozens of research
variants — has outpaced the availability of vendor-neutral, bit-exact reference
material. This paper presents: a catalog of 83 numeric formats spanning 13
families; a complete conformance-pack set covering all 83 catalog formats
(75 bit-exact packs with encode-decode round-trip checking, 0 self-consistent
packs (single decode law without an independent second witness), and 8
structural packs for formats that have no fixed radix-2 S:E:M layout); a deeply
validated Tier-1 reference subset of six packs for GF16, the MXFP4 element,
BF16, FP8 E4M3, FP8 E5M2 and the E8M0 block scale, cross-checked against an
external oracle; and a crosswalk to IEEE P3109 v3.2.0 mapping each Tier-1 pack
to its configurable form of the standard. Every pack is a self-contained JSON
document with a SHA-256 fingerprint, a shared row schema and an anchor vector
encoding the value 3.0 — the identity φ² + 1/φ² = 3 — as a cross-pack
correctness check. The Tier-1 packs are cross-checked against ml_dtypes 0.5.4
(Google/JAX); any discrepancy is documented explicitly and interpreted as a
specification-permitted interpretive gap rather than hidden. The work is
positioned as registry-filling: it proposes no new formats, makes no
model-accuracy claim and asserts no superiority over any vendor implementation.
All artefacts are publicly available at github.com/gHashTag/t27 under an open
license.

## Keywords

numeric formats; conformance vectors; bit-exact; FP8; BF16; MXFP4;
microscaling; IEEE P3109; vendor-neutral reference.

---

## Change-log v1 → v2 (erratum)

1. **Erratum 84 → 83 formats (everywhere).** Title, abstract (RU + EN), §3.1
   cluster table ("Итого = 83"), invariant CI-01 (`sum(cluster_counts) == 83`),
   the all-catalog coverage policy (§4.5), and `INDEX_all_formats.json`
   (`total_packs: 83`) are now consistent at **83**. The count matches the SSOT
   repository, not the v1 preprint number.

2. **SW conformance-pack recount v4 → v5 recorded.** v4 (2026-06-08) split the
   pack set as 49 bit-exact / 34 structural. Recomputed against the live SSOT
   index: six wide GF formats (GF48, GF96, GF128, GF256, GF512, GF1024),
   previously self-consistent, were promoted to strict bit-exactness by an
   independent second decoder (dyadic-exact, abs_error=0). Current split:
   **75 bit-exact / 0 self-consistent / 8 structural (total 83).** This is the
   SW representation-level ceiling (dual-channel verified).

3. **Scope note (unchanged, restated for honesty).** This paper covers
   *software representation-level* conformance (encode/decode bit-exactness)
   only. FPGA hardware Tier-E status (decode-HW / compute-HW on the AX7203
   board) is out
   of scope here and is reported in the companion GoldenFloat paper
   (arXiv:2606.05017). No model-accuracy or vendor-superiority claim is made.
