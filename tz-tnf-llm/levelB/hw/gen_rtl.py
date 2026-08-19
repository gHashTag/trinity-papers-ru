"""Generate parametric RTL for a fair decode+add cost comparison across 16-bit formats.

Two datapath styles are generated for every candidate:
  (a) exact  : decode to a common fixed-point (Kulisch-style) and add -- no rounding
  (b) round  : conventional align/add/normalize/round-to-nearest-even float adder

Fixed-point (two's complement) formats only get style (a); they are already fixed-point.
"""
import os, json

OUT = os.path.dirname(os.path.abspath(__file__))

def clog2(n):
    k = 0
    while (1 << k) < n:
        k += 1
    return k

def gen_fixed(name, W):
    """Plain two's complement adder with one guard bit."""
    return f"""
module {name} (
  input  wire signed [{W-1}:0] a,
  input  wire signed [{W-1}:0] b,
  output wire signed [{W}:0]   s
);
  assign s = $signed(a) + $signed(b);
endmodule
"""

def gen_exact(name, E, M, ecodes):
    """Decode two (1,E,M) floats into a common fixed-point of width Wfx and add.
    ecodes = number of distinct exponent codes actually reachable (2**E for binary,
    3**t for a ternary-coded exponent field)."""
    frac = M + 1                    # hidden bit + mantissa
    span = ecodes - 1               # number of distinct left shifts
    Wfx = frac + span               # magnitude width
    W = Wfx + 1                     # + sign
    shw = clog2(ecodes) if ecodes > 1 else 1
    return f"""
module {name} (
  input  wire [{E+M}:0] a,
  input  wire [{E+M}:0] b,
  output wire signed [{W}:0] s
);
  function [{W-1}:0] dec;
    input [{E+M}:0] x;
    reg [{frac-1}:0] man;
    reg [{shw-1}:0] ex;
    reg [{Wfx-1}:0] mag;
    begin
      man = {{1'b1, x[{M-1}:0]}};
      ex  = x[{E+M-1}:{M}];
      mag = {{{{{span}{{1'b0}}}}, man}} << ex;
      dec = x[{E+M}] ? (~{{1'b0, mag}} + 1'b1) : {{1'b0, mag}};
    end
  endfunction
  assign s = $signed(dec(a)) + $signed(dec(b));
endmodule
"""

def gen_round(name, E, M):
    """Conventional float adder: align by exponent difference, add, normalise, RNE."""
    frac = M + 1
    W = frac + 3          # 1 guard + round + sticky room
    shw = max(clog2(M + 4), 1)
    return f"""
module {name} (
  input  wire [{E+M}:0] a,
  input  wire [{E+M}:0] b,
  output wire [{E+M}:0] s
);
  wire sa = a[{E+M}], sb = b[{E+M}];
  wire [{E-1}:0] ea = a[{E+M-1}:{M}], eb = b[{E+M-1}:{M}];
  wire [{M-1}:0] ma = a[{M-1}:0],     mb = b[{M-1}:0];
  wire agtb = (ea > eb) || ((ea == eb) && (ma >= mb));
  wire [{E-1}:0] eh = agtb ? ea : eb;
  wire [{E-1}:0] el = agtb ? eb : ea;
  wire [{M-1}:0] mh = agtb ? ma : mb;
  wire [{M-1}:0] ml = agtb ? mb : ma;
  wire sh = agtb ? sa : sb;
  wire sl = agtb ? sb : sa;
  wire [{E-1}:0] d = eh - el;
  wire [{max(shw,E)-1}:0] dx = d;
  wire [{shw-1}:0] sh_amt = (dx > {M+3}) ? {M+3} : dx[{shw-1}:0];
  wire [{W-1}:0] fh = {{1'b1, mh, 2'b00}};
  wire [{W-1}:0] fl0 = {{1'b1, ml, 2'b00}};
  wire [{W-1}:0] fl = fl0 >> sh_amt;
  wire sticky = |(fl0 & ~({{{W}{{1'b1}}}} << sh_amt));
  wire [{W}:0] sum = (sh == sl) ? (fh + fl) : (fh - fl - sticky);
  // normalise: at most one right shift on carry, or leading-zero count on subtract
  reg [{shw-1}:0] lz;
  reg [{W}:0] nrm;
  reg [{E-1}:0] eo;
  integer i;
  always @* begin
    lz = 0;
    for (i = 0; i < {W}; i = i + 1)
      if ((lz == i[{shw-1}:0]) && !sum[{W-1}-i]) lz = i[{shw-1}:0] + 1'b1;
    if (sum[{W}]) begin
      nrm = sum >> 1;
      eo  = eh + 1'b1;
    end else begin
      nrm = sum << lz;
      eo  = eh - lz;
    end
  end
  wire g = nrm[1], r = nrm[0];
  wire [{M-1}:0] mo_t = nrm[{M+1}:2];
  wire roundup = g & (r | mo_t[0]);
  wire [{M}:0] mo = {{1'b0, mo_t}} + roundup;
  wire [{M-1}:0] mo_sh = mo[{M}:1];
  assign s = {{sh, mo[{M}] ? (eo + 1'b1) : eo, mo[{M}] ? mo_sh : mo[{M-1}:0]}};
endmodule
"""

CANDS = [
    # name,            kind,   E, M, ecodes, note
    ("fixed16",        "fx",   0, 16, 1,   "two's complement 16-bit, block scale outside"),
    ("float_e2m13",    "fp",   2, 13, 4,   "accuracy winner for the block-scaled ternary dot product"),
    ("float_e3m12",    "fp",   3, 12, 8,   "one exponent bit more"),
    ("float_e5m10",    "fp",   5, 10, 32,  "binary16 reference"),
    ("float_e6m9",     "fp",   6, 9,  64,  "phi split: e = round((N-1)/phi^2) = 6"),
    ("tnf16_t4m8",     "fp",   7, 8,  81,  "ternary-coded exponent, 4 trits (81 codes) in a 7-bit field"),
]

files, meta = [], []
for name, kind, E, M, ecodes, note in CANDS:
    src = ""
    if kind == "fx":
        src += gen_fixed(name + "_exact", M)
        wfx = M + 1
        meta.append(dict(name=name + "_exact", style="exact", E=0, M=M, ecodes=1,
                         internal_width=wfx, note=note))
    else:
        src += gen_exact(name + "_exact", E, M, ecodes)
        frac = M + 1
        meta.append(dict(name=name + "_exact", style="exact", E=E, M=M, ecodes=ecodes,
                         internal_width=frac + ecodes - 1 + 1, note=note))
        src += gen_round(name + "_round", E, M)
        meta.append(dict(name=name + "_round", style="round", E=E, M=M, ecodes=ecodes,
                         internal_width=M + 4, note=note))
    p = os.path.join(OUT, name + ".v")
    open(p, "w").write(src)
    files.append(p)

json.dump(meta, open(os.path.join(OUT, "designs.json"), "w"), indent=1)
print("\n".join(files))
for m in meta:
    print(m["name"], m["style"], "internal_width=", m["internal_width"])
