"""
b3_domain_break.py — Domain-level change in the rate of decline, robust version (audit Block 3, A4).

Why
---
The published analysis applied a Pettitt test to first differences of domain-mean LLI
and reported a 2006 break (K = 346, p < 0.001). Three problems: the Pettitt p-value
assumes independent observations, whereas the differenced series has lag-1
autocorrelation ≈ 0.8; K = 346 is not reproducible (306 from committed data); and the
same break appears in the Area series, so it is not LLI-specific.

What this script does
---------------------
For each domain-mean series (LLI, Area, and delta = LLI - Area):
1. Pettitt on first differences, as published (for reference).
2. A "kink" model on the LEVELS: a straight line whose slope changes at year k
   (continuous piecewise-linear). The best k maximises the F statistic against a
   single straight line (sup-F; candidate years trimmed 15% at each end).
3. p-value of sup-F by parametric bootstrap with AR(1) noise, under two noise
   assumptions that bracket the truth:
     - "phi from H0": AR(1) fitted to residuals of the straight line. If a real
       kink exists, these residuals are inflated and autocorrelated, so this
       p-value is CONSERVATIVE (too large).
     - "phi from H1": AR(1) fitted to residuals of the kink model. If the kink
       is spurious, this under-states the noise, so this p-value is LIBERAL.
4. Uncertainty of the kink year: moving-block bootstrap of kink-model residuals
   (block length 5), refitting k each time; 90% interval of k.
The kink year is reported as the last year of the earlier slope regime.

Inputs : data/eii_HEX20_annual.csv, data/area_HEX20_annual.csv
Outputs: results/block3/domain_break_summary.txt
Run from the repository root:  python analysis/b3_domain_break.py
"""

import numpy as np
import pandas as pd

YEARS = np.arange(1986, 2024)
NBOOT = 2000
TRIM = 0.15
rng = np.random.default_rng(7)


def load(path):
    df = pd.read_csv(path, encoding="utf-8-sig").set_index("ID_UNICO")
    df.columns = [int(c[-4:]) for c in df.columns]
    return df[list(YEARS)].mean().values


def pettitt(x):
    """Pettitt test: (index of last obs before break, K, approximate p under independence)."""
    n = len(x)
    U = np.array([np.sign(x[t + 1:][None, :] - x[:t + 1][:, None]).sum() for t in range(n - 1)])
    t = int(np.argmax(np.abs(U)))
    K = abs(U[t])
    return t, K, min(1.0, 2 * np.exp(-6 * K ** 2 / (n ** 3 + n ** 2)))


t_ = (YEARS - YEARS[0]).astype(float)
n = len(t_)
cands = np.arange(int(np.ceil(TRIM * n)), int(np.floor((1 - TRIM) * n)))  # kink positions (index)


def rss(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return (r ** 2).sum(), r, X @ beta


def fit_kink(y):
    """Return (best kink index, sup-F, fitted kink curve, kink residuals, line residuals)."""
    X0 = np.column_stack([np.ones(n), t_])
    rss0, r0, _ = rss(y, X0)
    best = (None, -np.inf, None, None)
    for k in cands:
        X1 = np.column_stack([X0, np.maximum(0, t_ - t_[k])])   # hinge: slope changes after index k
        rss1, r1, f1 = rss(y, X1)
        F = (rss0 - rss1) / (rss1 / (n - 3))
        if F > best[1]:
            best = (k, F, f1, r1)
    return best[0], best[1], best[2], best[3], r0


def ar1(r):
    """Lag-1 autocorrelation and innovation SD of a residual series."""
    phi = np.corrcoef(r[:-1], r[1:])[0, 1]
    return phi, r.std() * np.sqrt(max(1e-9, 1 - phi ** 2))


def sim_ar1(phi, sd):
    e = np.empty(n)
    e[0] = rng.normal(0, sd / np.sqrt(max(1e-9, 1 - phi ** 2)))
    for i in range(1, n):
        e[i] = phi * e[i - 1] + rng.normal(0, sd)
    return e


def sup_f_pvalue(y, phi, sd):
    """Parametric bootstrap p-value of sup-F under a straight line + AR(1) noise."""
    X0 = np.column_stack([np.ones(n), t_])
    _, _, line = rss(y, X0)
    F_obs = fit_kink(y)[1]
    hits = sum(fit_kink(line + sim_ar1(phi, sd))[1] >= F_obs for _ in range(NBOOT))
    return (1 + hits) / (NBOOT + 1)


def kink_year_interval(y, fitted, resid, block=5):
    """Moving-block bootstrap of kink-model residuals -> 90% interval of the kink year."""
    ks = []
    nb = int(np.ceil(n / block))
    for _ in range(NBOOT):
        starts = rng.integers(0, n - block + 1, nb)
        e = np.concatenate([resid[s:s + block] for s in starts])[:n]
        ks.append(YEARS[fit_kink(fitted + e)[0]])
    return np.percentile(ks, [5, 50, 95])


lli = load("data/eii_HEX20_annual.csv")
area = load("data/area_HEX20_annual.csv")
lines = []
for name, y in (("LLI", lli), ("Area", area), ("delta (LLI-Area)", lli - area)):
    t, K, p = pettitt(np.diff(y))
    k, F, fitted, r1, r0 = fit_kink(y)
    phi0, sd0 = ar1(r0)
    phi1, sd1 = ar1(r1)
    p_cons = sup_f_pvalue(y, phi0, sd0)
    p_lib = sup_f_pvalue(y, phi1, sd1)
    lo, med, hi = kink_year_interval(y, fitted, r1)
    X1 = np.column_stack([np.ones(n), t_, np.maximum(0, t_ - t_[k])])
    b = np.linalg.lstsq(X1, y, rcond=None)[0]
    lines.append(f"{name}:")
    lines.append(f"  Pettitt on first differences (as published): break after {YEARS[t + 1]}, K={K:.0f}, "
                 f"nominal p={p:.1e} (assumes independence)")
    lines.append(f"  Kink model on levels: kink after {YEARS[k]}; slope {b[1] * 1000:+.2f} -> {(b[1] + b[2]) * 1000:+.2f} "
                 f"(x10^-3 per year); sup-F={F:.1f}")
    lines.append(f"  sup-F bootstrap p: conservative (AR1 phi={phi0:.2f} from straight-line residuals) = {p_cons:.3f}; "
                 f"liberal (phi={phi1:.2f} from kink residuals) = {p_lib:.4f}")
    lines.append(f"  Kink year, 90% block-bootstrap interval: {lo:.0f}-{hi:.0f} (median {med:.0f})")
txt = "\n".join(lines)
open("results/block3/domain_break_summary.txt", "w", encoding="utf-8").write(txt + "\n")
print(txt)
