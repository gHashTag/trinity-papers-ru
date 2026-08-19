"""Functional check of every generated datapath against a Python golden model.

Without this the cell counts would be counts of unverified logic.
"""
import json, os, random, subprocess, sys

HW = os.path.dirname(os.path.abspath(__file__))
meta = json.load(open(os.path.join(HW, "designs.json")))
random.seed(20260819)
N = 400
res = {}

def tb_exact(name, wa, ws, signed_in):
    return f"""
`timescale 1ns/1ps
module tb;
  reg [{wa-1}:0] a, b;
  wire signed [{ws-1}:0] s;
  {name} dut(.a(a), .b(b), .s(s));
  integer f, r; reg [63:0] xa, xb;
  initial begin
    f = $fopen("in.txt", "r");
    while (!$feof(f)) begin
      r = $fscanf(f, "%d %d\\n", xa, xb);
      if (r == 2) begin a = xa[{wa-1}:0]; b = xb[{wa-1}:0]; #1 $display("%0d", s); end
    end
    $fclose(f); $finish;
  end
endmodule
"""

def tb_bits(name, wa, ws):
    return f"""
`timescale 1ns/1ps
module tb;
  reg [{wa-1}:0] a, b;
  wire [{ws-1}:0] s;
  {name} dut(.a(a), .b(b), .s(s));
  integer f, r; reg [63:0] xa, xb;
  initial begin
    f = $fopen("in.txt", "r");
    while (!$feof(f)) begin
      r = $fscanf(f, "%d %d\\n", xa, xb);
      if (r == 2) begin a = xa[{wa-1}:0]; b = xb[{wa-1}:0]; #1 $display("%0d", s); end
    end
    $fclose(f); $finish;
  end
endmodule
"""

def dec_exact(x, E, M, ecodes):
    s = (x >> (E + M)) & 1
    e = (x >> M) & ((1 << E) - 1)
    m = x & ((1 << M) - 1)
    if e >= ecodes:
        return None            # code outside the reachable exponent set
    mag = ((1 << M) | m) << e
    return -mag if s else mag

def fadd_rne(x, y, E, M):
    """Golden model of the conventional adder, mirroring the RTL contract:
    no subnormals, no inf/nan, exponent field wraps."""
    def unpack(v):
        return ((v >> (E + M)) & 1, (v >> M) & ((1 << E) - 1), v & ((1 << M) - 1))
    sa, ea, ma = unpack(x)
    sb, eb, mb = unpack(y)
    agtb = (ea > eb) or (ea == eb and ma >= mb)
    (sh, eh, mh), (sl, el, ml) = ((sa, ea, ma), (sb, eb, mb)) if agtb else ((sb, eb, mb), (sa, ea, ma))
    d = (eh - el) & ((1 << E) - 1)
    amt = min(d, M + 3)
    fh = ((1 << M) | mh) << 2
    fl0 = ((1 << M) | ml) << 2
    fl = fl0 >> amt
    sticky = 1 if (fl0 & ((1 << amt) - 1)) else 0
    W = M + 4
    if sh == sl:
        summ = fh + fl
    else:
        summ = fh - fl - sticky
    if summ >> W:
        nrm = summ >> 1
        eo = eh + 1
    else:
        lz = 0
        while lz < W and not ((summ >> (W - 1 - lz)) & 1):
            lz += 1
        if summ == 0:
            lz = 0
        nrm = (summ << lz) & ((1 << (W + 1)) - 1)
        eo = eh - lz
    g = (nrm >> 1) & 1
    r = nrm & 1
    mo_t = (nrm >> 2) & ((1 << M) - 1)
    roundup = g & (r | (mo_t & 1))
    mo = mo_t + roundup
    if mo >> M:
        eo += 1
        mo = (mo >> 1) & ((1 << M) - 1)
    else:
        mo &= (1 << M) - 1
    eo &= (1 << E) - 1
    return (sh << (E + M)) | (eo << M) | mo

def run(name, tb_src, vecs, exp, wa):
    d = os.path.join(HW, "sim_" + name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "tb.v"), "w").write(tb_src)
    open(os.path.join(d, "in.txt"), "w").write("".join(f"{a} {b}\n" for a, b in vecs))
    src = os.path.join(HW, name.rsplit("_", 1)[0] + ".v")
    base = name.replace("_exact", "").replace("_round", "")
    src = os.path.join(HW, base + ".v")
    p = subprocess.run(["iverilog", "-g2012", "-o", "sim", "tb.v", src], cwd=d,
                       capture_output=True, text=True)
    if p.returncode:
        return dict(ok=False, stage="compile", err=p.stderr[-800:])
    p = subprocess.run(["./sim"], cwd=d, capture_output=True, text=True)
    got = [int(l) for l in p.stdout.strip().splitlines() if l.strip().lstrip("-").isdigit()]
    if len(got) != len(exp):
        return dict(ok=False, stage="run", got=len(got), want=len(exp), err=p.stdout[-400:])
    bad = [(vecs[i], exp[i], got[i]) for i in range(len(exp)) if exp[i] != got[i]]
    return dict(ok=not bad, n=len(exp), mismatches=len(bad), first_bad=bad[:3])

for m in meta:
    name, E, M, ec, style = m["name"], m["E"], m["M"], m["ecodes"], m["style"]
    if name == "fixed16_exact":
        wa = 16
        vecs, exp = [], []
        for _ in range(N):
            a = random.getrandbits(16); b = random.getrandbits(16)
            sa = a - (1 << 16) if a >> 15 else a
            sb = b - (1 << 16) if b >> 15 else b
            vecs.append((a, b)); exp.append(sa + sb)
        res[name] = run(name, tb_exact(name, 16, 17, True), vecs, exp, wa)
    elif style == "exact":
        wa = 1 + E + M
        ws = m["internal_width"] + 1
        vecs, exp = [], []
        while len(vecs) < N:
            a = random.getrandbits(wa); b = random.getrandbits(wa)
            va = dec_exact(a, E, M, ec); vb = dec_exact(b, E, M, ec)
            if va is None or vb is None:
                continue
            vecs.append((a, b)); exp.append(va + vb)
        res[name] = run(name, tb_exact(name, wa, ws, True), vecs, exp, wa)
    else:
        wa = 1 + E + M
        vecs, exp = [], []
        while len(vecs) < N:
            a = random.getrandbits(wa); b = random.getrandbits(wa)
            if ((a >> M) & ((1 << E) - 1)) >= ec or ((b >> M) & ((1 << E) - 1)) >= ec:
                continue
            vecs.append((a, b)); exp.append(fadd_rne(a, b, E, M))
        res[name] = run(name, tb_bits(name, wa, wa), vecs, exp, wa)
    r = res[name]
    print(name, "OK" if r.get("ok") else "FAIL", {k: v for k, v in r.items() if k != "ok"})

json.dump(res, open(os.path.join(HW, "verify.json"), "w"), indent=1, default=str)
