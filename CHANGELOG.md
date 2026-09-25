# Changelog

## Unreleased — claims corrections (audit 2026-09-25, Block 2)

No data or analysis code changed. Text corrections only; items that need
re-analysis are flagged, not rewritten.

- **README "Key results":** removed the "~800 cells" inference (1 − R² is a share of
  variance); residual criterion described as two-sided; added the domain-mean
  LLI ≈ Area equality; noted that ~75–80% of the rise in divergence is
  compositional; Moran p reported as p ≤ 0.01 (99-permutation floor); Pettitt
  K corrected to 306 (reproducible from `data/`), same break in the Area series,
  significance under revision (autocorrelated series); cell-level change points
  marked under revision (`ruptures` default `jump=5` restricted break years to
  5-year steps); RQ3 scale effect corrected (≤ 0.004 in 2020) and shape-effect
  wording clarified; status badge and Phase 3 set to "under revision".
- **docs/paper_outline_LLI.md (rev. 15):** Section 4.3 matrix table recomputed
  (2004 Concordant-High was 63.5%, actual 43.5%; Concordant-Low and diagonal
  columns corrected) and the difference-matrix narrative rewritten accordingly;
  RQ3 "CV_hex < CV_sq" and "< 0.001 across scales" claims corrected; Section 3.8
  now describes the implemented algorithms and break-year convention; Sections
  4.5, 4.6.2 and 4.7 flagged as superseded or unverified; the Section 3.9 claim
  that δ is free of shared-boundary correlation corrected; "external ecological
  validation" claim withdrawn. Audit notes are marked inline.
- **docs/analysis_roadmap_EII.md:** Moran p-value wording.
- **.gitignore:** `config_local.py` entry (not applied in v1.0.2 upload).

## v1.0.2 — 2026-09-25 (repository hygiene; no change to data or results)

- **CITATION.cff:** fixed invalid YAML (duplicate `version`/`date-released` keys);
  removed pre-upload checklist; `doi` now uses the Zenodo concept DOI; corrected
  the `ruptures` reference (Truong, Oudre & Vayatis 2020); MapBiomas Collection 10.1
  in abstract. Validated with `cffconvert --validate`.
- **README:** repository structure and data table now match the actual files;
  corrected hexagon geometry (side 8.77 km, perimeter 52.6 km); added legacy
  naming note (`eii_` = LLI); marked `continuidade_refatorado.ipynb` as legacy and
  `phase2_annual_pipeline.ipynb` as the primary extraction pipeline; citation now
  points to the concept DOI. The "Key results" section is unchanged, pending review.
- **docs:** corrected hexagon geometry, scale ratios (×2 area, ×√2 linear) and the
  description of jitter distances in `paper_outline_LLI.md` and
  `analysis_roadmap_EII.md`.
- **notebooks:** removed ` (1)` suffixes from two filenames; corrected the
  documentation of the jitter displacement distance (15,197 m is the flat-to-flat
  width, not the side; value unchanged); added a legacy/nodata warning cell to
  `continuidade_refatorado.ipynb`. No analysis code was changed.
- **config/config_template.py:** rewritten (previous version had a syntax error);
  aligned with the Phase 2 configuration variables.
- **Other:** added `requirements.txt` (unpinned) and this changelog; `config_local.py`
  added to `.gitignore`; removed duplicate `docs/phase1_summary.csv` (kept in `data/`);
  LICENSE copyright holder set to full name.

## v1.0.1 — 2026-04-29
- Zenodo DOI added (10.5281/zenodo.19889631).

## v1.0.0 — 2026-04-29
- First archived release.
