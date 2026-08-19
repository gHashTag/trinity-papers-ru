"""Technology-independent gate cost of every verified datapath (yosys techmap + stat).

This is a structural cost, not a Xilinx LUT count: the ABC mapping stage has not
finished in this sandbox, so LUT/latency numbers stay [not-evaluated].
"""
import json, os, re, sys, time
from yowasp_yosys import run_yosys

HW = os.path.dirname(os.path.abspath(__file__))
os.chdir(HW)
meta = json.load(open("designs.json"))
out = {}
for m in meta:
    name = m["name"]
    base = name.replace("_exact", "").replace("_round", "")
    ys = f"""read_verilog -sv {base}.v
hierarchy -top {name} -check
proc; opt -full; fsm; opt -full; memory; opt -full
techmap; opt -full
stat -width
"""
    open("syn.ys", "w").write(ys)
    log = f"log_{name}.txt"
    t0 = time.time()
    # yowasp run_yosys writes to stdout; capture by redirecting via tee-like -l
    run_yosys(["-q", "-l", log, "-s", "syn.ys"])
    dt = time.time() - t0
    txt = open(log).read()
    cells, gates, cellmap = None, {}, {}
    sec = txt.split("=== " + name + " ===")[-1]
    mm = re.search(r"(\d+)\s+cells", sec)
    if mm:
        cells = int(mm.group(1))
    for line in sec.splitlines():
        g = re.match(r"\s+(\$_?[A-Za-z0-9_.]+)\s+(\d+)", line)
        if g:
            cellmap[g.group(1)] = int(g.group(2))
    wires = re.search(r"(\d+)\s+wire bits", sec)
    out[name] = dict(style=m["style"], E=m["E"], M=m["M"], ecodes=m["ecodes"],
                     internal_width=m["internal_width"], cells=cells,
                     wire_bits=int(wires.group(1)) if wires else None,
                     cellmap=cellmap, seconds=round(dt, 2))
    print(name, out[name]["cells"], "cells", out[name]["wire_bits"], "wire bits", f"{dt:.1f}s")
json.dump(out, open("synth_cost.json", "w"), indent=1)
