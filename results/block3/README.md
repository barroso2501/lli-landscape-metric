# Block 3 — Re-analyses (audit 2026-09-25)

Scripts are in `analysis/`. Each runs from the repository root using only the committed
CSVs in `data/`, except `b3_raster_checks.py`, which needs the rasters and the grid
shapefile (run it locally). Confidence labels follow the audit report: **[verified]** =
recomputed here from committed data; **[needs check]** = requires rasters or shapefile.

| Script | Audit items | Runtime | Output |
|---|---|---|---|
| `b3_changepoints.py` | A9, A13, A4 (cell level) | ~3 min | `changepoints_cells.csv`, `changepoints_summary.txt` |
| `b3_divergence_conditional.py` | A2 | < 1 min | `divergence_*.csv`, `divergence_conditional.png`, `divergence_summary.txt` |
| `b3_neighbourhood.py` | A1, A5, A6 | < 1 min | `neighbourhood_by_year.csv`, `neighbourhood_summary.txt` |
| `b3_domain_break.py` | A4 (domain level) | < 1 min | `domain_break_summary.txt` |
| `b3_segments_baseline.py` | A7, RQ1 decisive test | < 1 min | `segments_baseline_summary.txt` (needs local `seg_w1w6_annual.csv`) |
| `b3_raster_checks.py` | A1 (null model), A8, A12 | 5–15 min per year, **local** | written to the configured folder |

`notebooks/phase3_changepoint_detection.ipynb` now sets `jump=1` and `min_size=2` explicitly.

---

## 1. Cell-level change points, corrected (`jump=1`) — [verified]

- Mode A break years span 1987–2021 (median 2002, mean 2003.5, SD 6.6), replacing
  1990–2020 / median 2000, which were artefacts of `jump=5`.
- Mode A forces a break in every cell. Only 68% of cells have a material break
  (|ΔLLI| ≥ 0.05); among them 98% are declines.
- **The "post-2010 attenuation" (≈50% negative breaks in 2010–2014) is an artefact
  of forced breaks in flat series.** In 2010–2014 there are 2,415 breaks, but only
  757 are material. Material breaks in that period are 99% declines, with a mean
  ΔLLI of −0.146. What changes after 2010 is the *number* of cells with material
  breaks, not their direction.
- Mode B (PELT, pen = 3.0) with `jump=1`: 0 breaks 11.7%, 1 break 21.2%, 2 breaks
  57.6%, 3+ breaks 9.5%.
- **LLI vs Area timing (the test of whether LLI "sees" change earlier):**
  - Sample: 7,276 cells with material breaks in both series.
  - Median lag t\*_LLI − t\*_Area = 0 years.
  - LLI earlier in 35.3% of cells, later in 33.7%, same year in 31.0%.
  - Sign test on non-zero lags: p = 0.105.
  - **No evidence that LLI breaks precede Area breaks at the cell level** at annual
    resolution. This bears directly on the "early-configuration indicator"
    hypothesis (outline §5.2).

## 2. Divergence conditional on Area — [verified]

Symmetric Kitagawa decomposition of the 1986 → 2023 change:

| Metric | 1986 | 2023 | Change | Composition effect | Within-Area-bin effect |
|---|---|---|---|---|---|
| \|δ\| > 0.10 | 8.4% | 17.6% | +9.2 pp | +7.1 pp (77%) | +2.1 pp |
| Type I + II (τ = 0.5) | 2.8% | 8.1% | +5.4 pp | +5.3 pp (98%) | +0.1 pp |

- **The tripling of Type I + II is almost entirely compositional.** At a given Area,
  the probability of being divergent did not change.
- A composition-controlled signal does exist in the *sign* of δ.
  - Within Area bins ≥ 0.5, mean δ moved from ≈ 0 to negative. For example, at Area
    0.7–0.8 it went from +0.003 to −0.026.
  - Within low-Area bins it stayed positive.
  - The pattern is consistent with δ tracking the contrast between a cell and its
    neighbourhood (next section). In 2023 a cell with a given high Area is more often
    surrounded by converted land than a cell with the same Area in 1986.

## 3. δ as a cell–neighbourhood contrast — [verified]

- **Adjacency:** reconstructed from the ID layout (row-major, 115 × 100, flat-topped
  hexagons). It reproduces the published Moran's I exactly (1986: 0.114; 2004: 0.112;
  2023: 0.102), so it matches the shapefile's queen contiguity.
- **LLI ≈ 0.64 × own Area + 0.37 × mean neighbour Area**, stable across years. Adding
  neighbour Area lowers the unexplained variance of LLI from 7.1% to 5.4%.
- **The neighbour contrast (neighbour Area − own Area) explains 25–29% of δ's
  variance** in every year.
- **Moran's I with 999 permutations:**
  - Divergent state: p = 0.001 in 1986, 2004 and 2023.
  - δ net of the contrast is still clustered (I = 0.15–0.18). This residual mixes
    within-cell arrangement with shared-boundary sampling noise, and only the raster
    null model (§5) can separate the two.
- **Interpretation — hypothesis, not established:**
  - A neighbour weight is expected from geometry alone, because the perimeter lies
    between cells. So "LLI contains neighbourhood information" is largely a property
    of the sampling design rather than an ecological finding.
  - This neighbourhood information is also available from Area once adjacency is used.

## 4. Domain-level break — [verified]

| Series | Kink after | Slope before → after (×10⁻³ yr⁻¹) | sup-F p (conservative / liberal) | 90% CI of kink year |
|---|---|---|---|---|
| LLI | 2006 | −8.2 → −3.9 | ≤ 0.001 / 0.0005 | 2005–2007 |
| Area | 2006 | −8.2 → −3.9 | 0.001 / 0.0005 | 2005–2007 |
| δ (LLI − Area) | 1992 | −0.14 → −0.04 | 0.17 / 0.07 | 1992–2000 |

- **The 2006 halving of the decline rate is robust** to autocorrelation. This
  replaces the audit's earlier AR(1) check on first differences (p ≈ 0.10), which
  was over-conservative.
- **The break is identical in the Area series**, so it is a land-cover signal that
  LLI reproduces, not evidence specific to LLI.
- The δ series shows no robust break.

## 5. Segment orientation and the area-plus-neighbours baseline (`b3_segments_baseline.py`) — [verified]

Input: `seg_w1w6_annual.csv` from the segment notebook, supplied by the author. It is
not committed because of its size (16 MB).

**A7 resolved from the data.**
- Two adjacent cells share one segment, so their values are identical. Every segment
  finds an exact partner (mean |diff| = 0.00000). This also confirms the inferred grid
  layout.
- Segments face (assuming +row = North, +col = East): **w1 = SE, w2 = S, w3 = SW,
  w4 = NW, w5 = N, w6 = NE**.
- The notebook's axes are therefore mislabelled:
  - `grad_EW` (w5 − w2) is **N − S**
  - `grad_NESW` (w4 − w1) is **NW − SE**
  - `grad_NWSE` (w3 − w6) is **SW − NE**
- The outline's "NE–SW dominance coherent with MATOPIBA" refers to the NW–SE axis.
- **Confirmed on the real shapefile** (`b3_raster_checks.py`, A7 section): all 11,500
  rings are clockwise with 6 vertices; w1..w6 are traversed at 240°, 180°, 120°, 60°,
  0°, 300° (as the notebook assumes) and face compass bearings 120°, 180°, 240°, 300°,
  0°, 60°, i.e. SE, S, SW, NW, N, NE.

**Segment cover vs the two cells it separates.**
- Model: w_seg ≈ 0.52 × Area(own) + 0.52 × Area(across).
- R² rises from 0.66–0.69 (own cell only) to 0.72–0.75 (both cells).
- The residual SD is 0.12–0.17. This is what the boundary line records beyond the two
  cells' average cover: fine-scale arrangement plus line-sampling error.

**Decisive predictive test.**
- Target: future Area loss over 5 years (origins 1990–2015; 69,000 cell-periods;
  spatial block cross-validation).
- Baseline: own Area, mean and individual neighbour Areas, and past changes of own
  and neighbour Area. The baseline is informative: neighbour Area information raises
  R² from 0.223 (own cell only) to 0.259.

| Learner | Baseline R² | + LLI | + 6 segments |
|---|---|---|---|
| Linear | 0.2587 | 0.2588 (Δ +0.0000) | 0.2587 (Δ −0.0000) |
| Gradient boosting | 0.3272 | 0.3268 (Δ −0.0004) | 0.3278 (Δ +0.0006) |

**Neither LLI nor the six segment values add any predictive skill for future habitat
loss once own and neighbour Area are known.** This is one operationalisation of
"information" (future land-cover change). LLI could still carry information relevant
to other outcomes (e.g. movement, fire spread), but that is untested and needs
external data.

## 6. Raster checks to run locally

The MapBiomas rasters are in **EPSG:4326** (pixel 0.000269°, ≈ 30 m N–S and ≈ 28.6–29.9 m E–W
across the domain); the grid is in ESRI:102033. Geometries are transformed vertex-only to
the raster CRS, as in the pipeline. `b3_raster_checks.py` v2 is resumable and several
times faster than v1.
 (`b3_raster_checks.py`) — [needs check]

Tested on a synthetic raster and grid. The pixel-count emulation reproduces
`rasterstats.zonal_stats` exactly (max |diff| = 0.0000).

1. **A7 — segment orientation.** For each segment index: the traversal angle used
   in the notebook, and the compass bearing of the side it faces. On a synthetic
   clockwise flat-top grid, the segment traversed at 0° faces North, which would make
   `grad_EW` a North–South gradient. This needs confirming on the real shapefile.
2. **A8 — pixel-count vs length-weighted LLI.**
   - Compares LLI computed both ways, for the full perimeter and per segment.
   - On synthetic data, length-weighting removes the full-perimeter vs mean-of-six
     offset (−0.001 vs +0.002 / −0.004).
   - Real-data numbers are what matter.
   - Side finding: `zonal_stats` reads a window clipped to each geometry's bounding
     box. A boundary lying exactly on a pixel border therefore loses the touched row
     on one side, a further small orientation-dependent effect.
3. **A1 — null model.**
   - Two concentric inner hexagons (scales 0.4 and 0.6) together have the same total
     length as the perimeter.
   - For the perimeter and for these rings, the script reports the SD of δ, the
     |δ| > 0.10 share, the Type I + II share, and a regression of w on own and
     neighbour Area.
   - If the perimeter's residual (what remains beyond own + neighbour cover) is close
     to the rings' residual, the remaining δ is consistent with line-sampling error.
4. **A12 — valid-data coverage** of interior and perimeter for every cell.

**Please send back** `raster_checks_summary.txt` and `orientation_diagnostic.csv`.
