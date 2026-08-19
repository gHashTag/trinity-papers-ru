"""Analyse results_ppl.json: is logit SQNR a monotone predictor of the perplexity delta?"""
import json, math
import numpy as np
d = json.load(open('results_ppl.json'))
out = {}
for tag, row in d.items():
    base = row['fp32']['ppl']
    xs, ys, names = [], [], []
    for k, v in row.items():
        if k == 'fp32': continue
        xs.append(v['logit_sqnr_db']); ys.append(100 * (v['ppl'] / base - 1)); names.append(k)
    xs, ys = np.array(xs), np.array(ys)
    # rank correlation between SQNR and |delta| (expect strongly negative if SQNR predicts damage)
    def rank(a):
        o = np.argsort(a); r = np.empty(len(a)); r[o] = np.arange(len(a)); return r
    rho = float(np.corrcoef(rank(xs), rank(np.abs(ys)))[0, 1])
    # inversions: pairs where higher SQNR gave larger |delta|
    inv = tot = 0
    for i in range(len(xs)):
        for j in range(len(xs)):
            if xs[i] > xs[j]:
                tot += 1
                if abs(ys[i]) > abs(ys[j]): inv += 1
    out[tag] = {'base_ppl': base, 'spearman_sqnr_vs_absdelta': round(rho, 3),
                'inversions': inv, 'pairs': tot,
                'inversion_pct': round(100 * inv / tot, 1) if tot else None,
                'rows': sorted([{'fmt': n, 'sqnr_db': float(x), 'delta_pct': round(float(y), 4)}
                                for n, x, y in zip(names, xs, ys)], key=lambda r: -r['sqnr_db'])}
    print('==', tag, 'base ppl', round(base, 4), '| spearman(SQNR, |delta|) =', round(rho, 3),
          f'| inversions {inv}/{tot}')
    for r in out[tag]['rows']:
        print(f"   {r['fmt']:18s} {r['sqnr_db']:7.2f} dB  {r['delta_pct']:+8.4f} %")
json.dump(out, open('results_ppl_analysis.json', 'w'), indent=1)
