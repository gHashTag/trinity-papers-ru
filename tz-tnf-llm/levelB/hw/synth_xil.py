import json, os, re, sys, time
from yowasp_yosys import run_yosys
HW = os.path.dirname(os.path.abspath(__file__)); os.chdir(HW)
meta = json.load(open("designs.json"))
out = {}
for m in meta:
    name = m["name"]; base = name.replace("_exact","").replace("_round","")
    open("synx.ys","w").write(f"read_verilog -sv {base}.v\nsynth_xilinx -family xc7 -top {name} -flatten\nstat\n")
    log = f"xlog_{name}.txt"; t0=time.time(); rc=0
    try:
        run_yosys(["-q","-l",log,"-s","synx.ys"])
    except BaseException as e:
        rc = 1
    dt=time.time()-t0
    txt = open(log).read() if os.path.exists(log) else ""
    sec = txt.split("=== "+name+" ===")[-1]
    luts = sum(int(g.group(2)) for g in re.finditer(r"\s+(LUT[1-6])\s+(\d+)", sec))
    carry = sum(int(g.group(2)) for g in re.finditer(r"\s+(CARRY4)\s+(\d+)", sec))
    cells = re.search(r"(\d+)\s+cells", sec)
    out[name]=dict(rc=rc, luts=luts, carry4=carry, cells=int(cells.group(1)) if cells else None, seconds=round(dt,1))
    print(name, out[name], flush=True)
json.dump(out, open("synth_xilinx.json","w"), indent=1)
print("ALLDONE")
