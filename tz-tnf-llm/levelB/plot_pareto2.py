import json, math, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
syn = json.load(open(os.path.join(HERE, "hw/synth_xilinx8.json")))
ltp = json.load(open(os.path.join(HERE, "hw/ltp8.json")))
br  = json.load(open(os.path.join(HERE, "results_8bit_analysis.json")))
fam = json.load(open(os.path.join(HERE, "results_tnf8_family.json")))

RTL = {"int8_b32": "fixed8_exact", "e2m5_b32": "float_e2m5_exact", "e2m5_b16": "float_e2m5_exact",
       "e4m3": "float_e4m3_exact", "e4m3_b32": "float_e4m3_exact", "e5m2_b32": "float_e5m2_exact",
       "e3m4_b32_PHI8": "float_e3m4_exact", "e3m4_b16_PHI8": "float_e3m4_exact",
       "tnf8_t2m5_b32": "tnf8_t2m3_exact", "tnf8_t2m3_b32": "tnf8_t2m3_exact",
       "tnf8_t1m5_b32": "tnf8_t1m5_exact", "tnf8_t3m2_b32": "tnf8_t3m2_exact",
       "int8_b16": "fixed8_exact", "int8_b128": "fixed8_exact"}
FAMC = {"int": "#2b6cb0", "fp8": "#dd6b20", "tnf": "#2f855a", "phi": "#805ad5"}
def fam_of(n):
    if n.startswith("tnf"): return "tnf"
    if "PHI" in n: return "phi"
    if n.startswith("int"): return "int"
    return "fp8"

pts = {}
rows = br["act8"]
for r in rows:
    n = r["fmt"]
    if n in RTL and n in ("int8_b32","int8_b16","e2m5_b16","e2m5_b32","e4m3","e4m3_b32","e5m2_b32",
                          "e3m4_b32_PHI8","e3m4_b16_PHI8","tnf8_t2m5_b32"):
        y = r["d_ppl_pct"]; lo, hi = r["ci95_d_ppl_pct"]
        pts[n] = dict(lut=syn[RTL[n]]["luts"], depth=ltp.get(RTL[n]), y=y, lo=lo, hi=hi, src="12 окон")
for k, v in fam.items():
    pol, n = k.split("|")
    if pol != "chunked" or n == "base": continue
    if n in RTL and n not in pts:
        pts[n] = dict(lut=syn[RTL[n]]["luts"], depth=ltp.get(RTL[n]), y=v["dppl_pct"], lo=None, hi=None, src="12 окон")
pts.pop("tnf8_t2m5_b32", None)   # renamed: same design as tnf8_t2m3_b32

OFF = {"int8_b32": (9, -14), "int8_b16": (9, 6), "e2m5_b16": (0, -22), "tnf8_t1m5_b32": (-6, 12),
       "e2m5_b32": (9, 6), "e3m4_b32_PHI8": (10, -4), "e3m4_b16_PHI8": (-10, 9),
       "tnf8_t2m3_b32": (-8, 24), "e4m3": (-8, 14), "e4m3_b32": (11, -4),
       "e5m2_b32": (-10, -6), "tnf8_t3m2_b32": (-10, -16), "int8_b128": (9, 6)}
HA = {"e4m3": "right", "e5m2_b32": "right", "tnf8_t2m3_b32": "right", "tnf8_t3m2_b32": "right", "e3m4_b16_PHI8": "right",
      "tnf8_t1m5_b32": "right"}
fig, ax = plt.subplots(figsize=(10.4, 6.4))
front = []
for n, p in sorted(pts.items(), key=lambda kv: kv[1]["lut"]):
    if all(not (q["lut"] <= p["lut"] and q["y"] <= p["y"] and q is not p) for q in pts.values()):
        front.append((p["lut"], p["y"], n))
front.sort()
ax.step([f[0] for f in front], [f[1] for f in front], where="post",
        color="#a0aec0", lw=1.4, zorder=1, label="фронт Парето")
for n, p in pts.items():
    c = FAMC[fam_of(n)]
    dom = any((n2 != n and pts[n2]["lut"] <= p["lut"] and pts[n2]["y"] <= p["y"]) for n2 in pts)
    ax.scatter(p["lut"], p["y"], s=95 if not dom else 62, c=c, zorder=3,
               marker="o" if not dom else "x", linewidths=1.8)
    lbl = n.replace("_b32", "·b32").replace("_b16", "·b16").replace("_PHI8", "·φ")
    ax.annotate(f"{lbl}  {p['lut']} LUT, гл. {p['depth']}", (p["lut"], p["y"]),
                textcoords="offset points", xytext=OFF.get(n, (9, 5)),
                fontsize=8.2, color="#1a202c", ha=HA.get(n, "left"))
ax.axhline(0, color="#718096", lw=1, ls="--")
ax.axhspan(-0.5, 0.5, color="#edf2f7", zorder=0)
ax.text(0.985, 0.045, "полоса практической неразличимости ±0,5 %\n(внешний порог, Fireworks / arXiv:2511.19794)",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#4a5568")
ax.set_xlabel("цена точного 8-битного датапата на xc7, LUT  [измерено, yosys]")
ax.set_ylabel("парная ΔPPL, %  (GPT-2 124M, Moby Dick, 12 окон)  [измерено]")
ax.set_title("8 бит: ущерб против цены. Крестик = точка доминируется")
ax.set_xscale("log"); ax.set_xlim(6, 420); ax.set_ylim(-1.4, 10.2); ax.grid(alpha=.25)
hs = [plt.Line2D([], [], marker="o", ls="", color=FAMC[k], label=v) for k, v in
      (("int", "целочисленные"), ("fp8", "OCP/бинарные float"), ("phi", "φ-раскладка"),
       ("tnf", "TNF, троичная экспонента"))]
ax.legend(handles=hs, loc="upper left", fontsize=8.5, framealpha=.9)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "pareto_act8_v2.png"), dpi=170)
print("frontier:", [(f[2], f[0], round(f[1], 3)) for f in front])
print("points:", len(pts))
