"""
b3_neighbourhood.py — Is delta mostly a cell-vs-neighbourhood contrast? (audit Block 3, A1/A5/A6)

Reasoning
---------
The LLI samples a thin strip on the cell boundary. That strip is shared with the six
neighbours: roughly half of each boundary pixel's context belongs to the neighbouring
cell. If so, LLI should behave like a mix of the cell's own cover and its neighbours'
cover, and delta = LLI - Area should track the contrast (neighbour Area - own Area).
If that contrast explains most of delta, the "interface" information in LLI is largely
information about the neighbourhood, which is available from Area alone once
neighbours are considered. This is a HYPOTHESIS test, not an established result.

Adjacency (IMPORTANT — inferred, not read from the shapefile)
-------------------------------------------------------------
The grid shapefile is not in the repository. Adjacency is reconstructed from the ID
order: IDs run row-major, 115 cells per row x 100 rows. For flat-topped hexagons in
columns, the six neighbours of (r, c) are (r±1, c), (r, c±1) and (r-1, c±1) if c is
even, (r+1, c±1) if c is odd (0-based). This layout and parity were inferred from
neighbour correlations of Area (lag-1 and lag-115 IDs r ≈ 0.81-0.83; wrong-parity
diagonals r ≈ 0.72-0.74; distance-2 cells r ≈ 0.70).
-> Re-run with queen weights from the real shapefile before citing any number
   (set GRID_SHAPEFILE below; the script then uses the shapefile instead).

What is computed
----------------
1. Per year, OLS fits:  LLI ~ Area   vs   LLI ~ Area + mean neighbour Area.
   Reported: R², and the neighbour coefficient.
2. Per year: correlation between delta and (neighbour Area - own Area), and the
   share of delta variance explained by that contrast.
3. Moran's I on the binary divergent state with 999 permutations (the published
   analysis used 99, whose minimum p-value is 0.01), and the same on delta after
   removing the contrast (residual delta), to see whether clustering survives.

Inputs : data/eii_HEX20_annual.csv, data/area_HEX20_annual.csv
Outputs: results/block3/neighbourhood_by_year.csv, results/block3/neighbourhood_summary.txt
Requires: numpy, pandas (+ geopandas and libpysal only if GRID_SHAPEFILE is set)

Run from the repository root:  python analysis/b3_neighbourhood.py
"""

import os
import numpy as np
import pandas as pd

GRID_SHAPEFILE = None   # e.g. r"D:\Modelo_LAPIG\grids\hex_20000ha.shp" to use real adjacency
NROW, NCOL = 100, 115
YEARS = list(range(1986, 2024))
TAU = 0.5
NPERM = 999
OUT = "results/block3"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)


def load(path):
    df = pd.read_csv(path, encoding="utf-8-sig").set_index("ID_UNICO")
    df.columns = [int(c[-4:]) for c in df.columns]
    return df[YEARS]


w = load("data/eii_HEX20_annual.csv")
a = load("data/area_HEX20_annual.csv")
ids = w.index.values
n = len(ids)

# ---- neighbour lists ------------------------------------------------------------
if GRID_SHAPEFILE:
    # Real adjacency from the shapefile (queen contiguity), in the same ID order.
    import geopandas as gpd
    from libpysal.weights import Queen
    g = gpd.read_file(GRID_SHAPEFILE).sort_values("ID_UNICO").set_index("ID_UNICO").loc[ids]
    W = Queen.from_dataframe(g.reset_index(), use_index=False, silence_warnings=True)
    nbrs = [np.array(W.neighbors[i], dtype=int) for i in range(n)]
    SOURCE = "shapefile (queen)"
else:
    assert n == NROW * NCOL and (ids == np.arange(1, n + 1)).all(), "ID layout assumption fails"
    nbrs = []
    for k in range(n):
        r, c = divmod(k, NCOL)
        dr = -1 if c % 2 == 0 else 1                  # row offset of the diagonal neighbours
        cand = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1), (r + dr, c - 1), (r + dr, c + 1)]
        nbrs.append(np.array([rr * NCOL + cc for rr, cc in cand if 0 <= rr < NROW and 0 <= cc < NCOL]))
    SOURCE = "INFERRED from ID order (verify with shapefile)"

# Row-standardised sparse-free representation: arrays of (i, j, weight)
I = np.concatenate([np.full(len(nb), i) for i, nb in enumerate(nbrs)])
J = np.concatenate(nbrs)
WT = np.concatenate([np.full(len(nb), 1 / len(nb)) for nb in nbrs])


def lag(x):
    """Spatial lag: row-standardised mean of the neighbours' values."""
    return np.bincount(I, weights=WT * x[J], minlength=n)


def moran(x, nperm=NPERM):
    """Global Moran's I with a conditional-free permutation p-value (one-sided, I > E[I])."""
    z = x - x.mean()
    s = (z * z).sum()
    I_obs = (n / WT.sum()) * (z * lag(z)).sum() / s
    sims = np.empty(nperm)
    for k in range(nperm):
        zp = rng.permutation(z)
        sims[k] = (n / WT.sum()) * (zp * lag(zp)).sum() / s
    p = (1 + (sims >= I_obs).sum()) / (nperm + 1)
    return I_obs, p


def ols_r2(y, X):
    """R² and coefficients of an OLS fit with intercept."""
    X1 = np.column_stack([np.ones(len(y))] + X)
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    res = y - X1 @ beta
    return 1 - res.var() / y.var(), beta

rows = []
for y in YEARS:
    wy, ay = w[y].values, a[y].values
    an = lag(ay)                                   # mean neighbour Area
    contrast = an - ay
    delta = wy - ay
    r2_a, _ = ols_r2(wy, [ay])
    r2_an, b = ols_r2(wy, [ay, an])
    r2_d, bd = ols_r2(delta, [contrast])
    resid_delta = delta - (bd[0] + bd[1] * contrast)
    row = {"year": y, "r2_lli_on_area": r2_a, "r2_lli_on_area_and_nbr": r2_an,
           "coef_area": b[1], "coef_nbr_area": b[2],
           "corr_delta_contrast": np.corrcoef(delta, contrast)[0, 1],
           "r2_delta_on_contrast": r2_d}
    if y in (1986, 2004, 2023):                    # permutation tests are slow; key years only
        div = ((ay >= TAU) != (wy >= TAU)).astype(float)
        row["moran_div_I"], row["moran_div_p"] = moran(div)
        row["moran_delta_I"], row["moran_delta_p"] = moran(delta)
        row["moran_resid_delta_I"], row["moran_resid_delta_p"] = moran(resid_delta)
    rows.append(row)
res = pd.DataFrame(rows)
res.round(4).to_csv(f"{OUT}/neighbourhood_by_year.csv", index=False, encoding="utf-8-sig")

L = [f"Adjacency source: {SOURCE}; mean neighbours per cell {np.mean([len(x) for x in nbrs]):.2f}"]
for y in (1986, 2004, 2023):
    r = res[res.year == y].iloc[0]
    L.append(f"{y}: R² LLI~Area {r.r2_lli_on_area:.3f} -> +nbr Area {r.r2_lli_on_area_and_nbr:.3f} "
             f"(coef own {r.coef_area:.3f}, nbr {r.coef_nbr_area:.3f}); "
             f"corr(delta, nbr-own contrast) {r.corr_delta_contrast:.3f} -> explains {r.r2_delta_on_contrast:.0%} of delta variance")
    L.append(f"      Moran (999 perm): divergent state I={r.moran_div_I:.3f} p={r.moran_div_p:.3f}; "
             f"delta I={r.moran_delta_I:.3f} p={r.moran_delta_p:.3f}; "
             f"delta net of contrast I={r.moran_resid_delta_I:.3f} p={r.moran_resid_delta_p:.3f}")
L.append(f"Range over 1986-2023: share of delta variance explained by contrast "
         f"{res.r2_delta_on_contrast.min():.0%}-{res.r2_delta_on_contrast.max():.0%}; "
         f"unexplained LLI variance falls from {1 - res.r2_lli_on_area.mean():.1%} (Area only) "
         f"to {1 - res.r2_lli_on_area_and_nbr.mean():.1%} (Area + neighbours), mean over years")
txt = "\n".join(L)
open(f"{OUT}/neighbourhood_summary.txt", "w", encoding="utf-8").write(txt + "\n")
print(txt)
