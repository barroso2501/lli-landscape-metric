"""
b3_segments_baseline.py — Does LLI carry information beyond own + neighbour Area? (audit Block 3, A1/A7)

This is the decisive test for RQ1. It uses the per-segment LLI file produced by
notebooks/phase3_segment_decomposition.ipynb (seg_w1w6_annual.csv; 11,500 cells x
6 segments x 40 years) together with the committed Area matrix.

Part 1 — Segment -> neighbour mapping, from the data (A7)
    Two adjacent hexagons share one boundary segment, so the same pixels are counted
    for both. For each segment index and column parity, the script finds the
    neighbour and segment with identical values (|diff| = 0). This gives the true
    direction each segment faces, independent of the notebook's angle labels.
    Grid layout (row-major, 115 columns x 100 rows) was inferred from IDs and is
    confirmed if every segment finds an exact match.
    Compass directions assume row index increases northwards and column index
    eastwards. Supporting evidence: the high-row / low-column quadrant was the most
    intact in 1985 (0.98 Area), consistent with the Amazon in the north-west of the
    domain. Confirm with the shapefile.

Part 2 — Segment cover vs the two cells it separates
    w_seg ~ Area(own cell) + Area(neighbour across that segment). The residual is
    what the boundary line records beyond the two cells' average cover.

Part 3 — Predictive test (out of sample)
    Target: future Area loss of a cell over H years, A(t) - A(t+H).
    Baseline predictors (area-only information): own Area, mean neighbour Area, the
    6 individual neighbour Areas, and past H-year changes of own and neighbour Area.
    Test predictors added to the baseline:
      +LLI      : cell LLI (mean of the 6 segments)
      +segments : the 6 segment values
    Skill is measured with spatial block cross-validation (blocks of 10 x 10 cells,
    so neighbouring cells are never split between training and test), pooled over
    origin years 1990, 1995, ..., 2015. Two learners: linear regression and gradient
    boosting (nonlinear). If LLI or segments add ~0 skill over the baseline, they do
    not carry information about future change that Area + neighbours lack.

Inputs : data/area_HEX20_annual.csv (committed), SEG_CSV (local file, see below)
Outputs: results/block3/segments_baseline_summary.txt
Run from the repository root:  python analysis/b3_segments_baseline.py
Runtime: ~2-4 min.
"""

import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import HistGradientBoostingRegressor

SEG_CSV = "data_local/seg_w1w6_annual.csv"   # output of the segment notebook (not committed)
NR, NC = 100, 115
H = 5                                          # prediction horizon (years)
ORIGINS = list(range(1990, 2019, 5))           # t; target uses t+H <= 2023
BLOCK = 10                                     # spatial CV block size (cells)
OUT = "results/block3"
os.makedirs(OUT, exist_ok=True)
L = []
say = lambda s="": (print(s), L.append(s))

area = pd.read_csv("data/area_HEX20_annual.csv", encoding="utf-8-sig").set_index("ID_UNICO")
area.columns = [int(c[-4:]) for c in area.columns]
seg = pd.read_csv(SEG_CSV, encoding="utf-8-sig").set_index("ID_UNICO")
assert (area.index == seg.index).all() and len(area) == NR * NC


def S(year):
    """(cells x 6) matrix of segment values w1..w6 for one year."""
    return np.column_stack([seg[f"w{k}_{year}"].values for k in range(1, 7)])


# ---------------------------------------------------------------------------------
# Part 1 — mapping each segment to the neighbour it faces
# ---------------------------------------------------------------------------------
OFFS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
rows, cols = np.divmod(np.arange(NR * NC), NC)
S23 = S(2023)
mapping = {}   # (parity, seg) -> (dr, dc, neighbour seg)
say("PART 1 — segment -> neighbour it faces (exact shared-edge match), 2023")
for par in (0, 1):
    for s in range(6):
        best = None
        for dr, dc in OFFS:
            m = (cols % 2 == par) & (rows + dr >= 0) & (rows + dr < NR) & (cols + dc >= 0) & (cols + dc < NC)
            i = np.where(m)[0]
            j = (rows[i] + dr) * NC + cols[i] + dc
            for s2 in range(6):
                e = np.abs(S23[i, s] - S23[j, s2]).mean()
                if best is None or e < best[0]:
                    best = (e, dr, dc, s2)
        mapping[(par, s)] = best[1:]
        say(f"  column parity {par}: w{s + 1} = w{best[3] + 1} of neighbour at (row{best[1]:+d}, col{best[2]:+d}); "
            f"mean |diff| {best[0]:.5f}")


# Direction each segment faces. Vertical segments (dc = 0) face N or S. The two segments
# on the same side (dc > 0 = East, dc < 0 = West) are told apart by the neighbour's row:
# the one leading to the lower row faces South (checked on even columns).
FACE = {}
for s in range(6):
    dr, dc, _ = mapping[(0, s)]
    if dc == 0:
        FACE[s] = "N" if dr > 0 else "S"
    else:
        other = [mapping[(0, q)][0] for q in range(6) if q != s and mapping[(0, q)][1] == dc][0]
        FACE[s] = ("S" if dr < other else "N") + ("E" if dc > 0 else "W")
say("  Direction faced (assumes +row = North, +col = East): " +
    ", ".join(f"w{s + 1}={FACE[s]}" for s in range(6)))
say("  Notebook labels: grad_EW = w5 - w2, grad_NESW = w4 - w1, grad_NWSE = w3 - w6.")
say(f"  Actual axes: w5 - w2 = {FACE[4]} - {FACE[1]}; w4 - w1 = {FACE[3]} - {FACE[0]}; "
    f"w3 - w6 = {FACE[2]} - {FACE[5]}.")

# neighbour index across each segment, per cell (NaN-safe with -1 for outside grid)
NB = np.full((NR * NC, 6), -1)
for k in range(NR * NC):
    r, c = divmod(k, NC)
    for s in range(6):
        dr, dc, _ = mapping[(c % 2, s)]
        rr, cc = r + dr, c + dc
        if 0 <= rr < NR and 0 <= cc < NC:
            NB[k, s] = rr * NC + cc

# ---------------------------------------------------------------------------------
# Part 2 — segment cover vs the two cells it separates
# ---------------------------------------------------------------------------------
say("\nPART 2 — w_segment ~ Area(own) + Area(neighbour across the segment)")
for y in (1986, 2004, 2023):
    Ay = area[y].values
    Wy = S(y)
    ok = NB >= 0
    w = Wy[ok]
    own = np.repeat(Ay[:, None], 6, 1)[ok]
    nb = Ay[NB[ok]]
    X = np.column_stack([np.ones(len(w)), own, nb])
    beta, *_ = np.linalg.lstsq(X, w, rcond=None)
    res = w - X @ beta
    r2 = 1 - res.var() / w.var()
    X0 = X[:, :2]
    b0, *_ = np.linalg.lstsq(X0, w, rcond=None)
    r2_0 = 1 - (w - X0 @ b0).var() / w.var()
    say(f"  {y}: own only R² {r2_0:.3f} -> own + across R² {r2:.3f}; coefficients own {beta[1]:.3f}, "
        f"across {beta[2]:.3f}; residual SD {res.std():.3f}")

# ---------------------------------------------------------------------------------
# Part 3 — predictive test with spatial block cross-validation
# ---------------------------------------------------------------------------------
say(f"\nPART 3 — predicting Area loss over {H} years, origins {ORIGINS[0]}-{ORIGINS[-1]} (pooled)")
blocks = (rows // BLOCK) * 100 + (cols // BLOCK)
feats = {"base": [], "lli": [], "seg": []}
yv, grp = [], []
for t in ORIGINS:
    A0, A1, Ap = area[t].values, area[t + H].values, area[t - 5 if t - 5 >= 1985 else 1985].values
    Wt = S(t)
    nbA = np.where(NB >= 0, A0[np.clip(NB, 0, None)], np.nan)
    nbAp = np.where(NB >= 0, Ap[np.clip(NB, 0, None)], np.nan)
    nb_mean = np.nanmean(nbA, 1)
    # missing neighbours (grid edge) -> replaced by the cell's mean neighbour Area
    nbA_f = np.where(np.isnan(nbA), nb_mean[:, None], nbA)
    base = np.column_stack([A0, nb_mean, nbA_f, A0 - Ap, nb_mean - np.nanmean(nbAp, 1)])
    feats["base"].append(base)
    feats["lli"].append(np.column_stack([base, Wt.mean(1)]))
    feats["seg"].append(np.column_stack([base, Wt]))
    yv.append(A0 - A1)
    grp.append(blocks)
for k in feats:
    feats[k] = np.vstack(feats[k])
yv = np.concatenate(yv)
grp = np.concatenate(grp)
ub = np.unique(grp)
rng = np.random.default_rng(0)
fold_of_block = dict(zip(ub, rng.integers(0, 5, len(ub))))
fold = np.array([fold_of_block[g] for g in grp])


def cv_r2(X, model):
    """Out-of-sample R² with 5 spatial-block folds."""
    pred = np.empty_like(yv)
    for f in range(5):
        tr, te = fold != f, fold == f
        m = model()
        m.fit(X[tr], yv[tr])
        pred[te] = m.predict(X[te])
    return 1 - ((yv - pred) ** 2).mean() / yv.var()


say(f"  n = {len(yv)} cell-periods; mean loss {yv.mean():.3f}, SD {yv.std():.3f}")
for lname, model in (("linear", LinearRegression),
                     ("gradient boosting", lambda: HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                                                                  random_state=0))):
    r = {k: cv_r2(feats[k], model) for k in feats}
    say(f"  {lname:<17}: baseline (Area + neighbours) R² {r['base']:.4f} | +LLI {r['lli']:.4f} "
        f"(Δ {r['lli'] - r['base']:+.4f}) | +6 segments {r['seg']:.4f} (Δ {r['seg'] - r['base']:+.4f})")
# reference: how much neighbours add over own Area only (shows the baseline is informative)
own_only = feats["base"][:, [0, 8]]          # own Area, own past change
r_own = cv_r2(own_only, LinearRegression)
say(f"  reference (linear): own Area + own past change only R² {r_own:.4f}")

open(f"{OUT}/segments_baseline_summary.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
