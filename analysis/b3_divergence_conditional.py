"""
b3_divergence_conditional.py — Divergence conditional on Area (audit Block 3, A2).

Question: does the rise in LLI-Area divergence over 1986-2023 reflect more divergence
at a GIVEN level of habitat cover, or just more cells at intermediate cover, where
divergence is naturally larger?

Method
------
- Cells are binned by Area into deciles of the Area axis (0-0.1, ..., 0.9-1.0).
- For each year: share of cells with |delta| > 0.10 inside each bin (the "rate"),
  and the share of cells in each bin (the "composition").
- Kitagawa decomposition of the change between 1986 and each later year:
    total change = composition effect + rate effect
  computed with both reference orders and averaged (symmetric decomposition),
  so the split does not depend on which year is taken as reference.
- Same decomposition for Type I + Type II (tau = 0.5) states.
- Signed delta by Area bin, to show where delta is negative vs positive.

Inputs : data/eii_HEX20_annual.csv, data/area_HEX20_annual.csv
Outputs: results/block3/divergence_rates_by_area_bin.csv  (year x bin rates, counts)
         results/block3/divergence_decomposition.csv      (year-by-year decomposition)
         results/block3/divergence_conditional.png        (two-panel figure)
         results/block3/divergence_summary.txt

Run from the repository root:  python analysis/b3_divergence_conditional.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")            # render to file; no display needed
import matplotlib.pyplot as plt

YEARS = list(range(1986, 2024))
THR = 0.10                       # |delta| threshold used in README / outline
TAU = 0.5                        # state threshold for Type I / II
EDGES = np.linspace(0, 1, 11)
EDGES[-1] = 1.0001               # include Area == 1.0 in the last bin
LABELS = [f"{EDGES[i]:.1f}-{min(EDGES[i + 1], 1):.1f}" for i in range(10)]
OUT = "results/block3"
os.makedirs(OUT, exist_ok=True)


def load(path):
    df = pd.read_csv(path, encoding="utf-8-sig").set_index("ID_UNICO")
    df.columns = [int(c[-4:]) for c in df.columns]
    return df[YEARS]


w = load("data/eii_HEX20_annual.csv")
a = load("data/area_HEX20_annual.csv")
d = w - a

# ---- rates and composition per year and Area bin --------------------------------
records = []
for y in YEARS:
    b = pd.cut(a[y], EDGES, right=False, labels=LABELS)
    big = d[y].abs() > THR
    div = (a[y] >= TAU) != (w[y] >= TAU)          # Type I or Type II
    g = pd.DataFrame({"bin": b, "big": big, "div": div, "delta": d[y]}).groupby("bin", observed=False)
    t = pd.DataFrame({"n": g.size(), "rate_absdelta_gt": g.big.mean(),
                      "rate_typeI_II": g["div"].mean(), "mean_delta": g.delta.mean()})
    t["share_cells"] = t.n / t.n.sum()
    t["year"] = y
    records.append(t.reset_index())
rates = pd.concat(records)
rates.round(4).to_csv(f"{OUT}/divergence_rates_by_area_bin.csv", index=False, encoding="utf-8-sig")


def kitagawa(y0, y1, col):
    """Symmetric composition/rate decomposition of the change in an overall share."""
    r0 = rates[rates.year == y0].set_index("bin")
    r1 = rates[rates.year == y1].set_index("bin")
    c0, c1 = r0.share_cells, r1.share_cells
    q0, q1 = r0[col].fillna(0), r1[col].fillna(0)      # empty bins contribute nothing
    total = (c1 * q1).sum() - (c0 * q0).sum()
    comp = ((c1 - c0) * (q0 + q1) / 2).sum()            # composition effect
    rate = ((q1 - q0) * (c0 + c1) / 2).sum()            # rate (within-bin) effect
    return (c0 * q0).sum(), (c1 * q1).sum(), total, comp, rate


dec = []
for y in YEARS[1:]:
    for col, name in (("rate_absdelta_gt", "absdelta_gt_0.10"), ("rate_typeI_II", "typeI_II")):
        s0, s1, tot, comp, rate = kitagawa(1986, y, col)
        dec.append({"metric": name, "year": y, "share_1986": s0, "share_year": s1,
                    "change": tot, "composition_effect": comp, "rate_effect": rate,
                    "composition_fraction": comp / tot if tot else np.nan})
dec = pd.DataFrame(dec)
dec.round(4).to_csv(f"{OUT}/divergence_decomposition.csv", index=False, encoding="utf-8-sig")

# ---- text summary -----------------------------------------------------------------
L = []
for name in ("absdelta_gt_0.10", "typeI_II"):
    r = dec[(dec.metric == name) & (dec.year == 2023)].iloc[0]
    L.append(f"{name}: 1986 {r.share_1986:.1%} -> 2023 {r.share_year:.1%} (change {r.change * 100:+.1f} pp) = "
             f"composition {r.composition_effect * 100:+.1f} pp + within-bin rate {r.rate_effect * 100:+.1f} pp "
             f"(composition fraction {r.composition_fraction:.0%})")
L.append("\nRate of |delta| > 0.10 by Area bin, 1986 vs 2023 (share of cells in bin):")
p = rates[rates.year.isin([1986, 2023])].pivot(index="bin", columns="year", values=["rate_absdelta_gt", "n", "mean_delta"])
for b in LABELS:
    L.append(f"  Area {b}: {p.loc[b, ('rate_absdelta_gt', 1986)]:6.1%} (n={int(p.loc[b, ('n', 1986)]):5d}) -> "
             f"{p.loc[b, ('rate_absdelta_gt', 2023)]:6.1%} (n={int(p.loc[b, ('n', 2023)]):5d});  "
             f"mean delta {p.loc[b, ('mean_delta', 1986)]:+.3f} -> {p.loc[b, ('mean_delta', 2023)]:+.3f}")
txt = "\n".join(L)
open(f"{OUT}/divergence_summary.txt", "w", encoding="utf-8").write(txt + "\n")
print(txt)

# ---- figure -----------------------------------------------------------------------
# Panel A: within-bin rate vs Area for selected years (sequential blue = time).
# Panel B: observed share vs composition-only counterfactual over time (2 series).
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEQ = {1986: "#86b6ef", 2004: "#2a78d6", 2023: "#104281"}   # light -> dark = earlier -> later
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURF,
                     "axes.facecolor": SURF})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
mid = (EDGES[:-1] + np.minimum(EDGES[1:], 1)) / 2
for y, col in SEQ.items():
    r = rates[rates.year == y].set_index("bin").reindex(LABELS)
    ok = r.n >= 30                                   # hide bins with too few cells
    ax1.plot(mid[ok.values], r.rate_absdelta_gt[ok].values * 100, color=col, lw=2, marker="o", ms=5, label=str(y))
ax1.set_xlabel("Area (bin midpoint)")
ax1.set_ylabel("% of cells with |δ| > 0.10")
ax1.set_title("A. Divergence rate at a given Area", loc="left", color=INK, fontsize=10)
ax1.legend(frameon=False, title="Year", fontsize=8, title_fontsize=8)
ax1.set_ylim(0, None)

obs = dec[dec.metric == "absdelta_gt_0.10"]
cf = obs.share_1986 + obs.composition_effect                  # composition-only path
ax2.plot(obs.year, obs.share_year * 100, color="#2a78d6", lw=2, label="Observed")
ax2.plot(obs.year, cf * 100, color="#eb6834", lw=2, ls="--", label="Composition only (1986 rates)")
ax2.set_xlabel("Year")
ax2.set_ylabel("% of cells with |δ| > 0.10")
ax2.set_title("B. Observed vs composition-only change", loc="left", color=INK, fontsize=10)
ax2.legend(frameon=False, fontsize=8)
for ax in (ax1, ax2):
    ax.grid(True, color=GRID, lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(f"{OUT}/divergence_conditional.png", dpi=200)
