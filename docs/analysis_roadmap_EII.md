# Analysis Roadmap — Edge Interception Index (EII) Paper
## Ordered sequence of analyses, inputs, outputs, and dependencies

**Status:** Active planning document  
**Last updated:** 2026-03-30

---

## Overview

This roadmap organizes all analyses required for the EII paper into four sequential phases. Each phase depends on the completion of the previous one. Within each phase, analyses are ordered by dependency. Estimated complexity is indicated as: 🟢 Low / 🟡 Medium / 🔴 High.

---

## Phase 1 — Grid Configuration (MAUP Foundation)
*Purpose: Fix the methodological choices (shape, scale) before running the full pipeline. Results feed into all subsequent phases.*

### 1.1 — Shape comparison: hexagon vs. square
- **Input:** MapBiomas binary rasters (subset: 1985 and 2020); hexagonal grid (existing); square grid at equivalent cell area (to be generated).
- **Output:** EII computed under both configurations for 1985 and 2020; 5×5 Area × EII frequency matrices for each configuration; difference matrix.
- **Key question:** Do the two geometries produce substantively different aggregated distributions?
- **Complexity:** 🟡 Medium (requires generating square grid and running pipeline twice)
- **Deliverable:** Fig. 6 component (hex vs. square panel)
- **Notes:** Use the same total cell area for comparison. Document the directional sampling coverage formally (6 × 60° vs. 4 × 90°).

### 1.2 — Scale sensitivity: multi-resolution comparison
- **Input:** MapBiomas binary rasters (1985 and 2020); hexagonal grids at 2–3 target cell sizes.
- **Output:** EII and Area distributions per scale; CV of EII as a function of perimeter length (statistical stability criterion); recommended scale with justification.
- **Key question:** At what scale is the EII estimator most stable while preserving spatial resolution?
- **Complexity:** 🟡 Medium (requires generating alternative grids and running pipeline)
- **Deliverable:** Supplementary or Fig. 6 component; documented scale choice for Section 3.3
- **Decision point:** The scale chosen here becomes fixed for all subsequent analyses.

### 1.3 — Zoning sensitivity: systematic grid displacement (jitter)
- **Input:** MapBiomas binary rasters (1985 and 2020); 25 grid realizations (original + 8 directions × 3 distances).
- **Grid displacement distances:** 1/6, 1/3, and 1/2 of cell side length.
- **Output:** EII computed for each of the 25 realizations; mean and SD of EII per cell; CV map across the Cerrado; mean ± SD of the 5×5 frequency matrix.
- **Key question:** How stable are EII estimates across arbitrary grid placement choices?
- **Complexity:** 🔴 High (25 pipeline runs; use parallel execution and checkpoint system)
- **Deliverable:** Fig. 6 component (CV map); numerical robustness statement for Section 3.7.3
- **Notes:** Run on the scale and shape selected in steps 1.1 and 1.2. Report the displacement distances as fractions of cell side length, not absolute meters, for generalizability.

---

## Phase 2 — Full Annual Time Series
*Purpose: Build the complete 40-year EII dataset for all cells. This is the core dataset for all subsequent analyses.*

### 2.1 — Run EII pipeline for all years (1985–2024)
- **Input:** MapBiomas binary rasters for all 40 years; hexagonal grid (configuration fixed in Phase 1).
- **Output:** Matrix of dimensions 19,183 cells × 40 years for EII (`w_i(t)`); checkpoint files per year.
- **Complexity:** 🔴 High (40 pipeline runs; use existing checkpoint architecture)
- **Notes:** Pipeline is already operational with checkpoint system. Estimated runtime should be documented. Quality check: verify nodata handling and border cell completeness ratio for all years.

### 2.2 — Assemble paired annual dataset
- **Input:** EII matrix (2.1); Area matrix (already available, 19,183 × 40).
- **Output:** Single consolidated dataset: 19,183 cells × 40 years × 2 metrics (Area and EII).
- **Complexity:** 🟢 Low
- **Notes:** Verify alignment of cell IDs between the two matrices. Document border cells with completeness ratio < 0.8 as a quality flag.

---

## Phase 3 — Core Analyses
*Purpose: Produce the results that answer the three research questions.*

### 3.1 — Area–EII correlation and independence (RQ1)
- **Input:** Paired annual dataset (2.2).
- **Output:** Pearson and Spearman correlation between $A_i(t)$ and $w_i(t)$ per year; residual distribution; proportion of variance in EII not explained by Area.
- **Key question:** Is EII statistically independent from Area, and at what level?
- **Complexity:** 🟢 Low
- **Deliverable:** Numerical result cited in Section 4.1; motivates the rest of the paper.

### 3.2 — Decoupled state classification (RQ1)
- **Input:** Paired annual dataset (2.2).
- **Output:** Per cell per year: classification into one of four states (High/Low Area × High/Low EII, threshold = 0.5 or 20%/80% quantiles — document rationale); frequency of each state across cells and years.
- **Decoupling typology:**
  - Coupled-High (High A, High EII): intact landscapes
  - Coupled-Low (Low A, Low EII): degraded landscapes
  - Type I Decoupled (High A, Low EII): interior preserved, interface degraded
  - Type II Decoupled (Low A, High EII): interior lost, interface still connected
- **Complexity:** 🟢 Low
- **Deliverable:** Fig. 3 components; state frequency table.

### 3.3 — 5×5 frequency matrix analysis for snapshot periods (RQ2)
- **Input:** Paired annual dataset (2.2); snapshot years: 1985, 1995, 2004, 2012, 2020.
- **Output:** Five 5×5 Area × EII frequency matrices; difference matrices between consecutive periods; total mass in decoupled quadrants per period.
- **Complexity:** 🟢 Low
- **Deliverable:** Fig. 3 (main panels); Table in supplementary (all matrices).

### 3.4 — Spatial maps of Area, EII, and decoupling (RQ2)
- **Input:** Paired annual dataset (2.2); hexagonal grid shapefile.
- **Output:** Choropleth maps for: $A_i$, $w_i$, decoupling type; at minimum 1985 and 2020; optionally 2004 and 2012.
- **Complexity:** 🟡 Medium (spatial join and visualization)
- **Deliverable:** Fig. 4

### 3.5 — Change point detection: EII and Area (RQ2)
- **Input:** Paired annual dataset (2.2); PELT algorithm (Python `ruptures`).
- **Parameters:** Penalty selection via BIC; allow 1–3 changepoints per cell; document sensitivity to penalty parameter (Supplementary S3).
- **Output per cell:** Year(s) of structural break in EII ($t^*_w$) and in Area ($t^*_A$); temporal lag $\delta_i = t^*_w - t^*_A$.
- **Aggregated outputs:** Frequency distribution of $\delta_i$; proportion of cells where $\delta_i < 0$ (EII leads Area); spatial map of $\delta_i$.
- **Complexity:** 🔴 High (19,183 independent time series; use vectorized or parallel implementation)
- **Deliverable:** Fig. 5; key numerical result for Section 4.2 and Discussion 5.2.
- **Notes:** Cells with fewer than 5 valid annual observations should be excluded. Document the proportion of cells with no detectable changepoint separately.

### 3.6 — Temporal interval sensitivity (RQ3)
- **Input:** Paired annual dataset (2.2).
- **Output:** 5×5 frequency matrices under 5-year vs. 10-year snapshot intervals; comparison of matrix entries; maximum absolute difference in cell frequencies.
- **Complexity:** 🟢 Low
- **Deliverable:** Supplementary S2; robustness statement in Section 4.5.

---

## Phase 4 — Synthesis and Documentation
*Purpose: Produce paper-ready figures, finalize methods documentation, and prepare reproducibility package.*

### 4.1 — Final figure production
- **Input:** All Phase 3 outputs.
- **Output:** Publication-quality versions of Figures 1–6 (see Paper Outline).
- **Specifications:** 300 dpi minimum; consistent color scheme across figures; colorblind-safe palette; all axes labeled with units.
- **Complexity:** 🟡 Medium
- **Notes:** Fig. 1 (conceptual diagram) can be drafted in parallel with Phase 1.

### 4.2 — Methods section formalization
- **Input:** Completed analyses; pipeline code.
- **Output:** Sections 3.1–3.9 of the paper (English); mathematical notation consistent throughout.
- **Complexity:** 🟡 Medium
- **Notes:** Section 3.4 (EII formalization) is the priority — write first, as it anchors all other sections.

### 4.3 — Reproducibility package
- **Input:** Pipeline notebooks; configuration files; grid shapefiles.
- **Output:** Documented code repository with: (a) environment specification, (b) configuration file with all parameters, (c) step-by-step README, (d) example run on a subset of cells.
- **Complexity:** 🟡 Medium
- **Notes:** The existing `continuidade_refatorado.ipynb` is already well-structured; extend with Phase 1 (jitter) and Phase 3 (change point) modules.

---

## Summary Table

| Step | Phase | RQ | Complexity | Dependency | Deliverable |
|---|---|---|---|---|---|
| 1.1 Shape comparison | 1 | RQ3 | 🟡 | None | Fig. 6 |
| 1.2 Scale sensitivity | 1 | RQ3 | 🟡 | None | Fig. 6 / S |
| 1.3 Jitter (MAUP) | 1 | RQ3 | 🔴 | 1.1, 1.2 | Fig. 6 |
| 2.1 Full EII pipeline | 2 | — | 🔴 | Phase 1 complete | Core dataset |
| 2.2 Paired dataset | 2 | — | 🟢 | 2.1 | Core dataset |
| 3.1 Correlation | 3 | RQ1 | 🟢 | 2.2 | Section 4.1 |
| 3.2 State classification | 3 | RQ1 | 🟢 | 2.2 | Fig. 3 |
| 3.3 Frequency matrices | 3 | RQ2 | 🟢 | 2.2 | Fig. 3 |
| 3.4 Spatial maps | 3 | RQ2 | 🟡 | 2.2 | Fig. 4 |
| 3.5 Change point detection | 3 | RQ2 | 🔴 | 2.2 | Fig. 5 |
| 3.6 Temporal sensitivity | 3 | RQ3 | 🟢 | 2.2 | Supp. S2 |
| 4.1 Final figures | 4 | — | 🟡 | Phase 3 | Figs. 1–6 |
| 4.2 Methods writing | 4 | — | 🟡 | Phase 3 | Sections 3.x |
| 4.3 Reproducibility pkg | 4 | — | 🟡 | Phase 3 | Supp. S4 |

---

## Critical Path

The minimum sequence for a submittable paper:

```
1.1 (Shape) → 1.2 (Scale) → [fix grid configuration]
→ 2.1 (Full pipeline) → 2.2 (Paired dataset)
→ 3.1 (Correlation) + 3.2 (States) + 3.3 (Matrices) + 3.4 (Maps)
→ 4.1 (Figures) + 4.2 (Methods)
```

Steps 1.3 (Jitter) and 3.5 (Change point) are methodologically important but can be added after the critical path is complete if time or computational constraints require it. Step 3.5 in particular significantly strengthens RQ2 and should be prioritized if feasible.

---

## Pending Decisions

| Decision | Options | Deadline |
|---|---|---|
| Target cell size | To be determined in step 1.2 | Before Phase 2 |
| Changepoint penalty parameter | BIC (default) vs. manual | Before step 3.5 |
| Snapshot years for matrices | 1985, 1995, 2004, 2012, 2020 (proposed) | Before step 3.3 |
| Decoupling threshold | 0.5 (midpoint) vs. quantile-based | Before step 3.2 |
| Target journal | Ecological Indicators (preliminary) | Before submission |

---

*This document should be updated as each analytical step is completed. Record actual outputs, deviations from the plan, and decisions made during analysis.*
