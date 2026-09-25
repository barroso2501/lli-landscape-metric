# Changelog

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
