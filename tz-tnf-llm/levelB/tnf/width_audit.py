"""Machine audit of the TNF ladder width rule, integer arithmetic only.

Two width definitions live in the same branch:
  slot rule   : 1 + E_t + M = N          (tnf_ladder_versions.py, counts a trit as one slot)
  physical    : 1 + ceil(E_t*log2 3) + M (tnf_spec_ref.py / tnf_ref.py exp_bits)
A trit needs ceil(log2 3) bits only when packed alone; packed as a group of E_t
trits it needs ceil(E_t*log2 3) bits. The two definitions cannot both hold.
"""
import json, math
from tnf_ladder_versions import LADDER_V1_RESEARCH, LADDER_V2_SPEC, TRIT_BUDGET

def offbits(t):                        # exact integer: smallest b with 2^b >= 3^t
    b = 0
    while (1 << b) < 3 ** t: b += 1
    return b

rows = []
print(f"{'rung':>7} {'ver':>11} {'Et':>3} {'M':>5} {'slots':>6} {'offbits':>8} {'phys':>6} "
      f"{'slot ok':>8} {'phys ok':>8} {'codes':>7}")
for tag, lad in (("v1-research", LADDER_V1_RESEARCH), ("v2-spec", LADDER_V2_SPEC)):
    for w in sorted(lad):
        t, m = lad[w]; ob = offbits(t)
        slots, phys = 1 + t + m, 1 + ob + m
        r = dict(rung=w, version=tag, Et=t, M=m, slot_sum=slots, off_bits=ob, phys_bits=phys,
                 slot_ok=slots == w, phys_ok=phys == w, exp_codes=3 ** t,
                 codes_wasted=(1 << ob) - 3 ** t)
        rows.append(r)
        print(f"TNF{w:<4} {tag:>11} {t:3d} {m:5d} {slots:6d} {ob:8d} {phys:6d} "
              f"{('ok' if r['slot_ok'] else 'VIOL'):>8} {('ok' if r['phys_ok'] else 'VIOL'):>8} {3**t:7d}")
n1 = sum(1 for r in rows if r["version"] == "v1-research" and not r["slot_ok"])
n2 = sum(1 for r in rows if r["version"] == "v2-spec" and not r["phys_ok"])
print(f"\nv1-research rows violating the slot rule : {n1}/9")
print(f"v2-spec     rows violating the physical container : {n2}/9")
print("no ladder version satisfies BOTH definitions at any rung above TNF4"
      if n2 == 9 else "check by hand")
# where does a physically byte-exact TNF live?
print("\nphysically exact containers, 1 + ceil(Et*log2 3) + M == N:")
for N in (8, 16, 32, 64):
    opts = [(t, N - 1 - offbits(t)) for t in range(1, 12) if N - 1 - offbits(t) >= 1]
    print(f"  N={N:4d}: " + ", ".join(f"Et={t}(codes {3**t}) M={m}" for t, m in opts[:6]))
json.dump(rows, open("width_audit.json", "w"), indent=1)
