"""
b3_changepoints.py — Cell-level change-point detection, corrected (audit Block 3, A9/A13).

What changed relative to notebooks/phase3_changepoint_detection.ipynb
---------------------------------------------------------------------
1. `jump=1` and `min_size=2` are set explicitly. The ruptures default `jump=5`
   restricted candidate breakpoints to every fifth year (1990, 1995, ..., 2020).
2. The same detection is run on the Area series, so that LLI and Area break years
   can be compared cell by cell (the lag t*_w - t*_A planned in outline §3.8).
   This is the test that could show whether LLI carries timing information
   that Area does not.
3. Mode A always returns one break, even in flat series. Each break is therefore
   reported with its magnitude (mean after - mean before), and summaries are
   given for all cells and for cells with |delta| >= 0.05 ("material" breaks).
   The threshold is a reporting choice; the sensitivity at 0.02 and 0.10 is printed.
4. The Mode B penalty (pen=3.0) is kept, with its sensitivity (1.5 / 3.0 / 6.0)
   computed on ALL cells rather than on a 500-cell subsample.

Break-year convention: `years[b - 1]` = LAST year of the first segment; the change
happens between that year and the next one.

Inputs : data/eii_HEX20_annual.csv, data/area_HEX20_annual.csv (committed files)
Outputs: results/block3/changepoints_cells.csv   (one row per cell)
         results/block3/changepoints_summary.txt (human-readable summary)
Runtime: ~3-5 min on a laptop (11,500 cells x 2 series x several PELT runs).

Run from the repository root:  python analysis/b3_changepoints.py
"""

import os
import numpy as np
import pandas as pd
import ruptures as rpt

YEARS = list(range(1986, 2024))  # effective analysis period (1985 and 2024 excluded)
MODEL = "rbf"                    # same cost function as the original notebook
JUMP = 1                         # evaluate every year as a candidate breakpoint
MIN_SIZE = 2                     # shortest allowed segment (ruptures default, now explicit)
PEN_B = 3.0                      # Mode B penalty used in the original analysis
PEN_SENS = [1.5, 3.0, 6.0]       # penalty sensitivity
MATERIAL = 0.05                  # |after - before| threshold for a "material" break
OUT = "results/block3"
os.makedirs(OUT, exist_ok=True)


def load(path):
    """Read a cells x years matrix and keep only the effective period, in year order."""
    df = pd.read_csv(path, encoding="utf-8-sig").set_index("ID_UNICO")
    df.columns = [int(c[-4:]) for c in df.columns]
    return df[YEARS]


def mode_a(series):
    """Exactly one break (Binseg). Returns (break year, mean after - mean before)."""
    b = rpt.Binseg(model=MODEL, jump=JUMP, min_size=MIN_SIZE).fit(series).predict(n_bkps=1)[0]
    return YEARS[b - 1], series[b:].mean() - series[:b].mean()


def mode_b(series, pen):
    """Automatic number of breaks (PELT) for a given penalty. Returns the break count."""
    bkps = rpt.Pelt(model=MODEL, jump=JUMP, min_size=MIN_SIZE).fit(series).predict(pen=pen)
    return len([b for b in bkps if b < len(series)])


lli = load("data/eii_HEX20_annual.csv")
area = load("data/area_HEX20_annual.csv")
assert (lli.index == area.index).all(), "cell order differs between LLI and Area"

# ---- run detection cell by cell -------------------------------------------------
rows = []
for cid, w, a in zip(lli.index, lli.values, area.values):
    yw, dw = mode_a(w)
    ya, da = mode_a(a)
    row = {"ID_UNICO": cid, "cp_year_lli": yw, "delta_lli": dw,
           "cp_year_area": ya, "delta_area": da}
    for pen in PEN_SENS:
        row[f"nB_lli_pen{pen}"] = mode_b(w, pen)
    row["nB_area_pen3.0"] = mode_b(a, PEN_B)
    rows.append(row)
cp = pd.DataFrame(rows).set_index("ID_UNICO")
cp["lag_lli_minus_area"] = cp.cp_year_lli - cp.cp_year_area
cp["material_both"] = (cp.delta_lli.abs() >= MATERIAL) & (cp.delta_area.abs() >= MATERIAL)
cp.round(4).to_csv(f"{OUT}/changepoints_cells.csv", encoding="utf-8-sig")

# ---- summaries ------------------------------------------------------------------
lines = []
say = lines.append
mat = cp[cp.delta_lli.abs() >= MATERIAL]

say("CELL-LEVEL CHANGE POINTS — LLI, 1986-2023 (Binseg n_bkps=1, rbf, jump=1, min_size=2)")
say(f"All cells (n={len(cp)}): break years {cp.cp_year_lli.min()}-{cp.cp_year_lli.max()}, "
    f"median {cp.cp_year_lli.median():.0f}, mean {cp.cp_year_lli.mean():.1f}, SD {cp.cp_year_lli.std():.1f}; "
    f"mean delta {cp.delta_lli.mean():.3f}; declining {(cp.delta_lli < 0).mean():.1%}")
for thr in (0.02, 0.05, 0.10):
    say(f"  share of cells with |delta_lli| >= {thr}: {(cp.delta_lli.abs() >= thr).mean():.1%}")
say(f"Material breaks only (|delta| >= {MATERIAL}, n={len(mat)}): median {mat.cp_year_lli.median():.0f}, "
    f"mean {mat.cp_year_lli.mean():.1f}, SD {mat.cp_year_lli.std():.1f}; declining {(mat.delta_lli < 0).mean():.1%}")

say("\nBreaks by period (all cells | material breaks):")
say(f"{'period':<11}{'n':>6}{'%':>7}{'mean d':>9}{'% neg':>7}   {'n':>6}{'mean d':>9}{'% neg':>7}")
for y0, y1 in [(1986, 1989), (1990, 1994), (1995, 1999), (2000, 2004), (2005, 2009),
               (2010, 2014), (2015, 2019), (2020, 2023)]:
    s = cp[cp.cp_year_lli.between(y0, y1)]
    m = mat[mat.cp_year_lli.between(y0, y1)]
    f = lambda d, col: (f"{d[col].mean():9.3f}{(d[col] < 0).mean() * 100:6.0f}%" if len(d) else f"{'-':>9}{'-':>7}")
    say(f"{y0}-{y1:<6}{len(s):6d}{len(s) / len(cp) * 100:6.1f}%{f(s, 'delta_lli')}   {len(m):6d}{f(m, 'delta_lli')}")

say("\nMode B (PELT, rbf, jump=1) — number of breaks per cell, share of cells:")
for pen in PEN_SENS:
    vc = cp[f"nB_lli_pen{pen}"].clip(upper=3).value_counts(normalize=True).sort_index()
    say(f"  pen={pen}: " + ", ".join(f"{'3+' if k == 3 else k}: {v:.1%}" for k, v in vc.items()))

say("\nLLI vs AREA break timing (Mode A):")
say(f"  identical break year, all cells: {(cp.lag_lli_minus_area == 0).mean():.1%}")
both = cp[cp.material_both]
lag = both.lag_lli_minus_area
say(f"  cells with material breaks in both series: n={len(both)}")
say(f"  lag = t*_LLI - t*_Area: identical {(lag == 0).mean():.1%}; |lag| <= 1 yr {(lag.abs() <= 1).mean():.1%}; "
    f"LLI earlier {(lag < 0).mean():.1%}; LLI later {(lag > 0).mean():.1%}; "
    f"median {lag.median():.0f}; mean {lag.mean():.2f}")
# sign test of LLI-earlier vs LLI-later among cells with non-zero lag
nz = lag[lag != 0]
from scipy.stats import binomtest
p = binomtest(int((nz < 0).sum()), len(nz), 0.5).pvalue if len(nz) else float("nan")
say(f"  sign test (LLI earlier vs later, ties excluded): n={len(nz)}, p={p:.3g}")

txt = "\n".join(lines)
open(f"{OUT}/changepoints_summary.txt", "w", encoding="utf-8").write(txt + "\n")
print(txt)
